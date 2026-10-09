"""Tests for fetching and importing BIMA projects into PRISM."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
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
from services.bima_service import BimaService
from services.storage import LocalStorage


def _engineer() -> User:
    return User(
        id=uuid4(),
        email="engineer@bima-ingestion.test",
        hashed_password="unused",
        full_name="BIMA Engineer",
        role=UserRole.ENGINEER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


class _StubBimaService:
    def __init__(
        self,
        projects: list[dict[str, Any]] | None = None,
        project_detail: dict[str, Any] | None = None,
    ) -> None:
        self.projects = projects or []
        self.project_detail = project_detail
        self.list_calls: list[str] = []
        self.detail_calls: list[tuple[int, str]] = []

    async def list_projects(self, token: str) -> list[dict[str, Any]]:
        self.list_calls.append(token)
        return self.projects

    async def get_project(self, project_id: int, token: str) -> dict[str, Any]:
        self.detail_calls.append((project_id, token))
        if self.project_detail is None:
            raise AssertionError("No BIMA detail was configured for this test.")
        return self.project_detail


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
async def test_bima_service_forwards_bearer_and_fetches_list_and_detail() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/projects":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "projects": [
                            {
                                "id": 627,
                                "number": "13726486.01",
                                "name": "Plant Upgrade",
                                "client_name": "Example Client",
                            }
                        ]
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "project": {
                        "id": 627,
                        "number": "13726486.01",
                        "name": "Plant Upgrade",
                        "client_name": "Example Client",
                    }
                }
            },
        )

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    projects = await service.list_projects("engineer-token")
    project = await service.get_project(627, "engineer-token")

    assert service.timeout_seconds == 15.0
    assert projects[0]["number"] == "13726486.01"
    assert project["id"] == 627
    assert [request.url.path for request in requests] == [
        "/api/projects",
        "/api/projects/627",
    ]
    assert all(request.headers["Authorization"] == "Bearer engineer-token" for request in requests)
    # BIMA answers an HTML login redirect unless the call looks like an API client.
    assert all(request.headers["Accept"] == "application/json" for request in requests)
    assert all("PRISM-App" in request.headers["User-Agent"] for request in requests)


@pytest.mark.anyio
async def test_bima_service_treats_login_redirect_as_expired_token() -> None:
    """A 302 to /login must not surface as a bogus 502 'invalid JSON'."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/projects":
            return httpx.Response(302, headers={"location": "https://bima.test/login"})
        return httpx.Response(
            200, html="<html><head><title>Login | BIMA</title></head></html>"
        )

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 401
    assert "expired" in str(raised.value.detail).lower()


@pytest.mark.anyio
async def test_bima_service_treats_login_redirect_loop_as_expired_token() -> None:
    """BIMA can bounce /login back to itself; that is still an auth failure."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://bima.test/login"})

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 401
    assert "expired" in str(raised.value.detail).lower()


@pytest.mark.anyio
async def test_bima_service_follows_redirect_to_api_payload() -> None:
    """A trailing-slash or http->https redirect must still reach the JSON payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/projects":
            return httpx.Response(301, headers={"location": "https://bima.test/api/projects/"})
        return httpx.Response(200, json={"data": [{"id": 627, "number": "1", "name": "Plant"}]})

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    projects = await service.list_projects("engineer-token")

    assert projects == [{"id": 627, "number": "1", "name": "Plant"}]


