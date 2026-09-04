"""Tests for Celery extraction task and pipeline enqueue behavior."""

import asyncio
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus, StageStatus
from models.document import Document
from services.pipeline import enqueue_extraction
from tasks.extraction import _run_extraction, _sanitize_error


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
