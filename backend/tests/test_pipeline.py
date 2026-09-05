"""Tests for Celery extraction task and pipeline enqueue behavior."""

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus, StageStatus
from models.document import Document
from schemas.extraction import ExtractionArtifact
from services.pipeline import enqueue_extraction
from services.storage import LocalStorage
from tasks.extraction import (
    _run_extraction,
    _run_ref_drift_stage,
    _run_revision_stage,
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
    assert document.status == DocumentStatus.COMPLETED_WITH_WARNINGS
    assert document.progress_pct == 100


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
