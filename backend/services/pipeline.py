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

from sqlalchemy import select
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
from services.report_synthesizer import ReportSynthesizer
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
    """Build document-specific Budinski evidence from heading-bounded text."""
    headings = sorted(
        (heading for heading in artifact.headings if heading.text.strip()),
        key=lambda heading: (heading.bbox.page_index, heading.bbox.y0),
    )
    heading_texts = [heading.text.strip() for heading in headings]
    section_patterns = {
        "executive_summary": re.compile(r"\b(?:executive\s+summary|abstract)\b", re.I),
        "introduction": re.compile(r"\b(?:introduction|background|purpose\s+and\s+scope)\b", re.I),
        "methodology": re.compile(r"\b(?:methodology|methods?|procedure|approach)\b", re.I),
        "results": re.compile(r"\b(?:results?|findings|analysis)\b", re.I),
        "discussion": re.compile(r"\bdiscussion\b", re.I),
        "conclusions": re.compile(r"\bconclusions?\b", re.I),
        "recommendations": re.compile(r"\brecommendations?\b", re.I),
    }
    section_lines: dict[str, list[tuple[int, str]]] = {key: [] for key in section_patterns}
    heading_index = 0
    active_section: str | None = None
    for span in sorted(artifact.spans, key=lambda item: (item.bbox.page_index, item.bbox.y0)):
        position = (span.bbox.page_index, span.bbox.y0)
        while heading_index < len(headings) and (
            headings[heading_index].bbox.page_index,
            headings[heading_index].bbox.y0,
        ) <= position:
            heading_text = headings[heading_index].text.strip()
            active_section = next(
                (key for key, pattern in section_patterns.items() if pattern.search(heading_text)),
                None,
            )
            heading_index += 1
        if active_section and span.text.strip():
            section_lines[active_section].append((span.bbox.page_index + 1, span.text.strip()))

    section_text = {
        key: "\n".join(text for _page, text in lines) for key, lines in section_lines.items()
    }
    section_pages = {
        key: sorted({page for page, _text in lines}) for key, lines in section_lines.items()
    }
    consistency_sections = [
        DocumentSection(
            name=section_name.replace("_", " ").title(),
            text=" ".join(text for line_page, text in lines if line_page == page),
            page=page,
        )
        for section_name in ("executive_summary", "conclusions")
        for page in section_pages[section_name]
        for lines in (section_lines[section_name],)
    ]
    text = "\n".join(span.text for span in artifact.spans)
    lowered = text.lower()
    procedure = section_text["methodology"]
    conclusions = section_text["conclusions"]
    recommendations = section_text["recommendations"]
    introduction = section_text["introduction"]
    rec_lines = [line for line in recommendations.splitlines() if line.strip()]
    owner_pattern = re.compile(
        r"\b(?:owner|responsible(?:\s+party)?|assigned\s+to)\s*[:=-]?\s*[A-Z][\w.-]+",
        re.I,
    )
    target_date_pattern = re.compile(
        r"\b(?:by|before|due(?:\s+date)?|no\s+later\s+than|target(?:\s+date)?)\s+"
        r"(?:\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}|[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}|"
        r"(?:end\s+of\s+)?20\d{2}|Q[1-4]\s+20\d{2})\b",
        re.I,
    )
    recommendations_actionable = bool(rec_lines) and all(
        owner_pattern.search(line) and target_date_pattern.search(line) for line in rec_lines
    )
    procedure_repeatable = bool(
        len(procedure) >= 120
        and re.search(r"\b(?:step\s*\d+|\d+[.)]|first|then|finally)\b", procedure, re.I)
        and re.search(
            r"\b(?:calculate|measur|test|inspect|equation|formula|parameter|criteria)\w*\b",
            procedure,
            re.I,
        )
    )
    purpose_explicit = bool(
        re.search(r"\bpurpose\s+of\s+(?:this\s+)?(?:report|document)\b", introduction, re.I)
    )
    objective_explicit = bool(
        re.search(r"\bobjective\s+of\s+(?:the\s+)?(?:work|study|project)\b", introduction, re.I)
    )
    section_evidence: dict[str, Any] = {}
    section_details: dict[str, dict[str, Any] | None] = {}
    for group, section_name in (
        ("Report Mechanics", "introduction"),
        ("Conclusions & Craft", "conclusions"),
        ("Style", "executive_summary"),
    ):
        lines = section_lines[section_name]
        matching_heading = next(
            (
                heading
                for heading in headings
                if section_patterns[section_name].search(heading.text)
            ),
            None,
        )
        section_evidence[group] = matching_heading
    for section_name, lines in section_lines.items():
        pattern = section_patterns[section_name]
        matching_heading = next(
            (heading for heading in headings if pattern.search(heading.text)), None
        )
        section_details[section_name] = (
            {
                "heading": matching_heading.text.strip(),
                "page": matching_heading.bbox.page_index + 1,
                "excerpt": lines[0][1][:240] if lines else "",
            }
            if matching_heading
            else None
        )
    expected_order = ["executive_summary", "introduction", "methodology", "results", "discussion", "conclusions", "recommendations"]
    detected_order: list[str] = []
    for heading in headings:
        section = next(
            (key for key, pattern in section_patterns.items() if pattern.search(heading.text)),
            None,
        )
        if section and (not detected_order or detected_order[-1] != section):
            detected_order.append(section)
    section_order_positions = [expected_order.index(key) for key in detected_order]
    section_order_logical = bool(section_order_positions) and section_order_positions == sorted(
        section_order_positions
    )
    abbreviation_section_present = any(
        re.search(r"\b(?:abbreviations?|acronyms?|glossary)\b", heading, re.I)
        for heading in heading_texts
    )
    acronym_tokens = set(re.findall(r"\b[A-Z][A-Z0-9/-]{1,}\b", text))
    has_unexplained_jargon = len(acronym_tokens) > 12 and not abbreviation_section_present
    summary_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", section_text["executive_summary"]))
    results_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", section_text["results"]))
    conclusion_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", conclusions))
    repeated_numbers = summary_numbers & results_numbers & conclusion_numbers
    counts_repeated_thrice = len(repeated_numbers) >= 3
    return {
        "headings": heading_texts,
        "executive_summary": section_text["executive_summary"],
        "introduction": introduction,
        "procedure": procedure,
        "results": section_text["results"],
        "discussion": section_text["discussion"],
        "conclusions": conclusions,
        "recommendations": [
            {
                "text": line,
                "owner": bool(owner_pattern.search(line)),
                "date": bool(target_date_pattern.search(line)),
            }
            for line in rec_lines
        ],
        "recommendations_actionable": recommendations_actionable,
        "recommendations_actionable_reason": (
            f"{sum(bool(owner_pattern.search(line)) for line in rec_lines)} of {len(rec_lines)} "
            "recommendation line(s) name an owner, and "
            f"{sum(bool(target_date_pattern.search(line)) for line in rec_lines)} include a target date."
        ),
        "purpose_of_report_stated": purpose_explicit,
        "purpose_distinct_from_objective": purpose_explicit and objective_explicit,
        "purpose_distinct_reason": (
            "Introduction states a report purpose and separately identifies the work objective."
            if purpose_explicit and objective_explicit
            else "Introduction does not establish both a report purpose and a distinct work objective."
        ),
        "section_evidence": section_evidence,
        "section_details": section_details,
        "section_pages": section_pages,
        "consistency_sections": consistency_sections,
        "section_order_logical": section_order_logical,
        "has_unexplained_jargon": has_unexplained_jargon,
        "abbreviation_section_present": abbreviation_section_present,
        "counts_repeated_thrice": counts_repeated_thrice,
        "has_tables_or_figures": bool(artifact.tables)
        or bool(re.search(r"\b(?:table|figure)\s+\d", text, re.I)),
        "objective_tone": not bool(
            re.search(r"\b(?:I believe|we believe|best ever|unmatched|revolutionary)\b", text, re.I)
        ),
        "references": bool(
            re.search(r"\b(references?|bibliography|codes? and standards?)\b", lowered)
        ),
        "objective_of_work_clear": bool(
            re.search(r"\b(objective|objectives|scope of work)\b", introduction, re.I)
        ),
        "purpose_of_work_clear": bool(
            re.search(r"\b(?:purpose of (?:the )?(?:work|study|project)|objective|scope of work)\b", introduction, re.I)
        ),
        "format_stated": bool(
            re.search(r"\b(?:report format|format of (?:this )?report|organized into|structured as)\b", introduction, re.I)
        ),
        "scope_stated": bool(re.search(r"\bscope(?: of work)?\b", introduction, re.I)),
        "procedure_repeatable": procedure_repeatable,
        "procedure_repeatable_reason": (
            "Methodology includes sequenced steps and measurable methods or criteria."
            if procedure_repeatable
            else "Methodology lacks extracted sequenced steps and measurable methods or criteria."
        ),
        "engineering_approach_logical": bool(
            procedure_repeatable
            and re.search(
                r"\b(?:then|subsequently|following|step\s*\d+|\d+[.)])\b",
                procedure,
                re.I,
            )
        ),
        "has_previous_work_baseline": bool(
            re.search(r"\b(?:previous|prior|historical|baseline|earlier\s+study)\b", text, re.I)
        ),
        "has_external_benchmark": bool(
            re.search(r"\b(?:benchmark|compared\s+with|compared\s+against)\b", text, re.I)
            and bool(re.search(r"\b(?:reference|study|published|literature)\b", text, re.I))
        ),
        "sufficient_background": len(introduction.split()) >= 80,
        "value_clearly_stated": bool(
            section_text["executive_summary"]
            and re.search(
                r"\b(?:result|conclud|demonstrat|recommend|benefit|decision|can\s+operate)\w*\b",
                section_text["executive_summary"],
                re.I,
            )
        ),
        "objectives_met": bool(
            re.search(
                r"\b(?:objective|objectives)\b.{0,100}\b(?:met|achieved|addressed)\b",
                text,
                re.I,
            )
        ),
        "timely": False,
        "steps_outlined": bool(re.search(r"\b(?:step\s*\d+|\d+[.)]|first|then|finally)\b", procedure, re.I)),
        "recommendations_has_owner_column": all(
            bool(owner_pattern.search(line)) for line in rec_lines
        ),
        "standards_edition_cited": bool(
            re.search(r"\b(?:ASME|API|ASTM|ISO)\b[^\n]{0,60}\b(?:19|20)\d{2}\b", text, re.I)
        ),
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
    doc_sections: dict[str, Any] = {
        "filename": document.original_filename,
    }
    consistency_findings: list[Any] = []

    if extracted_artifact is not None:
        doc_sections.update(_build_content_signals(extracted_artifact))
        cover = extracted_artifact.cover_metadata
        doc_sections.update(
            {
                "doc_id": cover.document_number or document.original_filename,
                "rev": cover.revision or "not supplied",
                "date": cover.document_date or "not supplied",
            }
        )
        section_items = doc_sections.get("consistency_sections", [])
        doc_sections["consistency_sections"] = section_items
        ground_truth = harvest_definition_tables(extracted_artifact.tables)
        consistency_findings = detect_category_band_contradictions(section_items, ground_truth)
        doc_sections["has_definition_contradiction"] = bool(consistency_findings)
        doc_sections["consistency_finding_summaries"] = [
            {
                "type": finding.rule,
                "message": finding.what_it_says,
                "page": finding.evidence.get("page"),
            }
            for finding in consistency_findings
        ]

    existing_issues = list(
        (
            await session.execute(select(Issue).where(Issue.document_id == document.id))
        ).scalars()
    )
    language_issues = [
        issue
        for issue in existing_issues
        if str(issue.category).upper() in {"LINGUISTIC", "ISSUECATEGORY.LINGUISTIC"}
    ]
    key_section_pages = {
        page
        for section in ("executive_summary", "conclusions", "recommendations")
        for page in doc_sections.get("section_pages", {}).get(section, [])
    }
    doc_sections["language_findings"] = language_issues
    doc_sections["language_faults_in_key_sections"] = any(
        issue.page_number in key_section_pages for issue in language_issues
    )
    doc_sections["blockers_count"] = sum(str(issue.severity).upper() == "BLOCKER" for issue in existing_issues)
    doc_sections["majors_count"] = sum(str(issue.severity).upper() == "MAJOR" for issue in existing_issues)
    doc_sections["minors_count"] = sum(str(issue.severity).upper() == "MINOR" for issue in existing_issues)
    scorecard = evaluator.evaluate_41_checklist_items(
        doc_sections, layout_anomalies=layout_anomalies
    )
    baselines = evaluator.evaluate_four_baselines(doc_sections)
    scorecard.baseline_measures = baselines
    conclusion_scores = [
        scorecard.conclusions_and_craft.conclusions_clear.score
        if scorecard.conclusions_and_craft
        else None,
        scorecard.technical_content.conclusions_supported.score
        if scorecard.technical_content
        else None,
    ]
    if doc_sections.get("conclusions") and (
        not baselines.conclusions_valid
        or any(score is not None and score <= 2 for score in conclusion_scores)
    ):
        scorecard.demonstration_rewrite = ReportSynthesizer().generate_demonstration_rewrite(
            doc_sections, consistency_findings
        )
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
        for finding in consistency_findings:
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
                    page_number=(
                        finding.evidence.get("page")
                        if isinstance(finding.evidence.get("page"), int)
                        else None
                    ),
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
    section_dict: dict[str, Any] = section_evidence if isinstance(section_evidence, dict) else {}
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
