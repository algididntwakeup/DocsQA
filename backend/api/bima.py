"""Endpoint that proxies the flat BIMA project catalog.

BIMA exposes only a flat directory (``id``/``number``/``name``/``client_name``)
and answers 404 on per-project detail lookups, so PRISM treats it as a read-only
catalog: the local import state is annotated here and importing is an explicit
on-demand action on the project endpoints.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from db.session import get_session
from models.project import Project
from models.user import User
from schemas.project import BimaCatalogItem
from services.bima_service import BimaService

router = APIRouter(tags=["bima"])

logger = logging.getLogger(__name__)


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


def _resolve_bima_token(
    authorization: str | None,
    bima_cookie: str | None,
    *,
    endpoint: str,
) -> str:
    """Pick the upstream BIMA credential for one request.

    The browser's ``Authorization`` header carries the PRISM session JWT, not the
    upstream BIMA credential, so the SSO-issued ``bima_access_token`` cookie wins
    whenever it is present. The header stays supported for direct API clients.
    """

    if bima_cookie:
        return bima_cookie
    token = _require_bearer_token(authorization)
    logger.warning(
        "Serving %s from the Authorization header because the bima_access_token cookie "
        "is missing; the PRISM session JWT is not a valid BIMA credential.",
        endpoint,
    )
    return token


def _catalog_fields(record: dict[str, Any]) -> tuple[int, str, str, str | None]:
    """Normalize one BIMA directory row and reject incomplete upstream records."""

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

    raw_name = record.get("name", record.get("project_name"))
    raw_number = record.get("number", record.get("project_number"))
    raw_client_name = record.get("client_name", record.get("client"))
    if isinstance(raw_client_name, dict):
        raw_client_name = raw_client_name.get("name")

    if (
        bima_id < 1
        or not isinstance(raw_name, str)
        or not raw_name.strip()
        or raw_number is None
        or not str(raw_number).strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA project record is missing a valid number or name.",
        )
    # BIMA does not always populate the client; a missing client must not fail
    # the whole catalog. Only a non-textual value is treated as corrupt.
    if raw_client_name is None:
        client_name: str | None = None
    elif isinstance(raw_client_name, str):
        client_name = raw_client_name.strip() or None
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA project record has an invalid client name.",
        )
    return bima_id, str(raw_number).strip(), raw_name.strip(), client_name


@router.get("/bima/catalog", response_model=list[BimaCatalogItem])
async def list_bima_catalog(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    bima_service: Annotated[BimaService, Depends(get_bima_service)],
    authorization: Annotated[str | None, Header()] = None,
    bima_cookie: Annotated[str | None, Cookie(alias="bima_access_token")] = None,
) -> list[BimaCatalogItem]:
    """Return the flat BIMA project catalog annotated with the caller's import state.

    Import flags describe the calling user's own workspace only, and rows that
    BIMA reports as the caller's ongoing projects are marked with ``is_mine``.
    """

    token = _resolve_bima_token(authorization, bima_cookie, endpoint="/bima/catalog")
    try:
        remote_records = await bima_service.list_projects(token)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected failure while listing the BIMA project catalog.")
        raise
    normalized = [_catalog_fields(record) for record in remote_records]
    bima_ids = [bima_id for bima_id, _, _, _ in normalized]

    # The caller's own ongoing BIMA projects are a UI hint only: a failure here
    # must not take down the catalog, so ownership markers are dropped instead.
    mine_ids: set[int] | None = None
    try:
        mine_records = await bima_service.list_my_projects(token)
        mine_ids = {bima_id for bima_id, _, _, _ in map(_catalog_fields, mine_records)}
    except HTTPException as exc:
        logger.warning(
            "BIMA ongoing-project lookup failed (status=%s); serving the catalog without "
            "ownership markers.",
            exc.status_code,
        )
    except Exception:
        logger.exception("Unexpected failure while listing the caller's ongoing BIMA projects.")

    owned_projects: list[Project] = []
    if bima_ids:
        owned_projects = list(
            (
                await session.execute(
                    select(Project).where(
                        Project.owner_id == current_user.id,
                        Project.bima_project_id.in_(bima_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
    imported_by_id = {
        project.bima_project_id: project.id
        for project in owned_projects
        if project.bima_project_id is not None
    }

    # Rows imported before ``20261007_0019_bima_project_metadata`` carry NULL
    # project_number/client_name, which the workspace grid renders as fallback
    # text. Fill only the caller's own empty fields from the catalog row.
    catalog_by_id: dict[int, tuple[str, str | None]] = {
        bima_id: (number, client_name) for bima_id, number, _, client_name in normalized
    }
    repaired = False
    for project in owned_projects:
        if project.bima_project_id is None:
            continue
        entry = catalog_by_id.get(project.bima_project_id)
        if entry is None:
            continue
        number, client_name = entry
        if project.project_number is None:
            project.project_number = number
            repaired = True
        if project.client_name is None and client_name is not None:
            project.client_name = client_name
            repaired = True
    if repaired:
        try:
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            logger.warning(
                "Could not backfill BIMA project metadata; serving the catalog unchanged."
            )

    return [
        BimaCatalogItem(
            id=bima_id,
            number=number,
            name=name,
            client_name=client_name,
            is_imported=bima_id in imported_by_id,
            prism_project_id=(
                str(imported_by_id[bima_id]) if bima_id in imported_by_id else None
            ),
            is_mine=mine_ids is not None and bima_id in mine_ids,
            bima_owner_known=mine_ids is not None,
        )
        for bima_id, number, name, client_name in normalized
    ]
