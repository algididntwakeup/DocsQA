"""Celery task for the extraction stage of the Document QC pipeline."""

import asyncio
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from celery.utils.log import get_task_logger
from sqlalchemy import select

from core.celery_app import celery_app
from core.config import settings
from db.session import async_session_factory
from domain.enums import DocumentStatus, StageStatus
from models.document import Document, StageRun
from services.extract import extract_document
from services.storage import LocalStorage

logger = get_task_logger(__name__)

EXTRACTION_STAGE = "extraction"


def _sanitize_error(exc: Exception) -> tuple[str, str]:
    """Return a public error code and message without leaking internals."""
    message = str(exc).strip() or exc.__class__.__name__
    return exc.__class__.__name__.upper(), message[:1000]


def _persist_artifact(storage: LocalStorage, document_id: UUID, payload: bytes) -> str:
    """Persist a serialized extraction artifact and return its storage URI."""
    key = f"artifacts/{document_id}/extraction.json"
    return storage.put_stream(key, BytesIO(payload)).uri


async def _run_extraction(document_id: str) -> dict[str, object]:
    """Load, extract, and persist one document's canonical artifact."""
    doc_id = UUID(document_id)
    async with async_session_factory() as session:
        document = (
            await session.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none()
        if document is None:
            logger.warning("Extraction skipped for missing document %s", document_id)
            return {"document_id": document_id, "skipped": True}

        latest_attempt = (
            await session.execute(
                select(StageRun.attempt)
                .where(
                    StageRun.document_id == doc_id,
                    StageRun.stage_name == EXTRACTION_STAGE,
                )
                .order_by(StageRun.attempt.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        attempt = (latest_attempt or 0) + 1

        stage_run = StageRun(
            document_id=doc_id,
            stage_name=EXTRACTION_STAGE,
            status=StageStatus.RUNNING,
            progress_pct=0,
            attempt=attempt,
        )
        session.add(stage_run)
        document.status = DocumentStatus.PROCESSING
        await session.commit()
        await session.refresh(stage_run)

        storage = LocalStorage(settings.STORAGE_ROOT)

        try:
            source_path = storage.resolve(document.storage_uri)
            artifact = extract_document(Path(source_path), doc_id, document.media_type)
            artifact_uri = _persist_artifact(
                storage, doc_id, artifact.model_dump_json().encode("utf-8")
            )
            stage_run.artifact_uri = artifact_uri
            stage_run.progress_pct = 100
            if artifact.warnings:
                stage_run.status = StageStatus.SUCCEEDED_WITH_WARNINGS
                document.status = DocumentStatus.COMPLETED_WITH_WARNINGS
            else:
                stage_run.status = StageStatus.SUCCEEDED
                document.status = DocumentStatus.COMPLETED
            document.page_count = len(artifact.pages) or None
        except Exception as exc:  # noqa: BLE001 — stage failures are recorded, not raised
            code, message = _sanitize_error(exc)
            stage_run.status = StageStatus.FAILED
            stage_run.error_code = code
            stage_run.error_message = message
            document.status = DocumentStatus.FAILED
            logger.exception("Extraction failed for document %s", document_id)
        finally:
            stage_run.finished_at = datetime.now(UTC)
            await session.commit()

    return {"document_id": document_id, "stage": EXTRACTION_STAGE}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="docqc.extract",
    max_retries=2,
    default_retry_delay=5,
    autoretry_for=(Exception,),
)
def extract_document_task(self: Any, document_id: str) -> dict[str, object]:
    """Run extraction and persist a failed run before any retry is scheduled."""
    try:
        return asyncio.run(_run_extraction(document_id))
    except Exception as exc:  # noqa: BLE001 — retry idempotently, artifact state is per-attempt
        request = self.request
        retries = request.retries if request is not None else 0
        max_retries = self.max_retries
        if retries >= max_retries:
            return {"document_id": document_id, "failed": str(exc)}
        raise self.retry(exc=exc) from exc
