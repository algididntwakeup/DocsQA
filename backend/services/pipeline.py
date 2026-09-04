"""Pipeline orchestration glue between the HTTP layer and Celery tasks."""

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus, StageStatus
from models.document import Document, StageRun
from tasks.extraction import extract_document_task

EXTRACTION_STAGE = "extraction"


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
