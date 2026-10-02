"""Project-scoped document endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from api.auth import upsert_bima_user
from core.dependencies import get_current_user, get_upload_service, require_lead
from db.session import get_session
from domain.enums import DocumentStatus, Severity, UserRole
from models.document import Document
from models.issue import Issue
from models.project import Project
from models.user import User
from schemas.common import PageInfo
from schemas.documents import DocumentListResponse, DocumentRead, DocumentUploadResponse
from schemas.project import (
    ProjectAssignment,
    ProjectCreate,
    ProjectHeaderConfigUpdate,
    ProjectRead,
)
from services import bima_client as bima_client
from services.bima_adapter import BimaMasterDataAdapter
from services.pipeline import enqueue_extraction
from services.uploads import UploadService

router = APIRouter(prefix="/projects", tags=["projects"])


TERMINAL_DOCUMENT_STATUSES = {
    DocumentStatus.COMPLETED,
    DocumentStatus.COMPLETED_WITH_WARNINGS,
    DocumentStatus.FAILED,
}


def _project_status(project: Project) -> str:
    if project.finished_at is not None:
        return "FINISHED"
    return "NO_DOCUMENTS" if not project.documents else "ACTIVE"


def _project_read(project: Project) -> ProjectRead:
    data = ProjectRead.model_validate(project).model_dump()
    data.update(
        created_by_name=project.created_by.full_name if project.created_by else None,
        assigned_to_name=project.assigned_to.full_name if project.assigned_to else None,
        total_documents=len(project.documents),
        # The API status remains the PRISM lifecycle status; BIMA's raw status
        # is persisted separately on Project for synchronization decisions.
        status=_project_status(project),
    )
    return ProjectRead(**data)


async def _load_project_for_mutation(session: AsyncSession, project_id: UUID) -> Project:
    project = (
        (
            await session.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(
                    joinedload(Project.created_by),
                    joinedload(Project.assigned_to),
                    joinedload(Project.documents),
                )
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


def _ensure_project_open(project: Project) -> None:
    if project.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is finished; assignment and review changes are disabled.",
        )


@router.post("/sync-bima")
async def sync_bima_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
    bima_token: Annotated[str | None, Header(alias="X-BIMA-Token")] = None,
    bima_cookie: Annotated[str | None, Cookie(alias="bima_access_token")] = None,
) -> dict[str, int]:
    """Synchronize BIMA projects and their members into the local master data."""
    token = bima_token or bima_cookie
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="BIMA token is required to sync projects.",
        )
    remote_projects = await bima_client.fetch_bima_projects(token)
    remote_users = await bima_client.fetch_bima_users(token)
    master = BimaMasterDataAdapter().adapt(remote_projects, remote_users)
    created = 0
    updated = 0
    try:
        user_by_bima_id: dict[int, User] = {}
        for record in master.users:
            user = await upsert_bima_user(
                session,
                {
                    "bima_id": record.bima_id,
                    "email": record.email,
                    "full_name": record.full_name,
                    "role": record.role,
                    "department": record.department,
                    "position": record.position,
                },
                commit=False,
            )
            user_by_bima_id[record.bima_id] = user
        for remote in master.projects:
            project = (
                await session.execute(
                    select(Project)
                    .options(selectinload(Project.members))
                    .where(Project.bima_project_id == remote.bima_project_id)
                )
            ).scalar_one_or_none()
            if project is None:
                project = Project(
                    name=remote.name,
                    code=remote.code,
                    description=remote.description,
                    plant_area=remote.plant_area,
                    status=remote.status,
                    created_by_id=current_user.id,
                    bima_project_id=remote.bima_project_id,
                    members=[user_by_bima_id[bima_id] for bima_id in remote.member_bima_ids],
                )
                session.add(project)
                created += 1
            else:
                updated += 1
                project.members = [user_by_bima_id[bima_id] for bima_id in remote.member_bima_ids]
            project.name = remote.name
            project.code = remote.code
            project.description = remote.description
            project.plant_area = remote.plant_area
            project.status = remote.status
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA sync could not be applied; no changes were saved.",
        ) from exc
    return {"synced": len(master.projects), "created": created, "updated": updated}


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
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
            | Project.members.any(User.id == current_user.id)
            | exists().where(
                Document.project_id == Project.id,
                or_(
                    Document.assigned_to_id == current_user.id,
                    Document.owner_id == current_user.id,
                ),
            )
        )
    projects = (
        (await session.execute(query.order_by(Project.created_at.desc()))).unique().scalars().all()
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
    project = await _load_project_for_mutation(session, project_id)
    _ensure_project_open(project)
    if payload.assigned_to_id is not None:
        assigned = (
            await session.execute(
                select(User).where(User.id == payload.assigned_to_id, User.is_active.is_(True))
            )
        ).scalar_one_or_none()
        if assigned is None:
            raise HTTPException(status_code=404, detail="Assigned user not found or inactive.")
    project.assigned_to_id = payload.assigned_to_id
    project.assigned_to = assigned if payload.assigned_to_id is not None else None
    await session.commit()
    await session.refresh(project, attribute_names=["created_by", "assigned_to", "documents"])
    return _project_read(project)


@router.put("/{project_id}/header-config", response_model=ProjectRead)
async def update_project_header_config(
    project_id: UUID,
    payload: ProjectHeaderConfigUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
) -> ProjectRead:
    """Save the default document header template for this project."""
    project = await _load_project_for_mutation(session, project_id)
    _ensure_project_open(project)
    project.header_config = payload.header_config.model_dump()
    await session.commit()
    await session.refresh(project, attribute_names=["created_by", "assigned_to", "documents"])
    return _project_read(project)


@router.post("/{project_id}/finish", response_model=ProjectRead)
async def finish_project(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
) -> ProjectRead:
    """Finish a project and make its review workspace read-only."""
    project = await _load_project_for_mutation(session, project_id)
    if project.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is already finished.",
        )
    unfinished = [
        document.original_filename
        for document in project.documents
        if document.status not in TERMINAL_DOCUMENT_STATUSES
    ]
    if unfinished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Project cannot be finished while documents are still processing.",
                "documents": unfinished,
            },
        )
    project.finished_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(project, attribute_names=["created_by", "assigned_to", "documents"])
    return _project_read(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
) -> None:
    """Delete an empty project; documents are never deleted implicitly."""
    project = await _load_project_for_mutation(session, project_id)
    if project.documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project cannot be deleted while it contains documents.",
        )
    await session.delete(project)
    await session.commit()


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
    query = (
        select(Document)
        .where(Document.project_id == project_id)
        .options(
            joinedload(Document.owner),
            joinedload(Document.assigned_to),
            joinedload(Document.project).selectinload(Project.members),
        )
    )
    project = (
        await session.execute(
            select(Project).options(selectinload(Project.members)).where(Project.id == project_id)
        )
    ).scalar_one_or_none()
    member_ids = {member.id for member in project.members} if project is not None else set()
    is_member = current_user.id in member_ids
    bima_backed = project is not None and project.bima_project_id is not None
    if current_user.role == UserRole.ENGINEER:
        if bima_backed:
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project.",
                )
        else:
            query = query.where(
                or_(
                    Document.assigned_to_id == current_user.id,
                    Document.owner_id == current_user.id,
                )
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
                    "project_finished": bool(document.project and document.project.finished_at),
                }
            )
            for document in documents
        ],
        pagination=PageInfo(
            page=1,
            page_size=max(1, len(documents)),
            total=len(documents),
        ),
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
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    _ensure_project_open(project)
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
