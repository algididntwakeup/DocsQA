"""Project-scoped document endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_upload_service
from db.session import get_session
from domain.enums import DocumentStatus, Severity, UserRole
from models.document import Document
from models.issue import Issue
from models.project import Project
from models.user import User
from schemas.documents import DocumentListResponse, DocumentRead, DocumentUploadResponse
from schemas.project import ProjectRead
from services.pipeline import enqueue_extraction
from services.uploads import UploadService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProjectRead]:
    """List projects visible to the authenticated user."""
    query = select(Project)
    if current_user.role != UserRole.LEAD_ENGINEER:
        query = query.where(
            exists().where(Document.project_id == Project.id, Document.owner_id == current_user.id)
        )
    projects = (await session.execute(query.order_by(Project.created_at.desc()))).scalars().all()
    return [ProjectRead.model_validate(project) for project in projects]


@router.get("/{project_id}/documents", response_model=DocumentListResponse)
async def list_project_documents(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    engineer_id: UUID | None = None,
    sort_by: Annotated[str, Query(pattern=r"^(date_desc|date_asc)$")] = "date_desc",
    workflow_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    has_blockers: bool | None = None,
) -> DocumentListResponse:
    """List project documents with lead-only cross-engineer filters."""
    query = select(Document).where(Document.project_id == project_id)
    if current_user.role != UserRole.LEAD_ENGINEER:
        query = query.where(Document.owner_id == current_user.id)
    elif engineer_id is not None:
        query = query.where(Document.owner_id == engineer_id)
    if workflow_status is not None:
        query = query.where(Document.status == workflow_status)
    if has_blockers is not None:
        blocker = exists().where(
            Issue.document_id == Document.id,
            Issue.severity.in_([Severity.BLOCKER, Severity.CRITICAL, "HIGH"]),
            Issue.included_in_report.is_(True),
        )
        query = query.where(blocker if has_blockers else ~blocker)
    order = Document.created_at.desc() if sort_by == "date_desc" else Document.created_at.asc()
    documents = (await session.execute(query.order_by(order))).scalars().all()
    return DocumentListResponse(
        documents=[DocumentRead.model_validate(document) for document in documents],
        pagination={"page": 1, "page_size": max(1, len(documents)), "total": len(documents)},
    )


@router.post(
    "/{project_id}/documents/upload", response_model=DocumentUploadResponse, status_code=201
)
async def upload_project_document(
    project_id: UUID,
    file: Annotated[UploadFile, File(description="Native-text PDF or DOCX")],
    session: Annotated[AsyncSession, Depends(get_session)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentUploadResponse:
    """Upload a document and assign its project and owner."""
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found."
        )
    result = await upload_service.create_or_reuse(file, session)
    if not result.deduplicated:
        result.document.project_id = project_id
        result.document.owner_id = current_user.id
        await session.commit()
        await session.refresh(result.document)
        await enqueue_extraction(result.document, session)
    return DocumentUploadResponse(
        id=result.document.id,
        filename=result.document.original_filename,
        status=result.document.status,
        created_at=result.document.created_at,
        deduplicated=result.deduplicated,
    )