@pytest.mark.anyio
async def test_bima_service_reports_html_error_page_instead_of_502_json() -> None:
    """An HTML error page must be logged as non-JSON, never parsed as a payload."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>Nginx error</body></html>")

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 502
    assert "invalid JSON" in str(raised.value.detail)


@pytest.mark.anyio
async def test_bima_service_sends_single_bearer_prefix() -> None:
    """A token arriving as 'Bearer Bearer x' must not be forwarded twice."""

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["Authorization"])
        return httpx.Response(200, json={"data": []})

    service = BimaService(base_url="https://bima.test", transport=httpx.MockTransport(handler))

    for token in ("plain-token", "Bearer plain-token", "Bearer Bearer plain-token"):
        await service.list_projects(token)

    assert seen == ["Bearer plain-token"] * 3


@pytest.mark.anyio
async def test_bima_service_maps_connect_error_to_bad_gateway() -> None:
    class ConnectFailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("name resolution failed", request=request)

        async def aclose(self) -> None:
            return None

    service = BimaService(base_url="https://bima.test", transport=ConnectFailTransport())

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 502
    assert raised.value.detail == "BIMA is unreachable."


@pytest.mark.anyio
async def test_bima_service_maps_upstream_failure_to_gateway_error() -> None:
    service = BimaService(
        base_url="https://bima.test",
        transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
    )

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 502
    assert "upstream error" in str(raised.value.detail)


@pytest.mark.anyio
async def test_bima_service_maps_timeout_to_gateway_timeout() -> None:
    class TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("BIMA timed out", request=request)

        async def aclose(self) -> None:
            return None

    service = BimaService(base_url="https://bima.test", transport=TimeoutTransport())

    with pytest.raises(HTTPException) as raised:
        await service.list_projects("engineer-token")

    assert raised.value.status_code == 504


@pytest.mark.anyio
async def test_list_bima_projects_marks_imported_projects(tmp_path: Path) -> None:
    user = _engineer()
    prism_id = uuid4()
    imported = Project(
        id=prism_id,
        name="Plant Upgrade",
        bima_project_id=627,
        created_by_id=user.id,
    )
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [imported]))
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = result
    service = _StubBimaService(
        projects=[
            {
                "id": 627,
                "number": "13726486.01",
                "name": "Plant Upgrade",
                "client_name": "Example Client",
            },
            {
                "id": 628,
                "number": "13726486.02",
                "name": "New Facility",
                "client_name": "Another Client",
            },
        ]
    )
    previous = _install_overrides(session, user, service)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/bima/projects",
                headers={"Authorization": "Bearer engineer-token"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"][0]["id"] == 627
    assert body["data"][0]["is_imported"] is True
    assert body["data"][0]["prism_project_id"] == str(prism_id)
    assert body["data"][1]["is_imported"] is False
    assert body["data"][1]["prism_project_id"] is None
    assert service.list_calls == ["engineer-token"]


@pytest.mark.anyio
async def test_list_bima_projects_prefers_bima_cookie_over_prism_jwt() -> None:
    """The PRISM session JWT is not a BIMA credential; the SSO cookie must win."""
    user = _engineer()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
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
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"bima_access_token": "bima-engineer-token"},
        ) as client:
            response = await client.get(
                "/api/v1/bima/projects",
                headers={"Authorization": "Bearer prism-session-jwt"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    assert service.list_calls == ["bima-engineer-token"]


@pytest.mark.anyio
async def test_list_bima_projects_accepts_missing_client_name() -> None:
    """BIMA does not always populate the client; the directory must still load."""

    user = _engineer()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    service = _StubBimaService(
        projects=[{"id": 900, "number": "13726486.09", "name": "Unassigned Client Plant"}]
    )
    previous = _install_overrides(session, user, service)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/bima/projects",
                headers={"Authorization": "Bearer engineer-token"},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert item["id"] == 900
    assert item["number"] == "13726486.09"
    assert item["name"] == "Unassigned Client Plant"
    assert item["client_name"] == ""


@pytest.mark.anyio
async def test_import_bima_project_creates_record_and_workspace(tmp_path: Path) -> None:
    user = _engineer()
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    session.execute.return_value = existing_result
    service = _StubBimaService(
        project_detail={
            "id": 627,
            "number": "13726486.01",
            "name": "Plant Upgrade",
            "client_name": "Example Client",
        }
    )
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
                json={"bima_project_id": 627},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 201
    body = response.json()
    project = session.add.call_args.args[0]
    assert body["id"] == str(project.id)
    assert body["bima_project_id"] == 627
    assert body["project_number"] == "13726486.01"
    assert body["client_name"] == "Example Client"
    assert project.name == "Plant Upgrade"
    assert project.created_by_id == user.id
    assert service.detail_calls == [(627, "bima-engineer-token")]
    assert (tmp_path / "projects" / str(project.id)).is_dir()
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_duplicate_bima_project_import_returns_conflict(tmp_path: Path) -> None:
    user = _engineer()
    session = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = SimpleNamespace(id=uuid4())
    session.execute.return_value = existing_result
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
                json={"bima_project_id": 627},
            )
    finally:
        _restore_overrides(previous)

    assert response.status_code == 409
    assert service.detail_calls == []
    session.add.assert_not_called()
    assert list(tmp_path.iterdir()) == []
