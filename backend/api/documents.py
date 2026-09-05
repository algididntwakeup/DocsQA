"""Contract-first document lifecycle endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_storage, get_upload_service
from core.errors import feature_not_ready
from db.session import get_session
from domain.enums import IssueCategory, Severity
from models.audit import AuditEvent
from models.document import Document, StageRun
from models.issue import Issue
from schemas.audit import (
    AuditEventListResponse,
    AuditEventRead,
    DocumentDispositionRequest,
)
from schemas.common import PageInfo, ProblemDetail
from schemas.documents import (
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
    StageRunRead,
    TraceabilitySummaryResponse,
)
from schemas.issues import IssueListResponse, IssueRead
from services.pipeline import enqueue_extraction
from services.storage.local import LocalStorage
from services.uploads import UploadService

router = APIRouter(prefix="/documents", tags=["documents"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.get("", response_model=DocumentListResponse, responses=NOT_READY)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    """List documents visible to the current user."""

    total = (await session.execute(select(func.count(Document.id)))).scalar_one()
    rows = (
        (
            await session.execute(
                select(Document)
                .order_by(Document.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return DocumentListResponse(
        documents=[DocumentRead.model_validate(d) for d in rows],
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
) -> DocumentUploadResponse:
    """Persist a validated document and enqueue canonical extraction."""

    result = await upload_service.create_or_reuse(file, session)
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRead:
    """Return safe metadata for one document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRead.model_validate(document)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses=NOT_READY,
)
async def get_document_status(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentStatusResponse:
    """Return processing progress and latest stage states."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    stage_runs = (
        (
            await session.execute(
                select(StageRun)
                .where(StageRun.document_id == document_id)
                .order_by(StageRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        review_status=document.review_status,
        progress_pct=document.progress_pct,
        stages=[StageRunRead.model_validate(r) for r in stage_runs],
        updated_at=document.updated_at,
    )


@router.get(
    "/{document_id}/issues",
    response_model=IssueListResponse,
    responses=NOT_READY,
)
async def list_document_issues(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    category: IssueCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssueListResponse:
    """List issues with optional canonical category filtering."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

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
        counts_by_severity[sev] = count

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
    "/{document_id}/pdf",
    response_class=FileResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document or canonical PDF not found",
        }
    },
)
async def get_document_pdf(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> FileResponse:
    """Stream the canonical PDF rendition of an uploaded document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    uri = document.canonical_pdf_uri or document.storage_uri
    if not uri:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical PDF rendition not available.",
        )

    key = uri
    if key.startswith(storage.scheme):
        key = key[len(storage.scheme) :]

    path = storage._path_for_key(key)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on storage.",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=f"{document.safe_filename}.pdf",
        content_disposition_type="inline",
    )


@router.post(
    "/{document_id}/disposition",
    response_model=DocumentRead,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def set_document_disposition(
    document_id: UUID,
    payload: DocumentDispositionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRead:
    """Apply final Lead Reviewer disposition to an audited document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    previous_state = {"review_status": document.review_status.value}
    document.review_status = payload.disposition
    new_state = {"review_status": document.review_status.value}

    audit_event = AuditEvent(
        document_id=document.id,
        issue_id=None,
        actor_id=payload.actor_id,
        actor_role=payload.actor_role,
        action="DOCUMENT_DISPOSITION",
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.justification,
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(document)

    return DocumentRead.model_validate(document)


@router.get(
    "/{document_id}/audit-events",
    response_model=AuditEventListResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def list_document_audit_events(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuditEventListResponse:
    """List immutable audit events for an audited document in chronological order."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    events = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.document_id == document_id)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            )
        )
        .scalars()
        .all()
    )

    return AuditEventListResponse(
        events=[AuditEventRead.model_validate(e) for e in events],
        total=len(events),
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
) -> TraceabilitySummaryResponse:
    """Return traceability counts for audit triage."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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
        sev_key = issue.severity.value
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1
        if issue.severity == Severity.CRITICAL:
            critical_count += 1
        if issue.decision is None:
            unresolved_count += 1

    return TraceabilitySummaryResponse(
        document_id=document.id,
        counts_by_type=counts_by_type,
        counts_by_severity=counts_by_severity,
        critical_count=critical_count,
        unresolved_count=unresolved_count,
    )


@router.get(
    "/{document_id}/export",
    response_class=Response,
    responses=NOT_READY,
)
async def export_document(
    document_id: UUID,
    format: Annotated[str, Query(pattern=r"^(pdf|xlsx|csv)$")],
) -> Response:
    """Export the annotated rendition or structured issue log."""

    feature_not_ready("Document export")
