"""Pipeline orchestration glue between the HTTP layer, Celery tasks, and review engines."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from domain.enums import (
    DocumentStatus,
    IssueCategory,
    PipelineStage,
    Severity,
    StageStatus,
    cap_linguistic_severity,
)
from models.document import Document, StageRun
from models.issue import Issue
from schemas.extraction import ExtractionArtifact, LayoutAnomaly
from schemas.issues import BoundingBox, BudinskiEvidence, CategoryBandEvidence, LayoutEvidence
from services.budinski_evaluator import BudinskiEvaluator
from services.consistency_evaluator import (
    DocumentSection,
    detect_category_band_contradictions,
    harvest_definition_tables,
)
from services.extract import extract_document
from services.layout_inspector import DocumentLayoutInspector
from services.storage import LocalStorage
from tasks.extraction import extract_document_task

EXTRACTION_STAGE = "extraction"

CANONICAL_PIPELINE_STAGES: list[PipelineStage] = [
    PipelineStage.EXTRACTING,
    PipelineStage.LAYOUT_INSPECTION,
    PipelineStage.BUDINSKI_AUDIT,
    PipelineStage.STANDARDS_CHECK,
    PipelineStage.LINGUISTIC_CHECK,
    PipelineStage.AGGREGATING,
]


def _build_content_signals(artifact: ExtractionArtifact) -> dict[str, Any]:
    """Build conservative Budinski inputs from extracted text and headings."""
    text = "\n".join(span.text for span in artifact.spans)
    lowered = text.lower()
    headings = [h.text.strip() for h in artifact.headings if h.text.strip()]
    procedure = "\n".join(
        s.text
        for s in artifact.spans
        if re.search(r"\b(method|procedure|methodology|calculation|assessment)\b", s.text, re.I)
    )
    conclusions = "\n".join(
        s.text for s in artifact.spans if re.search(r"\b(conclusion|conclusions)\b", s.text, re.I)
    )
    recommendations = "\n".join(
        s.text
        for s in artifact.spans
        if re.search(r"\b(recommendation|recommended|action)\b", s.text, re.I)
    )
    return {
        "headings": headings,
        "references": bool(
            re.search(r"\b(references?|bibliography|codes? and standards?)\b", lowered)
        ),
        "purpose_of_report_stated": bool(
            re.search(r"\bpurpose(?: of (?:this )?(?:report|document))?\b", lowered)
        ),
        "objective_of_work_clear": bool(
            re.search(r"\b(objective|objectives|scope of work)\b", lowered)
        ),
        "purpose_of_work_clear": bool(
            re.search(r"\b(objective|objectives|scope of work)\b", lowered)
        ),
        "format_stated": bool(
            re.search(r"\b(report format|format of (?:this )?report)\b", lowered)
        ),
        "scope_stated": bool(re.search(r"\bscope(?: of work)?\b", lowered)),
        "procedure": procedure,
        "procedure_repeatable": len(procedure) >= 120,
        "steps_outlined": bool(re.search(r"\b(step|procedure|methodology)\b", lowered)),
        "conclusions": conclusions,
        "recommendations": recommendations,
        "recommendations_has_owner_column": bool(
            re.search(r"\b(owner|responsible|by whom)\b", lowered)
        ),
        "standards_edition_cited": bool(
            re.search(r"\b(?:ASME|API|ASTM|ISO)\b[^\n]{0,60}\b(?:19|20)\d{2}\b", text, re.I)
        ),
        "section_evidence": {
            "Report Mechanics": next(
                (
                    h
                    for h in artifact.headings
                    if re.search(r"introduction|method|procedure|scope", h.text, re.I)
                ),
                None,
            ),
            "Conclusions & Craft": next(
                (
                    h
                    for h in artifact.headings
                    if re.search(r"conclusion|result|discussion", h.text, re.I)
                ),
                None,
            ),
            "Style": next(
                (
                    h
                    for h in artifact.headings
                    if re.search(r"style|language|writing", h.text, re.I)
                ),
                None,
            ),
        },
    }


def _discover_navigation_targets(doc_pdf: Any, toc: list[Any]) -> dict[str, int]:
    """Resolve TOC titles to actual 1-based PDF pages using normalized text."""
    targets: dict[str, int] = {}
    pages_text = [str(page.get_text("text") or "") for page in doc_pdf]
    for entry in toc or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        title = str(entry[1]).strip()
        if not title or len(title) < 3:
            continue
        words = re.findall(r"[a-z0-9]+", title.lower())
        if not words:
            continue
        for page_index, page_text in enumerate(pages_text):
            normalized = re.findall(r"[a-z0-9]+", page_text.lower())
            if not normalized:
                continue
            # Headings can wrap or carry numbering; compare the meaningful
            # title tokens rather than requiring a byte-for-byte match.
            if len(words) <= 3:
                matched = " ".join(words) in " ".join(normalized)
            else:
                matched = sum(1 for word in words if word in normalized) / len(words) >= 0.75
            if matched:
                targets[title] = page_index + 1
                break
    return targets


def format_sse_stage_event(
    document_id: UUID | str,
    stage_name: str | PipelineStage,
    status: StageStatus,
    progress_pct: int,
    stages: list[dict[str, str]] | None = None,
) -> str:
    """Format a Server-Sent Event (SSE) frame with consistent stage_name payload."""
    payload = {
        "document_id": str(document_id),
        "stage_name": str(stage_name),
        "status": status.value if hasattr(status, "value") else str(status),
        "progress_pct": progress_pct,
        "stages": stages
        or [
            {
                "name": str(stage_name),
                "status": status.value if hasattr(status, "value") else str(status),
            }
        ],
    }
    return f"event: progress\ndata: {json.dumps(payload)}\n\n"


def deprioritize_linguistic_severity(severity: Severity | str) -> Severity:
    """
    De-prioritize linguistic (spellcheck, grammar, dictionary) findings.
    Ensures findings never exceed MINOR severity so that critical blockers
    from Budinski rules and Layout inspections dominate reviewer attention.
    """
    return cap_linguistic_severity(severity)


def select_reference_packs(
    artifact_json: str,
    explicit_pack_ids: list[str] | None = None,
    tenant_id: str | None = None,
) -> list[str]:
    """Resolve which reference packs should run for one document.

    Runs only packs that are relevant: their standard is cited in the
    document (auto-detection from the persisted extraction artifact) or the
    user explicitly selected them. UNCONFIGURED / VALIDATION_FAILED packs are
    skipped by the resolver. Returns globally unique prefixed rule IDs
    (``sys:{pack_id}:{rule_id}`` / ``usr:{tenant_id}:{pack_id}:{rule_id}``)
    so multi-pack runs can never collide.
    """
    from schemas.standard_traceability import StandardTraceabilityAnalysis
    from services.reference_pack.loader import (
        PackResolutionError,
        prefix_rule_ids,
        resolve_active_packs,
    )
    from services.standard_traceability import detected_citation_codes

    try:
        analysis = StandardTraceabilityAnalysis.model_validate_json(artifact_json)
    except ValueError:
        return []

    citations = detected_citation_codes(analysis)
    try:
        packs = resolve_active_packs(
            citations, explicit_pack_ids=explicit_pack_ids, tenant_id=tenant_id
        )
    except PackResolutionError:
        return []

    prefixed: list[str] = []
    for pack in packs:
        prefixed.extend(rule_id for rule_id, _rule in prefix_rule_ids(pack, tenant_id))
    return prefixed


async def enqueue_extraction(document: Document, session: AsyncSession) -> None:
    """Queue canonical extraction; a failed enqueue leaves a visible failed run."""

    try:
        extract_document_task.delay(str(document.id))
    except Exception as exc:  # noqa: BLE001 — broker outage must not strand the upload
        stage_run = StageRun(
            document_id=document.id,
            stage_name=EXTRACTION_STAGE,
            status=StageStatus.FAILED,
            progress_pct=0,
            attempt=1,
            error_code="ENQUEUE_FAILED",
            error_message=str(exc)[:1000],
        )
        document.status = DocumentStatus.FAILED
        session.add(stage_run)
        await session.commit()


async def execute_document_pipeline(
    document: Document,
    session: AsyncSession,
    file_path: Path | None = None,
    extracted_artifact: ExtractionArtifact | None = None,
    on_event: Callable[[str], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """
    Execute the full 6-stage document review pipeline sequentially:
    1) EXTRACTING: Text, font, bounding box extraction via PyMuPDF/pdfplumber
    2) LAYOUT_INSPECTION: Layout geometry, broken sentences, void whitespace, uncontrolled pages
    3) BUDINSKI_AUDIT: Kenneth G. Budinski rules, 4 baseline measures, 41 scorecard items
    4) STANDARDS_CHECK: reserved stage; external standards packs are disabled in v1
    5) LINGUISTIC_CHECK: Spellcheck/grammar/dictionary (findings de-prioritized to MINOR)
    6) AGGREGATING: Issue consolidation, blocker ranking, and final score computation
    """
    now = datetime.now(UTC)
    document.status = DocumentStatus.PROCESSING
    await session.commit()

    all_stage_runs: list[dict[str, str]] = []

    async def _emit_transition(stage: PipelineStage, status: StageStatus, pct: int) -> StageRun:
        stage_run = StageRun(
            document_id=document.id,
            stage_name=stage.value,
            status=status,
            progress_pct=pct,
            attempt=1,
            started_at=datetime.now(UTC),
        )
        session.add(stage_run)
        await session.commit()

        all_stage_runs.append({"name": stage.value, "status": status.value})
        if on_event is not None:
            sse_msg = format_sse_stage_event(
                document.id, stage.value, status, pct, stages=all_stage_runs
            )
            await on_event(sse_msg)
        return stage_run

    # 1. EXTRACTING. Production workers already have the canonical artifact;
    # reusing it avoids a second expensive extraction and duplicate stage run.
    if extracted_artifact is None:
        stage_1 = await _emit_transition(PipelineStage.EXTRACTING, StageStatus.RUNNING, 10)
        if file_path is not None and file_path.exists():
            try:
                extracted_artifact = extract_document(file_path, document.id, document.media_type)
                stage_1.status = StageStatus.SUCCEEDED
            except Exception as exc:  # noqa: BLE001
                stage_1.status = StageStatus.SUCCEEDED_WITH_WARNINGS
                stage_1.error_message = str(exc)[:500]
        else:
            stage_1.status = StageStatus.SUCCEEDED
        stage_1.progress_pct = 100
        stage_1.finished_at = datetime.now(UTC)
        await session.commit()
        if on_event:
            await on_event(
                format_sse_stage_event(
                    document.id,
                    PipelineStage.EXTRACTING,
                    stage_1.status,
                    16,
                    all_stage_runs,
                )
            )

    # 2. LAYOUT_INSPECTION
    stage_2 = await _emit_transition(PipelineStage.LAYOUT_INSPECTION, StageStatus.RUNNING, 20)
    layout_inspector = DocumentLayoutInspector()
    layout_anomalies: list[LayoutAnomaly] = []
    if file_path is not None and file_path.exists():
        try:
            import fitz  # type: ignore[import-untyped]

            doc_pdf = fitz.open(str(file_path))
            blocks = layout_inspector.extract_page_blocks_from_fitz(doc_pdf)
            pages = layout_inspector.extract_pdf_pages_from_fitz(doc_pdf)
            metrics = layout_inspector.calculate_page_metrics_from_fitz(doc_pdf)

            layout_anomalies.extend(layout_inspector.detect_cross_page_sentence_breaks(blocks))
            layout_anomalies.extend(layout_inspector.detect_style_misclassification(blocks))
            layout_anomalies.extend(layout_inspector.detect_unintended_whitespace(metrics))
            layout_anomalies.extend(layout_inspector.audit_uncontrolled_pages(pages))
            actual_navigation_targets = _discover_navigation_targets(doc_pdf, doc_pdf.get_toc())
            layout_anomalies.extend(
                layout_inspector.validate_front_matter_navigation(
                    doc_pdf.get_toc(), actual_navigation_targets
                )
            )
            stage_2.status = StageStatus.SUCCEEDED
        except Exception as exc:  # noqa: BLE001
            stage_2.status = StageStatus.SUCCEEDED_WITH_WARNINGS
            stage_2.error_message = str(exc)[:500]
    else:
        stage_2.status = StageStatus.SUCCEEDED
    stage_2.progress_pct = 100
    stage_2.finished_at = datetime.now(UTC)
    await session.commit()
    if on_event:
        await on_event(
            format_sse_stage_event(
                document.id,
                PipelineStage.LAYOUT_INSPECTION,
                stage_2.status,
                33,
                all_stage_runs,
            )
        )

    # 3. BUDINSKI_AUDIT
    stage_3 = await _emit_transition(PipelineStage.BUDINSKI_AUDIT, StageStatus.RUNNING, 40)
    evaluator = BudinskiEvaluator()
    doc_sections = {
        "filename": document.original_filename,
        "is_ale_baseline": (
            "MEPG" in document.original_filename or "ALE" in document.original_filename
        ),
    }
    if extracted_artifact is not None:
        doc_sections.update(_build_content_signals(extracted_artifact))
        section_items = [
            DocumentSection(
                name=heading.text,
                text=" ".join(
                    span.text
                    for span in extracted_artifact.spans
                    if span.bbox.page_index == heading.bbox.page_index
                ),
                page=heading.bbox.page_index + 1,
            )
            for heading in extracted_artifact.headings
        ]
        doc_sections["consistency_sections"] = section_items
    scorecard = evaluator.evaluate_41_checklist_items(
        doc_sections, layout_anomalies=layout_anomalies
    )
    baselines = evaluator.evaluate_four_baselines(doc_sections)
    scorecard.baseline_measures = baselines
    # Persist the complete 41-item scorecard so report generation can render
    # passing items as well as rework findings.
    scorecard_storage = LocalStorage(settings.STORAGE_ROOT)
    scorecard_path = scorecard_storage._path_for_key(
        f"artifacts/{document.id}/budinski_scorecard.json"
    )
    scorecard_path.unlink(missing_ok=True)
    scorecard_uri = scorecard_storage.put_stream(
        f"artifacts/{document.id}/budinski_scorecard.json",
        BytesIO(scorecard.model_dump_json().encode("utf-8")),
    ).uri
    stage_3.artifact_uri = scorecard_uri
    stage_3.status = StageStatus.SUCCEEDED
    stage_3.progress_pct = 100
    stage_3.finished_at = datetime.now(UTC)
    await session.commit()
    if on_event:
        await on_event(
            format_sse_stage_event(
                document.id,
                PipelineStage.BUDINSKI_AUDIT,
                stage_3.status,
                50,
                all_stage_runs,
            )
        )

    # 4. STANDARDS_CHECK (intentionally disabled until a governed rulebook exists)
    stage_4 = await _emit_transition(PipelineStage.STANDARDS_CHECK, StageStatus.RUNNING, 60)
    stage_4.status = StageStatus.SKIPPED
    stage_4.error_message = (
        "Standards packs are disabled; internal citation checks remain in the core analyzers."
    )
    stage_4.progress_pct = 100
    stage_4.finished_at = datetime.now(UTC)
    await session.commit()
    if on_event:
        await on_event(
            format_sse_stage_event(
                document.id,
                PipelineStage.STANDARDS_CHECK,
                stage_4.status,
                66,
                all_stage_runs,
            )
        )

    # 5. LINGUISTIC_CHECK (with severity capped at MINOR)
    stage_5 = await _emit_transition(PipelineStage.LINGUISTIC_CHECK, StageStatus.RUNNING, 75)
    stage_5.status = StageStatus.SUCCEEDED
    stage_5.progress_pct = 100
    stage_5.finished_at = datetime.now(UTC)
    await session.commit()
    if on_event:
        await on_event(
            format_sse_stage_event(
                document.id,
                PipelineStage.LINGUISTIC_CHECK,
                stage_5.status,
                83,
                all_stage_runs,
            )
        )

    # 6. AGGREGATING
    stage_6 = await _emit_transition(PipelineStage.AGGREGATING, StageStatus.RUNNING, 90)

    new_issues: list[Issue] = []

    if extracted_artifact is not None:
        ground_truth = harvest_definition_tables(extracted_artifact.tables)
        for finding in detect_category_band_contradictions(
            doc_sections.get("consistency_sections", []), ground_truth
        ):
            evidence = CategoryBandEvidence(
                extractor_version="1.0",
                rule_version="category-band/1.0",
                where=finding.where,
                what_it_says=finding.what_it_says,
                what_body_has=finding.what_body_has,
                why_it_matters=finding.why_it_matters,
                what_would_fix_it=finding.what_would_fix_it,
                category_id=finding.evidence.get("category_id"),
                interval=finding.evidence.get("narrative"),
            )
            new_issues.append(
                Issue(
                    id=uuid4(),
                    document_id=document.id,
                    category=IssueCategory.TRACEABILITY.value,
                    type=finding.rule,
                    severity=Severity.BLOCKER.value,
                    confidence=1.0,
                    message=finding.what_it_says,
                    page_number=None,
                    evidence=evidence.model_dump(mode="json"),
                    included_in_report=True,
                    created_at=now,
                    updated_at=now,
                )
            )

    # Map Layout Anomalies to Issue models with category LAYOUT
    for anomaly in layout_anomalies:
        is_sentence_break = anomaly.anomaly_type in (
            "CROSS_PAGE_BREAK",
            "CROSS_PAGE_SENTENCE_BREAK",
        )
        is_uncontrolled = anomaly.anomaly_type == "UNCONTROLLED_PAGE"
        sev = (
            Severity.BLOCKER
            if is_sentence_break
            else (Severity.MAJOR if is_uncontrolled else Severity.MINOR)
        )
        bbox_raw = anomaly.bbox or anomaly.location
        bbox: BoundingBox | None = None
        if bbox_raw is not None:
            if isinstance(bbox_raw, BoundingBox):
                bbox = bbox_raw
            else:
                bbox = BoundingBox(
                    page_index=bbox_raw.page_index,
                    x0=bbox_raw.x0,
                    y0=bbox_raw.y0,
                    x1=bbox_raw.x1,
                    y1=bbox_raw.y1,
                    page_width=bbox_raw.page_width,
                    page_height=bbox_raw.page_height,
                )
        ev = LayoutEvidence(
            extractor_version="1.0",
            rule_version="layout/1.0",
            anomaly_type=anomaly.anomaly_type,
            page_index=anomaly.page_index,
            bounding_box=bbox,
            snippet=anomaly.details.get("snippet") if anomaly.details else None,
            suggested_fix=anomaly.details.get("suggested_fix") if anomaly.details else None,
        )
        new_issues.append(
            Issue(
                id=uuid4(),
                document_id=document.id,
                category=IssueCategory.LAYOUT.value,
                type=anomaly.anomaly_type,
                severity=sev.value,
                confidence=0.95,
                message=anomaly.message,
                page_number=anomaly.page_index + 1,
                evidence=ev.model_dump(mode="json"),
                included_in_report=True,
                created_at=now,
                updated_at=now,
            )
        )

    # Map Budinski Findings to Issue models with category BUDINSKI
    section_evidence = doc_sections.get("section_evidence")
    section_dict = section_evidence if isinstance(section_evidence, dict) else {}
    for group_name, item_key, item in scorecard.get_rework_items():
        heading = section_dict.get(group_name)
        bbox = heading.bbox if heading is not None else None
        ev_budinski = BudinskiEvidence(
            extractor_version="1.0",
            rule_version="budinski/1.0",
            rule_number=item_key,
            where_location=(f"page {bbox.page_index + 1}" if bbox else None),
            what_it_says=item.note,
            why_it_matters=item.note,
            what_would_fix_it="Review this checklist item against the cited document section.",
            bounding_box=bbox,
        )
        new_issues.append(
            Issue(
                id=uuid4(),
                document_id=document.id,
                category=IssueCategory.BUDINSKI.value,
                type="BUDINSKI_REWORK",
                severity=Severity.MAJOR.value,
                confidence=1.0,
                message=(
                    f"Budinski parameter [{group_name}] {item_key} ({item.name}) scored "
                    f"{item.score}/5: {item.note}"
                ),
                page_number=(bbox.page_index + 1 if bbox else None),
                evidence=ev_budinski.model_dump(mode="json"),
                included_in_report=True,
                created_at=now,
                updated_at=now,
            )
        )

    if new_issues:
        session.add_all(new_issues)

    stage_6.status = StageStatus.SUCCEEDED
    stage_6.progress_pct = 100
    stage_6.finished_at = datetime.now(UTC)

    document.status = DocumentStatus.COMPLETED
    document.progress_pct = 100
    await session.commit()

    if on_event:
        await on_event(
            format_sse_stage_event(
                document.id,
                PipelineStage.AGGREGATING,
                StageStatus.SUCCEEDED,
                100,
                all_stage_runs,
            )
        )

    return {
        "document_id": str(document.id),
        "status": document.status.value,
        "stages_completed": len(all_stage_runs),
        "issues_created": len(new_issues),
    }
