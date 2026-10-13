"""On-demand BIMA import: flat catalog annotation and owner assignment."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from api.bima import get_bima_service
from core.dependencies import get_current_user, get_storage
from db.session import get_session
from domain.enums import UserRole
from main import app
from models.project import Project
from models.user import User
from services.storage import LocalStorage


def _engineer() -> User:
    return User(
        id=uuid4(),
        email="engineer@bima-import.test",
        hashed_password="unused",
        full_name="BIMA Engineer",
        role=UserRole.ENGINEER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


class _StubBimaService:
    """Minimal stand-in exposing only the flat catalog call PRISM still makes."""

    def __init__(
        self,
        projects: list[dict[str, Any]] | None = None,
        my_projects: list[dict[str, Any]] | None = None,
    ) -> None:
        self.projects = projects or []
        self.my_projects = my_projects or []
        self.list_calls: list[str] = []
        self.my_list_calls: list[str] = []
        self.my_error: Exception | None = None

    async def list_projects(self, token: str) -> list[dict[str, Any]]:
        self.list_calls.append(token)
        return self.projects

    async def list_my_projects(self, token: str) -> list[dict[str, Any]]:
        self.my_list_calls.append(token)
        if self.my_error is not None:
            raise self.my_error
        return self.my_projects


def _install_overrides(
    session: AsyncMock,
    user: User,
    service: _StubBimaService,
    storage: LocalStorage | None = None,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    previous: dict[Callable[..., Any], Callable[..., Any]] = dict(app.dependency_overrides)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_bima_service] = lambda: service
    if storage is not None:
        app.dependency_overrides[get_storage] = lambda: storage
    return previous


def _restore_overrides(previous: dict[Callable[..., Any], Callable[..., Any]]) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.mark.anyio
async def test_catalog_marks_imported_projects() -> None:
    """The flat catalog annotates the caller's import state and ongoing projects."""

    user = _engineer()
    prism_id = uuid4()
    now = datetime.now(UTC)
    owned = Project(
        id=prism_id,
        name="Plant Upgrade",
        bima_project_id=627,
        project_number="13726486.01",
        client_name="Example Client",
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [owned])
    )
    service = _StubBimaService(
        projects=[
            {
                "id": 627,
                "number": "13726486.01",
                "name": "Plant Upgrade",
                "client_name": "Example Client",
            },
            {"id": 628, "number": "13726486.02", "name": "New Facility"},
        ],
        my_projects=[
            {
                "id": 628,
                "number": "13726486.02",
                "name": "New Facility",
                "client_name": None,
            }
        ],
    )
    previous = _install_overrides(session, user, service)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/bima/catalog",
                headers={"Authorization": "Bearer engineer-token"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    imported, fresh = items
    assert imported == {
        "id": 627,
        "number": "13726486.01",
        "name": "Plant Upgrade",
        "client_name": "Example Client",
        "is_imported": True,
        "prism_project_id": str(prism_id),
        "is_mine": False,
        "bima_owner_known": True,
    }
    assert fresh == {
        "id": 628,
        "number": "13726486.02",
        "name": "New Facility",
        "client_name": None,
        "is_imported": False,
        "prism_project_id": None,
        "is_mine": True,
        "bima_owner_known": True,
    }
    assert service.list_calls == ["engineer-token"]
    assert service.my_list_calls == ["engineer-token"]
    # The import annotation is scoped to the calling user's own workspace.
    statement = str(session.execute.call_args.args[0])
    assert "projects.owner_id" in statement
    # The row already carries the BIMA metadata, so no repair write happens.
    session.commit.assert_not_called()


@pytest.mark.anyio
async def test_catalog_degrades_when_my_projects_fails() -> None:
    """A failing /api/projects/mine lookup must not take down the catalog."""

    user = _engineer()
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [])
    )
    service = _StubBimaService(
        projects=[{"id": 627, "number": "13726486.01", "name": "Plant Upgrade"}]
    )
    service.my_error = HTTPException(
        status_code=502, detail="BIMA is unreachable."
    )
    previous = _install_overrides(session, user, service)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/bima/catalog",
                headers={"Authorization": "Bearer engineer-token"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    (item,) = response.json()
    assert item["is_mine"] is False
    assert item["bima_owner_known"] is False
    assert item["is_imported"] is False


@pytest.mark.anyio
async def test_catalog_repairs_missing_metadata_for_owned_rows() -> None:
    """Rows imported before the metadata migration are backfilled from BIMA."""

    user = _engineer()
    prism_id = uuid4()
    now = datetime.now(UTC)
    stale = Project(
        id=prism_id,
        name="Plant Upgrade",
        bima_project_id=627,
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [stale])
    )
    session.commit = AsyncMock()
    service = _StubBimaService(
        projects=[
            {
                "id": 627,
                "number": "13726486.01",
                "name": "Plant Upgrade",
                "client_name": "Example Client",
            }
        ]
    )
    previous = _install_overrides(session, user, service)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/bima/catalog",
                headers={"Authorization": "Bearer engineer-token"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    assert stale.project_number == "13726486.01"
    assert stale.client_name == "Example Client"
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_import_lookup_is_owner_scoped() -> None:
    """The idempotency lookup must not return another user's imported row."""

    user = _engineer()
    now = datetime.now(UTC)
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        value.created_at = now
        value.updated_at = now
        value.owner = user
        value.documents = []

    session.refresh.side_effect = refresh
    service = _StubBimaService()
    with TemporaryDirectory() as workspace_root:
        storage = LocalStorage(Path(workspace_root))
        previous = _install_overrides(session, user, service, storage)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/projects/import-bima",
                    headers={"Authorization": "Bearer prism-session-jwt"},
                    json={
                        "bima_project_id": 627,
                        "project_number": "13726486.01",
                        "name": "Plant Upgrade",
                        "client_name": "Example Client",
                    },
                )
        finally:
            _restore_overrides(previous)

    assert response.status_code == 201
    statement = str(session.execute.call_args.args[0])
    assert "projects.owner_id" in statement
    assert "projects.bima_project_id" in statement


