import asyncio
import contextlib
import json
import logging
import shutil
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.concurrency import run_in_threadpool

from core.dependencies import (
    get_accessible_document,
    get_current_user,
    get_storage,
    get_upload_service,
    require_lead,
)
from db.session import async_session_factory, get_session
from domain.enums import (
    DocumentStatus,
    DocumentWorkflowStatus,
    IssueCategory,
    PipelineStage,
    ReportLanguage,
    Severity,
    StageStatus,
    UserRole,
)
from models.document import Document, StageRun
from models.issue import Issue
from models.project import Project
from models.user import User
from schemas.common import PageInfo, ProblemDetail
from schemas.documents import (
    DocumentAssignment,
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
    DocumentWorkflowUpdate,
    ReviewReportPreview,
    StageRunRead,
    TraceabilitySummaryResponse,
)
from schemas.issues import IssueListResponse, IssueRead
from schemas.report import HeaderTemplateConfig, ReportExportRequest
from services.export import (
    LibreOfficeConversionError,
    assessment_from_document_findings,
    convert_docx_to_pdf,
    export_annotated_pdf,
    generate_ale_review_docx,
)
from services.permission_service import (
    can_review_document,
    has_workspace_oversight,
)
from services.pipeline import enqueue_extraction
from services.progress_events import open_document_progress_subscription
from services.storage.local import LocalStorage
from services.uploads import UploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

WIP_ERROR = (
    "Kamu masih memiliki dokumen aktif yang sedang direview. "
    "Selesaikan review (Mark Reviewed) terlebih dahulu."
)

_PROGRESS_PHASES: dict[str, tuple[str, int, int]] = {
    "extraction": ("Text extraction", 10, 25),
    PipelineStage.EXTRACTING.value: ("Text extraction", 10, 25),
    "revision_sync": ("Document checks", 25, 30),
    PipelineStage.BUDINSKI_AUDIT.value: ("Budinski checks", 30, 55),
    "table_math": ("Table/reference checks", 60, 80),
    "ref_drift": ("Table/reference checks", 60, 80),
    "standard_traceability": ("Table/reference checks", 60, 80),
    PipelineStage.LAYOUT_INSPECTION.value: ("Table/reference checks", 60, 80),
    PipelineStage.STANDARDS_CHECK.value: ("Table/reference checks", 60, 80),
    "spellcheck": ("Document checks", 80, 84),
    "grammar": ("Document checks", 80, 84),
    "duplicate_content": ("Document checks", 80, 84),
    "ambiguity": ("Document checks", 80, 84),
    "aggregation": ("Report synthesis", 85, 99),
    PipelineStage.AGGREGATING.value: ("Report synthesis", 85, 99),
}


def _stage_progress(stage_name: str, progress_pct: int) -> tuple[str, int]:
    """Map a pipeline stage's local progress onto the workspace progress scale."""
    name = (
        PipelineStage.EXTRACTING.value
        if stage_name == "extraction"
        else stage_name
    )
    label, start, end = _PROGRESS_PHASES.get(name, ("Document analysis", 10, 99))
    progress = start + round((end - start) * progress_pct / 100)
    return label, min(end, max(start, progress))


