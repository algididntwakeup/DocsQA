"""Endpoints for listing and importing projects from BIMA."""

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.projects import _project_read
from core.dependencies import get_current_user, get_storage
from db.session import get_session
from models.project import Project
from models.user import User
from schemas.project import (
    BimaProjectItem,
    BimaProjectListResponse,
    ImportBimaProjectRequest,
    ProjectRead,
)
from services.bima_service import BimaService
from services.storage import LocalStorage

router = APIRouter(tags=["bima"])


def get_bima_service() -> BimaService:
    """Build the configured BIMA client for one request."""

    return BimaService()


def _require_bearer_token(authorization: str | None) -> str:
    """Extract a BIMA bearer token from the incoming Authorization header."""

    parts = authorization.split() if authorization else []
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A BIMA Bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def _project_fields(record: dict[str, Any]) -> tuple[int, str, str, str]:
    """Normalize the BIMA fields used by PRISM and reject incomplete upstream records."""

    raw_id = record.get("id")
    if raw_id is None:
        raw_id = record.get("bima_project_id")
    try:
        if raw_id is None:
            raise ValueError("missing ID")
        bima_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA project record has an invalid ID.",
        ) from exc

    raw_name = record.get("name")
    raw_number = record.get("number", record.get("project_number"))
    raw_client_name = record.get("client_name", record.get("client", ""))
    if isinstance(raw_client_name, dict):
        raw_client_name = raw_client_name.get("name", "")

    if (
        bima_id < 1
        or not isinstance(raw_name, str)
        or not raw_name.strip()
        or raw_number is None
        or not str(raw_number).strip()
        or not isinstance(raw_client_name, str)
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA project record is missing a valid number, name, or client name.",
        )
    return bima_id, str(raw_number), raw_name, raw_client_name


def _remove_empty_workspace(path: Path | None) -> None:
    """Remove only the newly-created empty project directory after a failed import."""

    if path is None:
        return
    with suppress(OSError):
        path.rmdir()


@router.get("/bima/projects", response_model=BimaProjectListResponse)
async def list_bima_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    _current_user: Annotated[User, Depends(get_current_user)],
    bima_service: Annotated[BimaService, Depends(get_bima_service)],
    authorization: Annotated[str | None, Header()] = None,
    bima_cookie: Annotated[str | None, Cookie(alias="bima_access_token")] = None,
) -> BimaProjectListResponse:
    """List projects visible to the BIMA user and mark any already imported."""

    # The browser's Authorization header contains the PRISM session JWT. SSO stores
    # the upstream BIMA credential in its own HttpOnly cookie.
    token = bima_cookie or _require_bearer_token(authorization)
    remote_records = await bima_service.list_projects(token)
    normalized = [_project_fields(record) for record in remote_records]
    bima_ids = [bima_id for bima_id, _, _, _ in normalized]

    imported_by_id: dict[int, Project] = {}
    if bima_ids:
        result = await session.execute(
            select(Project).where(Project.bima_project_id.in_(bima_ids))
        )
        imported_by_id = {
            project.bima_project_id: project
            for project in result.scalars().all()
            if project.bima_project_id is not None
        }

    items: list[BimaProjectItem] = []
    for bima_id, number, name, client_name in normalized:
        imported = imported_by_id.get(bima_id)
        try:
            item = BimaProjectItem(
                id=bima_id,
                number=number,
                name=name,
                client_name=client_name,
                is_imported=imported is not None,
                prism_project_id=str(imported.id) if imported is not None else None,
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA project record does not match the project contract.",
            ) from exc
        items.append(item)

    return BimaProjectListResponse(success=True, data=items)


@router.post(
    "/projects/import-bima",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def import_bima_project(
    payload: ImportBimaProjectRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    bima_service: Annotated[BimaService, Depends(get_bima_service)],
    authorization: Annotated[str | None, Header()] = None,
    bima_cookie: Annotated[str | None, Cookie(alias="bima_access_token")] = None,
) -> ProjectRead:
    """Import one BIMA project into PRISM and create its workspace directory."""

    token = bima_cookie or _require_bearer_token(authorization)
    existing = (
        await session.execute(
            select(Project).where(Project.bima_project_id == payload.bima_project_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This BIMA project has already been imported.",
        )

    remote = await bima_service.get_project(payload.bima_project_id, token)
    bima_id, number, name, client_name = _project_fields(remote)
    if bima_id != payload.bima_project_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA returned a different project than the requested ID.",
        )

    project = Project(
        id=uuid4(),
        name=name,
        bima_project_id=bima_id,
        project_number=number,
        client_name=client_name,
        created_by_id=current_user.id,
        created_by=current_user,
        assigned_to=None,
        documents=[],
        created_at=datetime.now(UTC),
    )
    workspace_path = None
    try:
        session.add(project)
        await session.flush()
        await session.refresh(project, attribute_names=["created_at"])
        workspace_path = storage.get_full_path(f"projects/{project.id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        _remove_empty_workspace(workspace_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This BIMA project has already been imported.",
        ) from exc
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
