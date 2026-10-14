"""Project-scoped document endpoints."""

import logging
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from core.dependencies import (
    get_current_user,
    get_storage,
    get_upload_service,
    require_lead,
    require_superuser,
)
from db.session import get_session
from domain.enums import DocumentStatus, Severity
from models.document import Document
from models.issue import Issue
from models.project import Project
from models.user import User
from schemas.common import PageInfo
from schemas.documents import DocumentListResponse, DocumentRead, DocumentUploadResponse
from schemas.project import (
    ImportBimaProjectRequest,
    PortfolioOwnerCount,
    PortfolioStatsRead,
    ProjectCreate,
    ProjectHeaderConfigUpdate,
    ProjectRead,
)
from services.permission_service import (
    can_create_project,
    can_manage_folders,
    create_permission_message,
    folder_permission_message,
    has_workspace_oversight,
)
from services.pipeline import enqueue_extraction
from services.storage import LocalStorage
from services.uploads import UploadService

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


TERMINAL_DOCUMENT_STATUSES = {
    DocumentStatus.COMPLETED,
    DocumentStatus.COMPLETED_WITH_WARNINGS,
    DocumentStatus.FAILED,
}


def _project_status(project: Project, total_documents: int | None = None) -> str:
    if project.finished_at is not None:
        return "FINISHED"
    has_documents = bool(project.documents) if total_documents is None else total_documents > 0
    return "ACTIVE" if has_documents else "NO_DOCUMENTS"


def _project_read(project: Project, total_documents: int | None = None) -> ProjectRead:
    data = ProjectRead.model_validate(project).model_dump()
    count = len(project.documents) if total_documents is None else total_documents
    data.update(
        owner_name=project.owner.full_name if project.owner else None,
        total_documents=count,
        status=_project_status(project, count),
    )
    return ProjectRead(**data)


