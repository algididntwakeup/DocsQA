"""Celery task for the extraction stage of the Document QC pipeline."""

import asyncio
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.config import settings
from db.session import async_session_factory
from domain.enums import DocumentStatus, StageStatus
from models.document import Document, StageRun
from schemas.extraction import ExtractionArtifact
from services.extract import extract_document
from services.revision_sync import analyze_revision
from services.standard_traceability import analyze_standard_traceability
from services.storage import LocalStorage

logger = get_task_logger(__name__)

EXTRACTION_STAGE = "extraction"
REVISION_STAGE = "revision_sync"
STANDARD_STAGE = "standard_traceability"


def _sanitize_error(exc: Exception) -> tuple[str, str]:
    """Return a public error code and message without leaking internals."""
    message = str(exc).strip() or exc.__class__.__name__
    return exc.__class__.__name__.upper(), message[:1000]


def _persist_artifact(
    storage: LocalStorage, document_id: UUID, name: str, payload: bytes
) -> str:
    """Persist a serialized extraction artifact and return its storage URI."""
    key = f"artifacts/{document_id}/{name}.json"
    return storage.put_stream(key, BytesIO(payload)).uri


async def _latest_attempt(
    session: AsyncSession, document_id: UUID, stage_name: str
) -> int:
    value = (
        await session.execute(
            select(StageRun.attempt)
            .where(
                StageRun.document_id == document_id,
                StageRun.stage_name == stage_name,
            )
            .order_by(StageRun.attempt.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return (value or 0) + 1


async def _run_revision_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist revision evidence while isolating analyzer failures."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=REVISION_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, REVISION_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    revision_failed = False
    try:
        analysis = analyze_revision(document.original_filename, artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            REVISION_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        revision_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Revision sync failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return revision_failed


async def _run_standard_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
    prior_degraded: bool,
) -> None:
    """Persist standard-traceability evidence and finalize visible status."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=STANDARD_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, STANDARD_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    standard_failed = False
    try:
        analysis = analyze_standard_traceability(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            STANDARD_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        standard_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Standard traceability failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        document.status = (
            DocumentStatus.COMPLETED_WITH_WARNINGS
            if prior_degraded or standard_failed
            else DocumentStatus.COMPLETED
        )
        document.progress_pct = 100
        await session.commit()


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

        stage_run = StageRun(
            document_id=doc_id,
            stage_name=EXTRACTION_STAGE,
            status=StageStatus.RUNNING,
            progress_pct=0,
            attempt=await _latest_attempt(session, doc_id, EXTRACTION_STAGE),
            started_at=datetime.now(UTC),
        )
        session.add(stage_run)
        document.status = DocumentStatus.PROCESSING
        await session.commit()
        await session.refresh(stage_run)

        storage = LocalStorage(settings.STORAGE_ROOT)

        artifact: ExtractionArtifact | None = None
        extraction_degraded = False
        try:
            source_path = storage.resolve(document.storage_uri)
            artifact = extract_document(Path(source_path), doc_id, document.media_type)
            artifact_uri = _persist_artifact(
                storage,
                doc_id,
                EXTRACTION_STAGE,
                artifact.model_dump_json().encode("utf-8"),
            )
            stage_run.artifact_uri = artifact_uri
            stage_run.progress_pct = 100
            if artifact.warnings:
                extraction_degraded = True
                stage_run.status = StageStatus.SUCCEEDED_WITH_WARNINGS
            else:
                stage_run.status = StageStatus.SUCCEEDED
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

        if artifact is not None:
            revision_failed = await _run_revision_stage(
                session, storage, document, artifact
            )
            await _run_standard_stage(
                session,
                storage,
                document,
                artifact,
                prior_degraded=extraction_degraded or revision_failed,
            )

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