async def check_engineer_wip_available(
    session: AsyncSession, engineer_id: UUID, project_id: UUID | None
) -> tuple[bool, Document | None]:
    """Return whether an engineer has a free single-document WIP slot in a project."""
    active_document = (
        await session.execute(
            select(Document)
            .where(
                Document.assigned_to_id == engineer_id,
                Document.workflow_status == DocumentWorkflowStatus.ANALYZING,
                Document.project_id == project_id,
            )
            .order_by(Document.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return active_document is None, active_document


def _document_read(document: Document) -> DocumentRead:
    """Serialize a document with assignment and owner display metadata."""
    return DocumentRead.model_validate(document).model_copy(
        update={
            "owner_name": document.owner.full_name if document.owner else None,
            "uploaded_by_name": document.owner.full_name if document.owner else "Unknown",
            "assigned_to_name": document.assigned_to.full_name if document.assigned_to else None,
            "assigned_to_email": document.assigned_to.email if document.assigned_to else None,
            "project_name": document.project.name if document.project else "Unassigned project",
            "project_plant": document.project.plant_area if document.project else None,
            "project_finished": bool(document.project and document.project.finished_at),
        }
    )


def _ensure_document_project_open(document: Document) -> None:
    if document.project and document.project.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is finished; document workflow changes are disabled.",
        )


async def _ensure_assignment_project_open(session: AsyncSession, document: Document) -> None:
    if document.project_id is None:
        return
    project = await session.get(Project, document.project_id)
    if project is not None and project.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is finished; document assignment changes are disabled.",
        )


async def _load_document_for_assignment(session: AsyncSession, document_id: UUID) -> Document:
    document = (
        await session.execute(select(Document).where(Document.id == document_id).with_for_update())
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.post("/{document_id}/claim", response_model=DocumentRead)
async def claim_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    """Claim an unassigned document when the engineer has no active WIP."""
    try:
        if current_user.role != UserRole.ENGINEER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Engineer access required."
            )
        await session.execute(select(User).where(User.id == current_user.id).with_for_update())
        document = await _load_document_for_assignment(session, document_id)
        await _ensure_assignment_project_open(session, document)
        if document.assigned_to_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Document is already assigned."
            )
        available, _ = await check_engineer_wip_available(
            session,
            current_user.id,
            document.project_id,
        )
        if not available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=WIP_ERROR)
        document.assigned_to_id = current_user.id
        document.assigned_to = current_user
        await session.commit()
        await session.refresh(
            document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
        )
        return _document_read(document)
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/{document_id}/assign", response_model=DocumentRead)
async def assign_document(
    document_id: UUID,
    payload: DocumentAssignment,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
) -> DocumentRead:
    """Assign a document to an engineer, optionally overriding the WIP limit."""
    try:
        document = await _load_document_for_assignment(session, document_id)
        await _ensure_assignment_project_open(session, document)
        if payload.engineer_id is None:
            document.assigned_to_id = None
            document.assigned_to = None
            await session.commit()
            await session.refresh(
                document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
            )
            return _document_read(document)
        engineer = (
            await session.execute(
                select(User)
                .where(
                    User.id == payload.engineer_id,
                    User.is_active.is_(True),
                    User.role == UserRole.ENGINEER,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if engineer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Engineer not found or inactive."
            )
        if not payload.override_wip:
            available, active_document = await check_engineer_wip_available(
                session,
                engineer.id,
                document.project_id,
            )
            if not available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Engineer already has an active document.",
                        "active_document": {
                            "id": str(active_document.id) if active_document else None,
                            "filename": (
                                active_document.original_filename if active_document else None
                            ),
                            "workflow_status": (
                                active_document.workflow_status.value if active_document else None
                            ),
                        },
                    },
                )
        document.assigned_to_id = engineer.id
        document.assigned_to = engineer
        await session.commit()
        await session.refresh(
            document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
        )
        return _document_read(document)
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.post("/{document_id}/mark-reviewed", response_model=DocumentRead)
async def mark_document_reviewed(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentRead:
    """Submit the document's engineer review.

    Allowed for the document uploader, the project owner, the assigned
    engineer, and local superusers. The legacy rule required the assigned PIC
    only, which blocked uploaders and project owners from finishing their own
    document's review.
    """
    _ensure_document_project_open(document)
    if not can_review_document(current_user, document):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Akses ditolak. Hanya pengunggah dokumen, pemilik proyek, atau "
                "superuser yang dapat menyelesaikan review."
            ),
        )
    document.workflow_status = DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    document.reviewed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(
        document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
    )
    return _document_read(document)


@router.post("/{document_id}/verify", response_model=DocumentRead)
async def verify_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
    document: Annotated[Document, Depends(get_accessible_document)],
    payload: DocumentWorkflowUpdate | None = None,
) -> DocumentRead:
    """Verify a document as a lead engineer."""
    _ensure_document_project_open(document)
    document.verified_by_id = current_user.id
    document.verified_at = datetime.now(UTC)
    document.workflow_status = DocumentWorkflowStatus.VERIFIED_BY_LEAD
    if payload is not None and payload.verification_notes is not None:
        document.verification_notes = payload.verification_notes
    await session.commit()
    await session.refresh(
        document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
    )
    return _document_read(document)


