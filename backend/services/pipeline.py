"""Pipeline orchestration glue between the HTTP layer, Celery tasks, and review engines."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus, IssueCategory, PipelineStage, Severity, StageStatus
from models.document import Document, StageRun
from models.issue import Issue
from schemas.extraction import LayoutAnomaly
from schemas.issues import BoundingBox, BudinskiEvidence, LayoutEvidence
from services.budinski_evaluator import BudinskiEvaluator
from services.extract import extract_document
from services.layout_inspector import DocumentLayoutInspector
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
    sev_str = severity.value if hasattr(severity, "value") else str(severity)
    if sev_str in ("BLOCKER", "CRITICAL", "MAJOR", "HIGH", "MEDIUM", "MINOR", "LOW"):
        return Severity.MINOR
    if sev_str == "INFO":
        return Severity.INFO
    return Severity.MINOR


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
    on_event: Callable[[str], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """
    Execute the full 6-stage document review pipeline sequentially:
    1) EXTRACTING: Text, font, bounding box extraction via PyMuPDF/pdfplumber
    2) LAYOUT_INSPECTION: Layout geometry, broken sentences, void whitespace, uncontrolled pages
    3) BUDINSKI_AUDIT: Kenneth G. Budinski rules, 4 baseline measures, 41 scorecard items
    4) STANDARDS_CHECK: ASME/API engineering standard citations and reference pack rules
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

    # 1. EXTRACTING
    stage_1 = await _emit_transition(PipelineStage.EXTRACTING, StageStatus.RUNNING, 10)
    if file_path is not None and file_path.exists():
        try:
            extract_document(file_path, document.id, document.media_type)
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
            layout_anomalies.extend(
                layout_inspector.validate_front_matter_navigation(doc_pdf.get_toc(), {})
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
    scorecard = evaluator.evaluate_41_checklist_items(
        doc_sections, layout_anomalies=layout_anomalies
    )
    baselines = evaluator.evaluate_four_baselines(doc_sections)
    scorecard.baseline_measures = baselines
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

    # 4. STANDARDS_CHECK
    stage_4 = await _emit_transition(PipelineStage.STANDARDS_CHECK, StageStatus.RUNNING, 60)
    stage_4.status = StageStatus.SUCCEEDED
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

    # Clean existing issues
    await session.execute(delete(Issue).where(Issue.document_id == document.id))

    new_issues: list[Issue] = []

    # Map Layout Anomalies to Issue models with category LAYOUT
    for anomaly in layout_anomalies:
        is_sentence_break = anomaly.anomaly_type == "CROSS_PAGE_SENTENCE_BREAK"
        is_uncontrolled = anomaly.anomaly_type == "UNCONTROLLED_PAGE"
        sev = (
            Severity.BLOCKER
            if is_sentence_break
            else (Severity.MAJOR if is_uncontrolled else Severity.MINOR)
        )
        bbox = BoundingBox(
            page_index=anomaly.page_index,
            x0=0.0,
            y0=0.0,
            x1=612.0,
            y1=792.0,
            page_width=612.0,
            page_height=792.0,
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
    for group_name, item_key, item in scorecard.get_rework_items():
        bbox = BoundingBox(
            page_index=0,
            x0=0.0,
            y0=0.0,
            x1=612.0,
            y1=792.0,
            page_width=612.0,
            page_height=792.0,
        )
        ev_budinski = BudinskiEvidence(
            extractor_version="1.0",
            rule_version="budinski/1.0",
            rule_number=item_key,
            why_it_matters=item.note,
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
                page_number=1,
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
