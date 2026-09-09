"""Tests for Celery extraction task and pipeline enqueue behavior."""

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus, IssueCategory, PipelineStage, Severity, StageStatus
from models.document import Document
from schemas.extraction import ExtractionArtifact, LayoutAnomaly
from schemas.issues import BoundingBox
from schemas.linguistic import LinguisticFinding
from services.pipeline import (
    CANONICAL_PIPELINE_STAGES,
    deprioritize_linguistic_severity,
    enqueue_extraction,
    execute_document_pipeline,
    format_sse_stage_event,
)
from services.storage import LocalStorage
from tasks.extraction import (
    _run_aggregation_stage,
    _run_ambiguity_stage,
    _run_duplicate_stage,
    _run_extraction,
    _run_grammar_stage,
    _run_ref_drift_stage,
    _run_revision_stage,
    _run_spellcheck_stage,
    _run_standard_stage,
    _run_table_math_stage,
    _sanitize_error,
)


def test_sanitize_error_bounds_message() -> None:
    """Public error messages are truncated and never carry class internals."""

    code, message = _sanitize_error(ValueError("x" * 5000))

    assert code == "VALUEERROR"
    assert len(message) == 1000


@dataclass
class _EmptyResult:
    scalar_one_or_none: object


class _MissingSession:
    """Async session that reports no matching document on every query."""

    async def execute(self, *_args: object, **_kwargs: object) -> _EmptyResult:
        return _EmptyResult(scalar_one_or_none=lambda: None)


class _MissingFactory:
    def __call__(self) -> "_MissingFactory":
        return self

    async def __aenter__(self) -> _MissingSession:
        return _MissingSession()

    async def __aexit__(self, *_args: object) -> None:
        return None


def test_run_extraction_skips_missing_document() -> None:
    """A queued id for a deleted document degrades to a skip result."""

    missing = uuid.uuid4()

    with patch("tasks.extraction.async_session_factory", _MissingFactory()):
        result = asyncio.run(_run_extraction(str(missing)))

    assert result == {"document_id": str(missing), "skipped": True}


def test_enqueue_extraction_failure_records_failed_run() -> None:
    """A broker outage strands the upload as FAILED with an explicit stage run."""

    document = Document(id=uuid.uuid4())
    session = AsyncMock(spec=AsyncSession)

    with patch("services.pipeline.extract_document_task") as task:
        task.delay.side_effect = RuntimeError("redis down")
        asyncio.run(enqueue_extraction(document, session))

    session.add.assert_called_once()
    session.commit.assert_called_once()
    assert document.status == DocumentStatus.FAILED
    stage_run = session.add.call_args.args[0]
    assert stage_run.status == StageStatus.FAILED
    assert stage_run.error_code == "ENQUEUE_FAILED"


