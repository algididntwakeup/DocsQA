"""Project-scoped document endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.dependencies import get_current_user, get_upload_service, require_lead
from db.session import get_session
from domain.enums import DocumentStatus, Severity, UserRole
from models.document import Document
from models.issue import Issue
from models.project import Project
from models.user import User
from schemas.documents import DocumentListResponse, DocumentRead, DocumentUploadResponse
from schemas.project import ProjectAssignment, ProjectCreate, ProjectRead
from services.pipeline import enqueue_extraction
from services.uploads import UploadService

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_read(project: Project) -> ProjectRead:
    data = ProjectRead.model_validate(project).model_dump()
    data.update(
        created_by_name=project.created_by.full_name if project.created_by else None,
        assigned_to_name=project.assigned_to.full_name if project.assigned_to else None,
        total_documents=len(project.documents),
        status="NO_DOCUMENTS" if not project.documents else "ACTIVE",
    )
    return ProjectRead(**data)


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectRead:
    """Create a project for lead users."""
    project = Project(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        plant_area=payload.plant_area,
        created_by_id=current_user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project, attribute_names=["created_by", "assigned_to", "documents"])
    await session.refresh(project, attribute_names=["created_by", "assigned_to", "documents"])
    return _project_read(project)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: UUID | None = None,
) -> list[ProjectRead]:
    """List projects visible to the authenticated user."""
    query = select(Project).options(
        joinedload(Project.created_by),
        joinedload(Project.assigned_to),
        joinedload(Project.documents),
    )
    if user_id is not None:
        query = query.where(Project.assigned_to_id == user_id)
        if (
            current_user.role not in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}
            and user_id != current_user.id
        ):
            query = query.where(Project.id == UUID(int=0))
    elif current_user.role not in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}:
        query = query.where(
            (Project.assigned_to_id == current_user.id)
            | exists().where(
                Document.project_id == Project.id,
                or_(
                    Document.assigned_to_id == current_user.id,
                    Document.owner_id == current_user.id,
                ),
            )
        )
    projects = (
        (await session.execute(query.order_by(Project.created_at.desc())))
        .unique()
        .scalars()
        .all()
    )
    return [_project_read(project) for project in projects]


@router.patch("/{project_id}/assign", response_model=ProjectRead)
async def assign_project(
    project_id: UUID,
    payload: ProjectAssignment,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
) -> ProjectRead:
    """Assign or unassign a project to an active user."""
    project = (
        await session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(
                joinedload(Project.created_by),
                joinedload(Project.assigned_to),
                joinedload(Project.documents),
            )
        )
    ).unique().scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.assigned_to_id is not None:
        assigned = (
            await session.execute(
                select(User).where(User.id == payload.assigned_to_id, User.is_active.is_(True))
            )
        ).scalar_one_or_none()
        if assigned is None:
            raise HTTPException(status_code=404, detail="Assigned user not found or inactive.")
    project.assigned_to_id = payload.assigned_to_id
    await session.commit()
    await session.refresh(project)
    return _project_read(project)


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
    query = select(Document).where(Document.project_id == project_id).options(
        joinedload(Document.owner), joinedload(Document.assigned_to)
    )
    if current_user.role == UserRole.ENGINEER:
        query = query.where(
            or_(Document.assigned_to_id == current_user.id, Document.owner_id == current_user.id)
        )
    elif engineer_id is not None:
        query = query.where(Document.assigned_to_id == engineer_id)
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
        documents=[
            DocumentRead.model_validate(document).model_copy(
                update={
                    "owner_name": document.owner.full_name if document.owner else None,
                    "assigned_to_name": (
                        document.assigned_to.full_name if document.assigned_to else None
                    ),
                    "assigned_to_email": (
                        document.assigned_to.email if document.assigned_to else None
                    ),
                }
            )
            for document in documents
        ],
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
