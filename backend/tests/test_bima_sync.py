"""Focused coverage for the BIMA master-data adapter and workspace sync."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api import projects as projects_api
from api.projects import list_projects, sync_bima_projects
from domain.enums import UserRole
from models.project import Project
from models.user import User
from services import bima_client
from services.bima_adapter import BimaMasterDataAdapter, sync_user_bima_projects


def _lead() -> User:
    return User(
        id=uuid4(),
        email="lead@prism.test",
        hashed_password="unused",
        full_name="Lead Engineer",
        role=UserRole.LEAD_ENGINEER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def _engineer() -> User:
    return User(
        id=uuid4(),
        email="engineer@prism.test",
        hashed_password="unused",
        full_name="Engineering User",
        role=UserRole.ENGINEER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


_DEFAULT_MEMBER_IDS: tuple[int, ...] = (42,)


def _project_payload(
    member_ids: list[int] | tuple[int, ...] | None = _DEFAULT_MEMBER_IDS,
    pic_id: int | None = 43,
) -> dict[str, Any]:
    """Build a BIMA project payload; `member_ids=None` omits the membership field."""
    payload: dict[str, Any] = {"id": 7, "name": "Plant 7", "code": "P-7"}
    if member_ids is not None:
        payload["member_ids"] = list(member_ids)
    if pic_id is not None:
        payload["pic_id"] = pic_id
    return payload


def _user_payload(user_id: int, email: str | None = None) -> dict[str, Any]:
    return {
        "id": user_id,
        "email": email or f"user{user_id}@reksim.local",
        "name": f"User {user_id}",
    }


def test_adapter_merges_members_and_pic() -> None:
    master = BimaMasterDataAdapter().adapt(
        [_project_payload()],
        [_user_payload(42), _user_payload(43)],
    )
    assert [record.bima_project_id for record in master.projects] == [7]
    assert master.projects[0].member_bima_ids == (42, 43)
    assert [record.bima_id for record in master.users] == [42, 43]


def test_adapter_ignores_unreferenced_directory_users() -> None:
    master = BimaMasterDataAdapter().adapt(
        [_project_payload(member_ids=[], pic_id=None)],
        [_user_payload(42), _user_payload(99)],
    )
    assert master.projects[0].member_bima_ids == ()
    assert master.users == ()


@pytest.mark.parametrize(
    ("projects", "users"),
    [
        ([_project_payload(member_ids=None)], [_user_payload(42), _user_payload(43)]),
        ([_project_payload(member_ids=[42, 99])], [_user_payload(42), _user_payload(43)]),
        ([_project_payload()], [_user_payload(42), _user_payload(42)]),
        ([_project_payload()], [{"id": "42", "email": "user42@test.local", "name": "User"}]),
        ([_project_payload()], [{"id": 42, "email": "", "name": "User"}]),
        ([_project_payload()], [_user_payload(42)]),
    ],
)
def test_adapter_rejects_invalid_payloads(projects: list[Any], users: list[Any]) -> None:
    with pytest.raises(HTTPException) as error:
        BimaMasterDataAdapter().adapt(projects, users)
    assert error.value.status_code == 502


@pytest.mark.anyio
async def test_fetch_bima_users_requires_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 401

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {}

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _url: str, headers: dict[str, str]) -> Response:
            assert headers == {"Authorization": "Bearer bima-token"}
            return Response()

    monkeypatch.setattr("services.bima_client.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(HTTPException) as error:
        await bima_client.fetch_bima_users("bima-token")
    assert error.value.status_code == 401


@pytest.mark.anyio
async def test_fetch_bima_users_rejects_malformed_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"success": True, "data": {"total": 3}}

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _url: str, headers: dict[str, str]) -> Response:
            return Response()

    monkeypatch.setattr("services.bima_client.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(HTTPException) as error:
        await bima_client.fetch_bima_users("bima-token")
    assert error.value.status_code == 502


def _session_with_project(project: Project | None) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = type(
        "Result", (), {"scalar_one_or_none": lambda _self: project}
    )()
    return session


def _patch_sources(
    monkeypatch: pytest.MonkeyPatch,
    projects: list[dict[str, Any]],
    users: list[dict[str, Any]],
) -> dict[int, User]:
    created_users = {
        record["id"]: User(
            id=uuid4(),
            email=record["email"],
            full_name=record["name"],
            role=UserRole.ENGINEER,
            is_active=True,
            bima_id=record["id"],
            created_at=datetime.now(UTC),
        )
        for record in users
    }

    async def fake_fetch_projects(_token: str) -> list[dict[str, Any]]:
        return projects

    async def fake_fetch_users(_token: str) -> list[dict[str, Any]]:
        return users

    async def fake_upsert(
        _session: AsyncMock, payload: dict[str, Any], *, commit: bool = True
    ) -> User:
        assert commit is False
        return created_users[int(payload["bima_id"])]

    monkeypatch.setattr(projects_api.bima_client, "fetch_bima_projects", fake_fetch_projects)
    monkeypatch.setattr(projects_api.bima_client, "fetch_bima_users", fake_fetch_users)
    monkeypatch.setattr(projects_api, "upsert_bima_user", fake_upsert)
    return created_users


@pytest.mark.anyio
async def test_sync_creates_project_with_merged_members(monkeypatch: pytest.MonkeyPatch) -> None:
    users = [_user_payload(42), _user_payload(43)]
    created_users = _patch_sources(monkeypatch, [_project_payload()], users)
    session = _session_with_project(None)

    result = await sync_bima_projects(session, _lead(), bima_token="bima-token")

    assert result == {"synced": 1, "created": 1, "updated": 0}
    session.commit.assert_awaited_once()
    added = [call.args[0] for call in session.add.call_args_list]
    projects = [value for value in added if isinstance(value, Project)]
    assert len(projects) == 1
    assert projects[0].bima_project_id == 7
    assert projects[0].code == "P-7"
    assert {member.bima_id for member in projects[0].members} == {42, 43}
    assert created_users[42].bima_id == 42


@pytest.mark.anyio
async def test_sync_updates_existing_project_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    lead = _lead()
    existing = Project(
        id=uuid4(),
        name="Old name",
        code="OLD",
        bima_project_id=7,
        status="ACTIVE",
        created_by_id=lead.id,
        created_at=datetime.now(UTC),
    )
    existing.members = []
    _patch_sources(
        monkeypatch,
        [_project_payload(member_ids=[42], pic_id=None)],
        [_user_payload(42)],
    )
    session = _session_with_project(existing)

    result = await sync_bima_projects(session, lead, bima_token="bima-token")

    assert result == {"synced": 1, "created": 0, "updated": 1}
    assert existing.name == "Plant 7"
    assert existing.code == "P-7"
    assert [member.bima_id for member in existing.members] == [42]
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_sync_rejects_incomplete_payload_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_sources(monkeypatch, [_project_payload(member_ids=None)], [_user_payload(42)])
    session = _session_with_project(None)

    with pytest.raises(HTTPException) as error:
        await sync_bima_projects(session, _lead(), bima_token="bima-token")

    assert error.value.status_code == 502
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_sync_user_bima_projects_provisions_visible_workspace_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engineer = _engineer()
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = type(
        "Result", (), {"scalars": lambda _self: type("Scalars", (), {"all": lambda _self: []})()}
    )()

    async def fetch_projects(token: str) -> list[dict[str, Any]]:
        assert token == "engineer-bima-token"
        return [{"id": 71, "name": "Engineering Department Project", "code": "ENG-71"}]

    monkeypatch.setattr(projects_api.bima_client, "fetch_bima_projects", fetch_projects)

    result = await sync_user_bima_projects(session, engineer, "engineer-bima-token")

    assert result == {"synced": 1, "created": 1, "updated": 0}
    project = next(call.args[0] for call in session.add.call_args_list)
    assert project.name == "Engineering Department Project"
    assert project.code == "ENG-71"
    assert project.status == "ACTIVE"
    assert project.created_by_id == engineer.id
    assert project.bima_project_id == 71
    assert project.members == [engineer]
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_sync_user_bima_projects_matches_existing_folder_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engineer = _engineer()
    existing = Project(
        id=uuid4(),
        name="Engineering Department Project",
        code=None,
        status="ACTIVE",
        created_by_id=uuid4(),
        bima_project_id=None,
    )
    existing.members = []
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = type(
        "Result",
        (),
        {"scalars": lambda _self: type("Scalars", (), {"all": lambda _self: [existing]})()},
    )()

    async def fetch_projects(_token: str) -> list[dict[str, Any]]:
        return [{"id": 71, "name": "Engineering Department Project", "code": "ENG-71"}]

    monkeypatch.setattr(projects_api.bima_client, "fetch_bima_projects", fetch_projects)

    result = await sync_user_bima_projects(session, engineer, "engineer-bima-token")

    assert result == {"synced": 1, "created": 0, "updated": 1}
    assert existing.bima_project_id == 71
    assert existing.code == "ENG-71"
    assert existing.members == [engineer]
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_list_projects_refreshes_engineer_projects_from_bima_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engineer = _engineer()
    sync = AsyncMock(return_value={"synced": 0, "created": 0, "updated": 0})
    monkeypatch.setattr(projects_api, "sync_user_bima_projects", sync)
    project = Project(
        id=uuid4(),
        name="Engineering Department Project",
        code="ENG-71",
        status="ACTIVE",
        created_by_id=engineer.id,
        created_by=engineer,
        documents=[],
        assigned_to=None,
        created_at=datetime.now(UTC),
    )
    results = type(
        "Result",
        (),
        {
            "unique": lambda self: self,
            "scalars": lambda self: type("Scalars", (), {"all": lambda _self: [project]})(),
        },
    )()
    session = AsyncMock()
    session.execute.return_value = results

    result = await list_projects(session, engineer, bima_cookie="engineer-bima-token")

    assert len(result) == 1
    assert result[0].name == "Engineering Department Project"
    assert result[0].code == "ENG-71"
    sync.assert_awaited_once_with(session, engineer, "engineer-bima-token")