@router.post("/{document_id}/request-revision", response_model=DocumentRead)
async def request_document_revision(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
    document: Annotated[Document, Depends(get_accessible_document)],
    payload: DocumentWorkflowUpdate | None = None,
) -> DocumentRead:
    """Return a document to an engineer for revision."""
    _ensure_document_project_open(document)
    requested_status = (
        payload.workflow_status
        if payload is not None and payload.workflow_status is not None
        else DocumentWorkflowStatus.ANALYZING
    )
    if requested_status not in {
        DocumentWorkflowStatus.ANALYZING,
        DocumentWorkflowStatus.REVIEWED_BY_ENGINEER,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Revision status must be ANALYZING or REVIEWED_BY_ENGINEER.",
        )
    document.workflow_status = requested_status
    document.verification_notes = payload.verification_notes if payload is not None else None
    document.verified_by_id = None
    document.verified_at = None
    if requested_status == DocumentWorkflowStatus.ANALYZING:
        document.reviewed_at = None
    await session.commit()
    await session.refresh(
        document, attribute_names=["updated_at", "owner", "assigned_to", "project"]
    )
    return _document_read(document)


@router.get("", response_model=DocumentListResponse, responses=NOT_READY)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    project_id: Annotated[
        UUID | None,
        Query(description="Lead-only project filter for the master inspection register."),
    ] = None,
    assigned_to_id: Annotated[
        UUID | None,
        Query(description="Lead-only engineer assignment filter."),
    ] = None,
    workflow_status: Annotated[
        str | None,
        Query(
            description="Lead-only workflow filter.",
            enum=[status.value for status in DocumentWorkflowStatus],
        ),
    ] = None,
) -> DocumentListResponse:
    """List documents visible to the current user."""

    query = select(Document).options(
        joinedload(Document.owner),
        joinedload(Document.assigned_to),
        joinedload(Document.project),
    )
    # Non-privileged roles (engineers, HR/GA, finance) only see their own
    # documents; lead engineers and locally flagged superusers keep the
    # cross-engineer view.
    if not has_workspace_oversight(current_user):
        query = query.outerjoin(Document.project).where(
            (Document.assigned_to_id == current_user.id)
            | (Document.owner_id == current_user.id)
            | (Project.owner_id == current_user.id)
        )
    else:
        if project_id is not None:
            query = query.where(Document.project_id == project_id)
        if assigned_to_id is not None:
            query = query.where(Document.assigned_to_id == assigned_to_id)
        if workflow_status is not None:
            try:
                query = query.where(
                    Document.workflow_status == DocumentWorkflowStatus(workflow_status)
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Invalid workflow status.") from exc
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        (
            await session.execute(
                query.order_by(Document.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return DocumentListResponse(
        documents=[_document_read(d) for d in rows],
        pagination=PageInfo(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    responses={**NOT_READY, 200: {"model": DocumentUploadResponse}},
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Native-text PDF or DOCX")],
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentUploadResponse:
    """Persist a validated document and enqueue canonical extraction."""

    result = await upload_service.create_or_reuse(file, session)
    if not result.deduplicated:
        result.document.owner_id = current_user.id
        await session.commit()
        await session.refresh(result.document)
    if result.deduplicated:
        response.status_code = status.HTTP_200_OK
    else:
        await enqueue_extraction(result.document, session)
    return DocumentUploadResponse(
        id=result.document.id,
        filename=result.document.original_filename,
        status=result.document.status,
        created_at=result.document.created_at,
        deduplicated=result.deduplicated,
    )


@router.get("/{document_id}", response_model=DocumentRead, responses=NOT_READY)
async def get_document(
    document_id: UUID,
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentRead:
    """Return safe metadata for one document."""

    return _document_read(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def delete_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    document: Annotated[Document, Depends(get_accessible_document)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> Response:
    _ensure_document_project_open(document)
    if document.workflow_status == DocumentWorkflowStatus.VERIFIED_BY_LEAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Dokumen yang sudah diverifikasi resmi tidak dapat dihapus demi integritas audit."
            ),
        )
    if document.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dokumen yang sudah diserahkan ke Lead tidak dapat dihapus.",
        )
    if document.assigned_to_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Dokumen sedang ditugaskan ke engineer. Lepaskan tugas (unassign) terlebih "
                "dahulu sebelum menghapus."
            ),
        )
    if document.owner_id != current_user.id and current_user.role not in {
        UserRole.LEAD_ENGINEER,
        UserRole.SUPERUSER,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya uploader atau Lead Engineer yang dapat menghapus dokumen.",
        )

    # 1. Clean up physical files from storage
    for uri in (document.storage_uri, document.canonical_pdf_uri):
        if uri:
            with contextlib.suppress(FileNotFoundError):
                if uri.startswith(storage.scheme):
                    storage.delete(uri)
                else:
                    suffix = uri.split("://", 1)[-1] if "://" in uri else uri
                    target = storage.root / suffix
                    if target.exists() and target.is_file():
                        target.unlink()

    # 2. Clean up artifact directory
    artifacts_dir = storage.root / "artifacts" / str(document.id)
    if artifacts_dir.exists() and artifacts_dir.is_dir():
        with contextlib.suppress(OSError):
            shutil.rmtree(artifacts_dir, ignore_errors=True)

    # 3. Clean up database record (foreign keys cascade to stage_runs, issues, audit_events)
    await session.execute(delete(Document).where(Document.id == document_id))
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses=NOT_READY,
)
async def get_document_status(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentStatusResponse:
    """Return the current processing phase, percentage, and useful error context."""

    stage_runs = (
        (
            await session.execute(
                select(StageRun)
                .where(StageRun.document_id == document_id)
                .order_by(StageRun.created_at.asc(), StageRun.id.asc())
            )
        )
        .scalars()
        .all()
    )
    latest_by_stage: dict[str, StageRun] = {}
    for stage_run in stage_runs:
        stage_name = (
            PipelineStage.EXTRACTING.value
            if stage_run.stage_name == "extraction"
            else stage_run.stage_name
        )
        latest_by_stage[stage_name] = stage_run
    ordered_stage_runs = [
        latest_by_stage[stage.value] for stage in PipelineStage if stage.value in latest_by_stage
    ]
    ordered_stage_runs.extend(
        stage_run
        for stage_name, stage_run in latest_by_stage.items()
        if stage_name not in {stage.value for stage in PipelineStage}
    )
    latest_runs_by_time = sorted(
        latest_by_stage.values(), key=lambda stage_run: stage_run.created_at
    )
    current_stage_run = next(
        (
            stage_run
            for stage_run in reversed(latest_runs_by_time)
            if stage_run.status == StageStatus.RUNNING
        ),
        latest_runs_by_time[-1] if latest_runs_by_time else None,
    )
    failed_stage_run = next(
        (
            stage_run
            for stage_run in reversed(latest_runs_by_time)
            if stage_run.status == StageStatus.FAILED
        ),
        None,
    )
    if document.status == DocumentStatus.FAILED:
        current_stage = (
            _stage_progress(failed_stage_run.stage_name, failed_stage_run.progress_pct)[0]
            if failed_stage_run
            else "Analysis failed"
        )
        error_message = (
            failed_stage_run.error_message
            if failed_stage_run and failed_stage_run.error_message
            else "Document analysis failed. Retry the analysis or contact support."
        )
        calculated_progress = document.progress_pct
    elif document.status in {DocumentStatus.COMPLETED, DocumentStatus.COMPLETED_WITH_WARNINGS}:
        current_stage = "Analysis complete"
        error_message = None
        calculated_progress = 100
    elif current_stage_run is None:
        current_stage = "Queued for processing"
        error_message = None
        calculated_progress = document.progress_pct
    else:
        current_stage, calculated_progress = _stage_progress(
            current_stage_run.stage_name, current_stage_run.progress_pct
        )
        error_message = current_stage_run.error_message

    stage_reads = [StageRunRead.model_validate(r) for r in ordered_stage_runs]
    for stage_read in stage_reads:
        if stage_read.name == "extraction":
            stage_read.name = PipelineStage.EXTRACTING.value
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        progress_pct=max(document.progress_pct, calculated_progress),
        current_stage=current_stage,
        error_message=error_message,
        stages=stage_reads,
        updated_at=document.updated_at,
    )


@router.post("/{document_id}/retry", response_model=DocumentRead)
async def retry_document_analysis(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentRead:
    """Re-enqueue a failed document for its owner, assignee, or a lead reviewer."""
    is_lead = current_user.role in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}
    can_retry = current_user.id in {document.owner_id, document.assigned_to_id}
    if not is_lead and not can_retry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the document owner, assignee, or a lead engineer can retry analysis.",
        )
    if document.status != DocumentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed documents can be retried.",
        )

    document.status = DocumentStatus.QUEUED
    document.progress_pct = 0
    await session.commit()
    await enqueue_extraction(document, session)
    await session.refresh(document, attribute_names=["owner", "assigned_to", "project"])
    return _document_read(document)


@router.get(
    "/{document_id}/issues",
    response_model=IssueListResponse,
    responses=NOT_READY,
)
async def list_document_issues(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
    category: IssueCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssueListResponse:
    """List issues with optional canonical category filtering."""

    # Severity counts across all issues for this document
    counts_result = (
        await session.execute(
            select(Issue.severity, func.count(Issue.id))
            .where(Issue.document_id == document_id)
            .group_by(Issue.severity)
        )
    ).all()
    counts_by_severity: dict[Severity, int] = {s: 0 for s in Severity}
    for sev, count in counts_result:
        with contextlib.suppress(ValueError):
            counts_by_severity[Severity(sev)] = count

    # Filtered query for pagination
    query = select(Issue).where(Issue.document_id == document_id)
    if category is not None:
        query = query.where(Issue.category == category)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    offset = (page - 1) * page_size
    issues = (
        (
            await session.execute(
                query.order_by(Issue.created_at.asc(), Issue.id.asc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return IssueListResponse(
        issues=[IssueRead.model_validate(i) for i in issues],
        pagination=PageInfo(page=page, page_size=page_size, total=total),
        counts_by_severity=counts_by_severity,
    )


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document or file not found",
        },
        status.HTTP_409_CONFLICT: {
            "model": ProblemDetail,
            "description": "Document preview is pending",
        },
    },
)
@router.get(
    "/{document_id}/pdf",
    response_class=FileResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document or canonical PDF not found",
        },
        status.HTTP_409_CONFLICT: {
            "model": ProblemDetail,
            "description": "Document preview is pending",
        },
    },
)
async def get_document_file(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> FileResponse:
    """Stream the canonical PDF rendition or file preview of an uploaded document."""

    is_docx = (
        document.media_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or document.original_filename.lower().endswith(".docx")
        or document.storage_uri.lower().endswith(".docx")
    )

    # 1. If original document is .docx, resolve or convert to PDF preview
    if is_docx:
        pdf_path: Path | None = None
        if document.canonical_pdf_uri:
            try:
                candidate = storage.get_full_path(document.canonical_pdf_uri)
                if candidate.exists():
                    pdf_path = candidate
            except Exception:
                pdf_path = None

        if pdf_path is None:
            try:
                source_full_path = storage.get_full_path(document.storage_path)
                candidate = source_full_path.parent / "preview.pdf"
                if candidate.exists():
                    pdf_path = candidate
            except Exception:
                pass

        if pdf_path is None:
            if document.status in (DocumentStatus.QUEUED, DocumentStatus.PROCESSING):
                logger.info(
                    "DOCX preview conversion pending for document %s (status=%s)",
                    document.id,
                    document.status,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Document preview is still being generated. Please wait.",
                )

            # Document is completed, attempt on-the-fly conversion using LibreOffice
            try:
                source_path = storage.get_full_path(document.storage_path)
                if source_path.exists():
                    logger.info(
                        "Attempting on-the-fly DOCX to PDF conversion for document %s", document.id
                    )
                    pdf_path = await run_in_threadpool(
                        convert_docx_to_pdf, source_path, source_path.parent
                    )
                    document.canonical_pdf_uri = f"local://documents/{document.id}/preview.pdf"
                    await session.commit()
            except Exception as exc:
                logger.warning(
                    "On-the-fly DOCX conversion failed for document %s: %s",
                    document.id,
                    exc,
                )

        if pdf_path is not None and pdf_path.exists():
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=f"{document.safe_filename}.pdf",
                content_disposition_type="inline",
            )

        checked_path = str(storage.get_full_path(document.storage_path).parent / "preview.pdf")
        logger.error(
            "PDF preview file not found on disk: checked path %s for document %s (storage_uri=%s)",
            checked_path,
            document.id,
            document.storage_uri,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF preview file not found on storage: {checked_path}",
        )

    # 2. For native PDF documents
    uri = document.canonical_pdf_uri or document.storage_uri
    if not uri:
        logger.error("Document %s has no storage_uri or canonical_pdf_uri", document.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical PDF rendition not available.",
        )

    try:
        path = storage.get_full_path(document.storage_path)
    except Exception as exc:
        logger.error(
            "Failed to resolve path for document %s (storage_path=%s): %s",
            document.id,
            document.storage_path,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File path could not be resolved: {exc}",
        ) from exc

    if not path.exists():
        logger.error(
            "File not found on disk: checked path %s for document %s (storage_uri=%s)",
            path,
            document.id,
            document.storage_uri,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file not found on storage: {path}",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=f"{document.safe_filename}.pdf",
        content_disposition_type="inline",
    )


@router.get(
    "/{document_id}/traceability-summary",
    response_model=TraceabilitySummaryResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def get_traceability_summary(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> TraceabilitySummaryResponse:
    """Return traceability counts for audit triage."""

    issues = (
        (
            await session.execute(
                select(Issue).where(
                    Issue.document_id == document_id,
                    Issue.category == IssueCategory.TRACEABILITY,
                )
            )
        )
        .scalars()
        .all()
    )

    counts_by_type: dict[str, int] = {}
    counts_by_severity: dict[str, int] = {}
    critical_count = 0
    unresolved_count = 0

    for issue in issues:
        counts_by_type[issue.type] = counts_by_type.get(issue.type, 0) + 1
        sev_key = getattr(issue.severity, "value", str(issue.severity))
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1
        if issue.severity in {Severity.CRITICAL, "CRITICAL"}:
            critical_count += 1
        if issue.included_in_report:
            unresolved_count += 1

    return TraceabilitySummaryResponse(
        document_id=document.id,
        counts_by_type=counts_by_type,
        counts_by_severity=counts_by_severity,
        critical_count=critical_count,
        unresolved_count=unresolved_count,
    )


@router.get(
    "/{document_id}/report",
    response_model=ReviewReportPreview,
)
async def get_report_preview(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
    language: Annotated[ReportLanguage, Query()] = ReportLanguage.ENGLISH,
) -> ReviewReportPreview:
    """Return the current draft-report composition without generating a file."""
    issues = (
        (
            await session.execute(
                select(Issue).where(
                    Issue.document_id == document_id,
                    Issue.included_in_report.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    counts: dict[str, int] = {}
    blockers = 0
    for issue in issues:
        sev_key = getattr(issue.severity, "value", str(issue.severity))
        counts[sev_key] = counts.get(sev_key, 0) + 1
        if issue.severity in {
            Severity.BLOCKER,
            Severity.CRITICAL,
            Severity.HIGH,
            "BLOCKER",
            "CRITICAL",
            "HIGH",
        }:
            blockers += 1
    summary = (
        (
            "Blockers require correction before reissue."
            if language == ReportLanguage.ENGLISH
            else "Penghalang harus diperbaiki sebelum penerbitan ulang."
        )
        if blockers
        else (
            "No blocker findings are included in the draft report."
            if language == ReportLanguage.ENGLISH
            else "Tidak ada temuan penghalang dalam laporan draf."
        )
    )
    return ReviewReportPreview(
        document_id=document_id,
        included_findings=len(issues),
        blockers=blockers,
        counts_by_severity=counts,
        summary_judgement=summary,
    )


@router.get(
    "/{document_id}/export",
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
@router.post(
    "/{document_id}/export",
    response_class=Response,
    include_in_schema=False,
)
async def export_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    document: Annotated[Document, Depends(get_accessible_document)],
    format: Annotated[str, Query(pattern=r"^(pdf|docx|annotated_pdf)$")] = "docx",
    include_minors: Annotated[
        bool, Query(description="Include minor and informational findings.")
    ] = False,
    include_language_mechanics: Annotated[
        bool, Query(description="Include language and mechanics findings in the report.")
    ] = False,
    language: Annotated[ReportLanguage | None, Query()] = None,
    lang: Annotated[str | None, Query(pattern=r"^(en|id)$")] = None,
    export_options: Annotated[ReportExportRequest | None, Body()] = None,
) -> Response:
    """Export the formal review report (PDF via LibreOffice or DOCX) or annotated original PDF."""

    issues = (
        (
            await session.execute(
                select(Issue)
                .where(Issue.document_id == document_id)
                .order_by(Issue.created_at.asc(), Issue.id.asc())
            )
        )
        .scalars()
        .all()
    )

    safe_name = document.safe_filename
    report_lang = ReportLanguage.ENGLISH
    if lang == "id" or language == ReportLanguage.INDONESIAN:
        report_lang = ReportLanguage.INDONESIAN
    elif lang == "en" or language == ReportLanguage.ENGLISH:
        report_lang = ReportLanguage.ENGLISH

    if format == "annotated_pdf":
        selected_issues = [
            issue
            for issue in issues
            if issue.included_in_report
            and (
                include_minors
                or getattr(issue.severity, "value", str(issue.severity)).upper()
                not in {"MINOR", "INFO", "LOW"}
            )
        ]
        pdf_bytes = export_annotated_pdf(document, selected_issues, storage)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_annotated.pdf"'},
        )

    refresh = getattr(session, "refresh", None)
    if refresh is not None:
        try:
            await refresh(document, ["owner", "verified_by"])
        except TypeError:
            # Lightweight test sessions and compatibility adapters may only
            # implement SQLAlchemy's single-argument refresh form.
            await refresh(document)
    scorecard: dict[str, Any] | None = None
    scorecard_path = storage._path_for_key(f"artifacts/{document.id}/budinski_scorecard.json")
    if scorecard_path.exists():
        try:
            scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            scorecard = None
    report_include_language_mechanics = (
        export_options.include_language_mechanics
        if export_options and export_options.include_language_mechanics is not None
        else include_language_mechanics
    )
    project = await session.get(Project, document.project_id) if document.project_id else None
    assessment = assessment_from_document_findings(
        document,
        list(issues),
        scorecard_data=scorecard,
        include_minors=include_minors,
        language=report_lang,
        include_language_mechanics=report_include_language_mechanics,
        project=project,
    )
    project_config = None
    if project is not None and project.header_config:
        try:
            project_config = HeaderTemplateConfig.model_validate(project.header_config)
        except Exception:
            project_config = None
    effective_header_config = (
        export_options.header_config if export_options else project_config or HeaderTemplateConfig()
    )
    docx_bytes = generate_ale_review_docx(
        assessment,
        document,
        language=report_lang,
        header_config=effective_header_config,
        include_language_mechanics=report_include_language_mechanics,
    )

    if format == "docx":
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_review.docx"'},
        )

    if format == "pdf":
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix="prism-review-",
                    suffix=".docx",
                    dir=tmp_path,
                    delete=False,
                ) as tmp_docx_file:
                    tmp_docx_file.write(docx_bytes)
                    tmp_docx = Path(tmp_docx_file.name)
                pdf_path = await run_in_threadpool(convert_docx_to_pdf, tmp_docx, tmp_path)
                pdf_bytes = pdf_path.read_bytes()
            except LibreOfficeConversionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate PDF review report via LibreOffice: {exc}",
                ) from exc
            except FileNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"LibreOffice is not available on this host: {exc}",
                ) from exc
            except OSError as exc:
                logger.exception("Could not write or read the temporary PDF export")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Temporary PDF export failed: {exc}",
                ) from exc

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_review.pdf"'},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.get(
    "/{document_id}/events",
    response_class=StreamingResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def stream_document_events(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> StreamingResponse:
    """Stream real-time processing progress and stage transitions via Server-Sent Events (SSE)."""

    TERMINAL_STATUSES = {
        DocumentStatus.COMPLETED,
        DocumentStatus.COMPLETED_WITH_WARNINGS,
        DocumentStatus.FAILED,
    }
    REDIS_WAIT_SECONDS = 2.0
    FALLBACK_POLL_SECONDS = 10.0
    MAX_POLL_DURATION = 600  # 10 minutes max SSE lifetime

    async def event_generator() -> AsyncIterator[str]:
        started_at = asyncio.get_running_loop().time()
        last_db_poll = started_at - FALLBACK_POLL_SECONDS
        refresh = True
        redis_client: Any = None
        pubsub: Any = None
        try:
            try:
                redis_client, pubsub = await open_document_progress_subscription(document_id)
            except Exception:  # noqa: BLE001 — PostgreSQL polling is the fallback
                logger.debug("Redis progress subscription unavailable for %s", document_id)

            while asyncio.get_running_loop().time() - started_at < MAX_POLL_DURATION:
                now = asyncio.get_running_loop().time()
                if pubsub is not None and not refresh:
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=REDIS_WAIT_SECONDS,
                        )
                        now = asyncio.get_running_loop().time()
                        refresh = bool(message) or now - last_db_poll >= FALLBACK_POLL_SECONDS
                    except Exception:  # noqa: BLE001 — fall back to bounded DB polling
                        logger.debug("Redis progress subscription lost for %s", document_id)
                        with contextlib.suppress(Exception):
                            await pubsub.aclose()
                        with contextlib.suppress(Exception):
                            if redis_client is not None:
                                await redis_client.aclose()
                        pubsub = None
                        redis_client = None
                        refresh = True
                elif pubsub is None and not refresh:
                    await asyncio.sleep(FALLBACK_POLL_SECONDS)
                    refresh = True

                if not refresh:
                    continue

                async with async_session_factory() as poll_session:
                    doc = (
                        await poll_session.execute(
                            select(Document).where(Document.id == document_id)
                        )
                    ).scalar_one_or_none()
                    if doc is None:
                        yield "event: close\ndata: {}\n\n"
                        return

                    stages_res = (
                        (
                            await poll_session.execute(
                                select(StageRun)
                                .where(StageRun.document_id == document_id)
                                .order_by(StageRun.created_at.asc())
                            )
                        )
                        .scalars()
                        .all()
                    )

                last_db_poll = asyncio.get_running_loop().time()
                refresh = False
                latest_stages: dict[str, StageRun] = {}
                for stage_run in stages_res:
                    stage_name = (
                        PipelineStage.EXTRACTING.value
                        if stage_run.stage_name == "extraction"
                        else stage_run.stage_name
                    )
                    latest_stages[stage_name] = stage_run
                ordered_stages = [
                    latest_stages[stage.value]
                    for stage in PipelineStage
                    if stage.value in latest_stages
                ]
                ordered_stages.extend(
                    stage_run
                    for stage_name, stage_run in latest_stages.items()
                    if stage_name not in {stage.value for stage in PipelineStage}
                )
                completed_stages = sum(
                    1
                    for stage_run in ordered_stages
                    if stage_run.status
                    in (StageStatus.SUCCEEDED, StageStatus.SUCCEEDED_WITH_WARNINGS)
                )
                pct = (
                    100
                    if doc.status in TERMINAL_STATUSES
                    else min(95, int((completed_stages / 6) * 100))
                )
                payload = {
                    "document_id": str(doc.id),
                    "status": doc.status.value,
                    "progress_pct": pct,
                    "stages": [
                        {
                            "name": PipelineStage.EXTRACTING.value
                            if stage_run.stage_name == "extraction"
                            else stage_run.stage_name,
                            "status": stage_run.status.value,
                            "progress_pct": stage_run.progress_pct,
                        }
                        for stage_run in ordered_stages
                    ],
                }
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                if doc.status in TERMINAL_STATUSES:
                    yield "event: close\ndata: {}\n\n"
                    return

            yield "event: close\ndata: {}\n\n"
        finally:
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:
                    logger.debug("Redis progress pubsub close failed", exc_info=True)
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    logger.debug("Redis progress client close failed", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