async def _load_project_for_mutation(session: AsyncSession, project_id: UUID) -> Project:
    project = (
        (
            await session.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(
                    joinedload(Project.owner),
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
            detail="Project is finished; review changes are disabled.",
        )


def _remove_empty_workspace(path: Path | None) -> None:
    """Remove only the newly-created empty project directory after a failed import."""

    if path is None:
        return
    with suppress(OSError):
        path.rmdir()


@router.post("/import-bima", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def import_bima_project(
    payload: ImportBimaProjectRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> ProjectRead:
    """Import one BIMA catalog project on demand and assign its PRISM owner.

    Importing is idempotent per owner: the same BIMA project may exist once in
    each user's workspace. A project already owned by the caller is returned
    unchanged with ``200 OK``; a second user importing the same BIMA project
    receives ``201`` with a new project they own. A new project is created with
    the calling user as its owner and gets an empty workspace directory.
    """

    existing = (
        await session.execute(
            select(Project)
            .options(joinedload(Project.owner))
            .where(
                Project.bima_project_id == payload.bima_project_id,
                Project.owner_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _project_read(existing, total_documents=0)

    # Importing provisions the project workspace folder, so the folder RBAC
    # applies: engineering (13) numbers belong to engineering roles, internal
    # (03) numbers to HR/GA and finance.
    if not can_manage_folders(current_user.role, payload.project_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=folder_permission_message(payload.project_number),
        )

    project = Project(
        id=uuid4(),
        name=payload.name,
        bima_project_id=payload.bima_project_id,
        project_number=payload.project_number,
        client_name=payload.client_name,
        owner_id=current_user.id,
        owner=current_user,
        documents=[],
    )
    workspace_path = None
    try:
        session.add(project)
        await session.flush()
        await session.refresh(project, attribute_names=["owner", "documents"])
        workspace_path = storage.get_full_path(f"projects/{project.id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        await session.commit()
    except IntegrityError:
        # A concurrent import won the race; return the row it created.
        await session.rollback()
        _remove_empty_workspace(workspace_path)
        winner = (
            await session.execute(
                select(Project)
                .options(joinedload(Project.owner))
                .where(
                    Project.bima_project_id == payload.bima_project_id,
                    Project.owner_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if winner is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This BIMA project could not be imported into PRISM.",
            ) from None
        response.status_code = status.HTTP_200_OK
        return _project_read(winner, total_documents=0)
    except OSError as exc:
        await session.rollback()
        _remove_empty_workspace(workspace_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The PRISM project workspace could not be created.",
        ) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        _remove_empty_workspace(workspace_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The BIMA project could not be imported into PRISM.",
        ) from exc

    return _project_read(project, total_documents=0)


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectRead:
    """Create a project and its workspace folder under the folder RBAC rules.

    Numbered projects are restricted by prefix: ``13`` engineering projects are
    owned by engineering roles, ``03`` internal projects by HR/GA and finance.
    Unnumbered projects keep the legacy lead-only rule. Accounts carrying the
    local superuser flag bypass every rule: BIMA's flat directory cannot express
    cross-department oversight, so the flag is the only way to create a project
    outside the caller's own prefix.
    """
    if not current_user.is_superuser and not can_create_project(
        current_user.role, payload.project_number
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_permission_message(payload.project_number),
        )
    project = Project(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        plant_area=payload.plant_area,
        project_number=payload.project_number,
        owner_id=current_user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project, attribute_names=["owner", "documents"])
    return _project_read(project)


def _visible_projects_query(current_user: User) -> Any:
    """Build the project listing query with the caller's visibility scope.

    Visibility is strictly the caller's own projects, except for accounts that
    carry workspace oversight (lead engineers and locally flagged superusers):
    they see every workspace for cross-user review. The admin screen uses
    ``/api/v1/auth/users/{user_id}/projects``, which is guarded separately.
    """

    query = select(
        Project,
        func.coalesce(func.count(Document.id), 0).label("total_documents"),
    ).outerjoin(Document, Document.project_id == Project.id).options(
        # The listing groups by ``projects.id``, so the owner must be loaded with
        # a separate SELECT (selectinload). A joinedload would add ``users``
        # columns to the GROUP BY query and PostgreSQL rejects that with
        # GroupingError ("column users_1.id must appear in the GROUP BY clause").
        selectinload(Project.owner),
    )
    if not has_workspace_oversight(current_user):
        query = query.where(Project.owner_id == current_user.id)
    return query


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProjectRead]:
    """List the caller's own projects."""
    query = _visible_projects_query(current_user)
    project_result = await session.execute(
        query.group_by(Project.id).order_by(Project.created_at.desc())
    )
    all_rows = getattr(project_result, "all", None)
    if callable(all_rows):
        rows = all_rows()
        return [_project_read(project, count) for project, count in rows]
    projects = project_result.unique().scalars().all()
    return [_project_read(project, len(project.documents)) for project in projects]


@router.get("/stats", response_model=PortfolioStatsRead)
async def get_portfolio_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_superuser)],
) -> PortfolioStatsRead:
    """Return cross-workspace counters for the superuser control panel."""
    total_projects = await session.scalar(select(func.count(Project.id)))
    finished_projects = await session.scalar(
        select(func.count(Project.id)).where(Project.finished_at.isnot(None))
    )
    total_documents = await session.scalar(select(func.count(Document.id)))
    by_status = await session.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    by_workflow = await session.execute(
        select(Document.workflow_status, func.count(Document.id)).group_by(Document.workflow_status)
    )
    owner_rows = (
        await session.execute(
            select(
                User.id,
                User.full_name,
                func.count(func.distinct(Project.id)).label("project_count"),
                func.count(func.distinct(Document.id)).label("document_count"),
            )
            .outerjoin(Project, Project.owner_id == User.id)
            .outerjoin(Document, Document.owner_id == User.id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(func.distinct(Project.id)).desc(), User.full_name.asc())
        )
    ).all()
    return PortfolioStatsRead(
        total_projects=int(total_projects or 0),
        finished_projects=int(finished_projects or 0),
        total_documents=int(total_documents or 0),
        documents_by_status={str(key): int(count) for key, count in by_status.all()},
        documents_by_workflow={str(key): int(count) for key, count in by_workflow.all()},
        projects_by_owner=[
            PortfolioOwnerCount(
                owner_id=row[0],
                owner_name=row[1],
                project_count=int(row[2] or 0),
                document_count=int(row[3] or 0),
            )
            for row in owner_rows
        ],
    )


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
    await session.refresh(project, attribute_names=["owner", "documents"])
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
    await session.refresh(project, attribute_names=["owner", "documents"])
    return _project_read(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete an empty custom project; documents are never deleted implicitly.

    Projects imported from BIMA are permanent: they represent a real upstream
    directory entry, so removing the local folder would desynchronise PRISM from
    BIMA. Only custom projects (``bima_project_id is None``) may be deleted, and
    only by their owner or a locally flagged superuser.
    """
    project = await _load_project_for_mutation(session, project_id)
    if project.bima_project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="BIMA imported projects cannot be deleted.",
        )
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or a superuser can delete this project.",
        )
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
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    """List project documents with lead-only cross-engineer filters."""
    query = (
        select(Document)
        .where(Document.project_id == project_id)
        .options(
            joinedload(Document.owner),
            joinedload(Document.assigned_to),
            joinedload(Document.project),
        )
    )
    # Every non-oversight role (engineers, HR/GA, finance) is scoped to its own
    # documents; lead engineers and locally flagged superusers get the
    # cross-engineer view and filters.
    if not has_workspace_oversight(current_user):
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
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    documents = (
        await session.execute(
            query.order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
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
        pagination=PageInfo(page=page, page_size=page_size, total=total),
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