def test_revision_failure_preserves_successful_extraction(tmp_path: Path) -> None:
    """An isolated analyzer failure yields warnings, not document failure."""

    document = Document(id=uuid.uuid4(), original_filename="Report_Rev-A.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch("tasks.extraction.analyze_revision", side_effect=ValueError("bad table")),
    ):
        failed = asyncio.run(
            _run_revision_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is True
    assert stage_run.status == StageStatus.FAILED


def test_standard_failure_finalizes_with_warnings(tmp_path: Path) -> None:
    """The final independent analyzer reports degradation without data loss."""

    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)
    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch(
            "tasks.extraction.analyze_standard_traceability",
            side_effect=ValueError("bad references"),
        ),
    ):
        asyncio.run(
            _run_standard_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
                prior_degraded=False,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert stage_run.status == StageStatus.FAILED
    assert document.status is None
    assert document.progress_pct is None


def test_table_math_stage_success(tmp_path: Path) -> None:
    """Table math stage succeeds, sets status, and persists artifact."""

    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        failed = asyncio.run(
            _run_table_math_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is False
    assert stage_run.status == StageStatus.SUCCEEDED
    assert stage_run.progress_pct == 100
    assert stage_run.artifact_uri is not None


def test_table_math_failure_preserves_successful_extraction(tmp_path: Path) -> None:
    """An isolated table math analyzer failure yields warnings without crashing."""

    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch(
            "tasks.extraction.analyze_table_math",
            side_effect=ValueError("bad table structure"),
        ),
    ):
        failed = asyncio.run(
            _run_table_math_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is True
    assert stage_run.status == StageStatus.FAILED
    assert stage_run.error_code == "VALUEERROR"


def test_ref_drift_stage_success(tmp_path: Path) -> None:
    """Reference drift stage succeeds, sets status, and persists artifact."""

    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        failed = asyncio.run(
            _run_ref_drift_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is False
    assert stage_run.status == StageStatus.SUCCEEDED
    assert stage_run.progress_pct == 100
    assert stage_run.artifact_uri is not None


def test_ref_drift_failure_preserves_successful_extraction(tmp_path: Path) -> None:
    """An isolated reference drift failure yields warnings without crashing."""

    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch(
            "tasks.extraction.analyze_ref_drift",
            side_effect=ValueError("corrupted toc"),
        ),
    ):
        failed = asyncio.run(
            _run_ref_drift_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is True
    assert stage_run.status == StageStatus.FAILED
    assert stage_run.error_code == "VALUEERROR"


def test_aggregation_stage_success(tmp_path: Path) -> None:
    """Aggregation stage executes, persists artifact, and writes issues."""
    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        failed = asyncio.run(
            _run_aggregation_stage(
                session,
                LocalStorage(tmp_path),
                document,
                failed_stages=[],
                prior_degraded=False,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is False
    assert stage_run.status == StageStatus.SUCCEEDED
    assert stage_run.progress_pct == 100
    assert stage_run.artifact_uri is not None
    assert document.status == DocumentStatus.COMPLETED
    assert document.progress_pct == 100


def test_aggregation_stage_handles_failed_stages_with_warnings(tmp_path: Path) -> None:
    """Failed upstream stages produce synthetic issues and degrade document status."""
    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        failed = asyncio.run(
            _run_aggregation_stage(
                session,
                LocalStorage(tmp_path),
                document,
                failed_stages=[("table_math", "TIMEOUT", True)],
                prior_degraded=True,
            )
        )

    stage_run = session.add.call_args.args[0]
    assert failed is False
    assert stage_run.status == StageStatus.SUCCEEDED
    assert document.status == DocumentStatus.COMPLETED_WITH_WARNINGS
    assert document.progress_pct == 100
    # Verified that session.add_all was called with persisted issues
    session.add_all.assert_called_once()
    issues = session.add_all.call_args.args[0]
    assert len(issues) == 1
    assert issues[0].type == "STAGE_FAILURE"


def test_aggregation_stage_can_defer_document_completion(tmp_path: Path) -> None:
    """Core aggregation must not expose a completed document before review audit stages run."""
    document = Document(id=uuid.uuid4(), status=DocumentStatus.PROCESSING)
    session = AsyncMock(spec=AsyncSession)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        failed = asyncio.run(
            _run_aggregation_stage(
                session,
                LocalStorage(tmp_path),
                document,
                failed_stages=[],
                prior_degraded=False,
                finalize_document_status=False,
            )
        )

    assert failed is False
    assert document.status == DocumentStatus.PROCESSING
    assert document.progress_pct is None


def test_spellcheck_stage_success_and_failure_isolation(tmp_path: Path) -> None:
    """Spellcheck stage executes with isolated failure handling."""
    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch("tasks.extraction.get_approved_dictionary_terms", AsyncMock(return_value=set())),
    ):
        failed = asyncio.run(
            _run_spellcheck_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )
    assert failed is False

    # Failure isolation
    with (
        patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)),
        patch(
            "tasks.extraction.get_approved_dictionary_terms",
            AsyncMock(side_effect=RuntimeError("db error")),
        ),
    ):
        failed = asyncio.run(
            _run_spellcheck_stage(
                session,
                LocalStorage(tmp_path),
                document,
                artifact,
            )
        )
    assert failed is True


def test_grammar_duplicate_ambiguity_stage_success(tmp_path: Path) -> None:
    """Grammar, duplicate, and ambiguity stages execute and persist cleanly."""
    document = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=document.id)

    with patch("tasks.extraction._latest_attempt", AsyncMock(return_value=1)):
        g_failed = asyncio.run(
            _run_grammar_stage(session, LocalStorage(tmp_path), document, artifact)
        )
        d_failed = asyncio.run(
            _run_duplicate_stage(session, LocalStorage(tmp_path), document, artifact)
        )
        a_failed = asyncio.run(
            _run_ambiguity_stage(session, LocalStorage(tmp_path), document, artifact)
        )

    assert g_failed is False
    assert d_failed is False
    assert a_failed is False


def test_format_sse_stage_event() -> None:
    """format_sse_stage_event builds well-formed SSE progress frames."""
    doc_id = uuid.uuid4()
    msg = format_sse_stage_event(doc_id, PipelineStage.LAYOUT_INSPECTION, StageStatus.RUNNING, 25)
    assert msg.startswith("event: progress\ndata: {")
    assert f'"document_id": "{doc_id}"' in msg
    assert '"stage_name": "LAYOUT_INSPECTION"' in msg
    assert '"status": "RUNNING"' in msg
    assert '"progress_pct": 25' in msg
    assert msg.endswith("\n\n")


def test_deprioritize_linguistic_findings() -> None:
    """Linguistic and dictionary findings are capped at MINOR severity."""
    # Critical and high severities are clamped to MINOR
    assert deprioritize_linguistic_severity(Severity.BLOCKER) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.CRITICAL) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.MAJOR) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.HIGH) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.MEDIUM) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.MINOR) == Severity.MINOR
    assert deprioritize_linguistic_severity(Severity.LOW) == Severity.MINOR

    # INFO remains INFO
    assert deprioritize_linguistic_severity(Severity.INFO) == Severity.INFO

    # String input support
    assert deprioritize_linguistic_severity("BLOCKER") == Severity.MINOR
    assert deprioritize_linguistic_severity("CRITICAL") == Severity.MINOR
    assert deprioritize_linguistic_severity("INFO") == Severity.INFO