@pytest.mark.anyio
async def test_import_assigns_owner_from_token_user(tmp_path: Path) -> None:
    """A new import is owned by the authenticated user and gets a workspace folder."""

    user = _engineer()
    now = datetime.now(UTC)
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        value.created_at = now
        value.updated_at = now
        value.owner = user
        value.documents = []

    session.refresh.side_effect = refresh
    service = _StubBimaService()
    storage = LocalStorage(tmp_path)
    previous = _install_overrides(session, user, service, storage)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"bima_access_token": "bima-engineer-token"},
        ) as client:
            response = await client.post(
                "/api/v1/projects/import-bima",
                headers={"Authorization": "Bearer prism-session-jwt"},
                json={
                    "bima_project_id": 627,
                    "project_number": "13726486.01",
                    "name": "Plant Upgrade",
                    "client_name": "Example Client",
                },
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 201
    body = response.json()
    project = session.add.call_args.args[0]
    assert body["id"] == str(project.id)
    assert body["owner_id"] == str(user.id)
    assert body["owner_name"] == user.full_name
    assert body["bima_project_id"] == 627
    assert body["project_number"] == "13726486.01"
    assert body["client_name"] == "Example Client"
    assert body["status"] == "NO_DOCUMENTS"
    assert project.name == "Plant Upgrade"
    assert project.owner_id == user.id
    assert (tmp_path / "projects" / str(project.id)).is_dir()
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_import_is_idempotent(tmp_path: Path) -> None:
    """Re-importing the same BIMA project returns the existing row with 200."""

    user = _engineer()
    now = datetime.now(UTC)
    existing = Project(
        id=uuid4(),
        name="Plant Upgrade",
        bima_project_id=627,
        project_number="13726486.01",
        client_name="Example Client",
        owner_id=user.id,
        owner=user,
        documents=[],
        created_at=now,
        updated_at=now,
    )
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: existing)
    session.add = MagicMock()
    service = _StubBimaService()
    storage = LocalStorage(tmp_path)
    previous = _install_overrides(session, user, service, storage)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/projects/import-bima",
                headers={"Authorization": "Bearer engineer-token"},
                json={
                    "bima_project_id": 627,
                    "project_number": "13726486.01",
                    "name": "Plant Upgrade",
                    "client_name": "Example Client",
                },
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    assert response.json()["id"] == str(existing.id)
    assert response.json()["owner_id"] == str(user.id)
    session.add.assert_not_called()
    assert list(tmp_path.iterdir()) == []