def test_linguistic_schema_caps_legacy_high_severity() -> None:
    """Legacy linguistic artifacts cannot promote findings above MINOR."""
    finding = LinguisticFinding(
        type="SPELLCHECK_TYPO",
        message="Typo",
        severity=Severity.BLOCKER,
        original_text="teh",
        location=BoundingBox(
            page_index=0,
            x0=0.0,
            y0=0.0,
            x1=1.0,
            y1=1.0,
            page_width=612.0,
            page_height=792.0,
        ),
    )
    assert finding.severity == Severity.MINOR


def test_pipeline_stages_and_sse_events() -> None:
    """execute_document_pipeline sequences all 6 stages and emits SSE frames."""
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="MEPG_ALE_Test.pdf")
    session = AsyncMock(spec=AsyncSession)

    events: list[str] = []

    async def _capture_event(event_str: str) -> None:
        events.append(event_str)

    result = asyncio.run(
        execute_document_pipeline(
            document=doc,
            session=session,
            file_path=None,
            on_event=_capture_event,
        )
    )

    assert result["document_id"] == str(doc_id)
    assert result["status"] == "COMPLETED"
    assert len(events) > 0

    # Ensure all 6 canonical stages were referenced in events
    for stage in CANONICAL_PIPELINE_STAGES:
        assert any(stage.value in ev for ev in events), f"Missing stage {stage.value} in SSE events"

    # Validate structure of SSE events
    for ev in events:
        assert ev.startswith("event: progress\ndata: ")
        assert ev.endswith("\n\n")


def test_pipeline_reuses_worker_extraction_artifact() -> None:
    """The worker's review branch must not extract the document a second time."""
    doc = Document(id=uuid.uuid4(), original_filename="Report.pdf")
    session = AsyncMock(spec=AsyncSession)
    artifact = ExtractionArtifact(document_id=doc.id)

    with patch("services.pipeline.extract_document", side_effect=AssertionError("re-extracted")):
        result = asyncio.run(
            execute_document_pipeline(
                document=doc,
                session=session,
                file_path=Path("source.pdf"),
                extracted_artifact=artifact,
            )
        )

    assert result["status"] == "COMPLETED"
    assert all(
        stage_run.stage_name != PipelineStage.EXTRACTING.value
        for stage_run in session.add.call_args_list
    )


def test_pipeline_creates_layout_blocker_issues() -> None:
    """Layout inspection cross-page breaks produce BLOCKER issues.

    Also verifies uncontrolled pages produce MAJOR issues and unintended whitespace MINOR.
    """
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="MEPG_Sample.pdf")
    session = AsyncMock(spec=AsyncSession)

    anomalies = [
        LayoutAnomaly(
            anomaly_type="CROSS_PAGE_SENTENCE_BREAK",
            page_index=20,
            message="Sentence broken across page 20-21",
            details={"snippet": "Table 6-3 and"},
        ),
        LayoutAnomaly(
            anomaly_type="UNCONTROLLED_PAGE",
            page_index=55,
            message="Attachment page without controlled document header",
            details={},
        ),
        LayoutAnomaly(
            anomaly_type="UNINTENDED_WHITESPACE",
            page_index=15,
            message="Void whitespace area detected",
            details={},
        ),
    ]

    with patch("services.pipeline.DocumentLayoutInspector") as mock_inspector_cls:
        inspector_instance = mock_inspector_cls.return_value
        inspector_instance.detect_cross_page_sentence_breaks.return_value = [anomalies[0]]
        inspector_instance.audit_uncontrolled_pages.return_value = [anomalies[1]]
        inspector_instance.detect_unintended_whitespace.return_value = [anomalies[2]]
        inspector_instance.detect_style_misclassification.return_value = []
        inspector_instance.validate_front_matter_navigation.return_value = []

        fake_pdf = Path("fake.pdf")
        with patch("pathlib.Path.exists", return_value=True), patch("fitz.open"):
            asyncio.run(
                execute_document_pipeline(
                    document=doc,
                    session=session,
                    file_path=fake_pdf,
                )
            )

    # Check session.add_all was called with issues
    session.add_all.assert_called_once()
    issues = session.add_all.call_args.args[0]
    layout_issues = [i for i in issues if i.category == IssueCategory.LAYOUT.value]
    assert len(layout_issues) == 3

    break_issue = next(i for i in layout_issues if i.type == "CROSS_PAGE_SENTENCE_BREAK")
    assert break_issue.severity == Severity.BLOCKER.value

    uncontrolled_issue = next(i for i in layout_issues if i.type == "UNCONTROLLED_PAGE")
    assert uncontrolled_issue.severity == Severity.MAJOR.value

    whitespace_issue = next(i for i in layout_issues if i.type == "UNINTENDED_WHITESPACE")
    assert whitespace_issue.severity == Severity.MINOR.value
