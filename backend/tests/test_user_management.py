"""Tests for lead/superuser account administration."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.auth import (
    create_user,
    list_users,
    reset_user_password,
    update_user_status,
    update_user_superuser,
)
from api.projects import get_portfolio_stats
from core.dependencies import require_superuser, require_user_manager
from core.security import verify_password
from domain.enums import UserRole
from models.user import User
from schemas.user import (
    ManagedUserCreate,
    UserPasswordReset,
    UserStatusUpdate,
    UserSuperuserUpdate,
)


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value.lower()}@test.local",
        hashed_password="unused",
        full_name=role.value,
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def _result(value: Any) -> Any:
    return type(
        "Result",
        (),
        {
            "scalar_one_or_none": lambda self: value,
            "scalars": lambda self: type("Scalars", (), {"all": lambda self: value})(),
        },
    )()


@pytest.mark.anyio
async def test_engineer_is_rejected_from_user_management() -> None:
    with pytest.raises(HTTPException) as error:
        await require_user_manager(_user(UserRole.ENGINEER))
    assert error.value.status_code == 403


@pytest.mark.anyio
async def test_lead_and_superuser_are_allowed() -> None:
    assert await require_user_manager(_user(UserRole.LEAD_ENGINEER))
    assert await require_user_manager(_user(UserRole.SUPERUSER))


@pytest.mark.anyio
async def test_list_users_includes_owned_document_count() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    session = AsyncMock()
    count_result = type("Result", (), {"all": lambda self: [(lead, 4), (engineer, 0)]})()
    session.execute.return_value = count_result
    result = await list_users(session, lead)

    assert [item.email for item in result] == [lead.email, engineer.email]
    assert result[0].total_documents_owned == 4
    assert result[1].total_documents_owned == 0

@pytest.mark.anyio
async def test_create_user_hashes_temporary_password() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    session = AsyncMock()
    session.execute.return_value = _result(None)
    session.scalar.return_value = 0
    session.add = Mock()

    async def refresh(user: Any, *args: Any) -> None:
        user.id = user.id or uuid4()
        user.is_active = True
        user.created_at = datetime.now(UTC)

    session.refresh.side_effect = refresh
    payload = ManagedUserCreate(
        email="new.engineer@test.local",
        full_name="New Engineer",
        role=UserRole.ENGINEER,
        temporary_password="temporary-secret",
    )

    result = await create_user(payload, session, lead)
    created = session.add.call_args.args[0]

    assert result.email == payload.email
    assert created.hashed_password != payload.temporary_password
    assert verify_password(payload.temporary_password, created.hashed_password)
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_status_toggle_and_password_reset() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    target = _user(UserRole.ENGINEER)
    session = AsyncMock()
    session.execute.return_value = _result(target)
    session.scalar.return_value = 0

    status_result = await update_user_status(
        target.id, UserStatusUpdate(is_active=False), session, lead
    )
    assert status_result.is_active is False

    old_hash = target.hashed_password
    reset_result = await reset_user_password(
        target.id, UserPasswordReset(temporary_password="new-temporary-secret"), session, lead
    )
    assert reset_result.email == target.email
    assert target.hashed_password != old_hash
    assert target.hashed_password is not None
    assert verify_password("new-temporary-secret", target.hashed_password)
    assert session.commit.await_count == 2


@pytest.mark.anyio
async def test_flagged_account_is_allowed_into_user_management() -> None:
    """A locally flagged account administers users without a lead-level role.

    Regression guard: the dashboard admitted the caller on ``is_superuser`` but
    the endpoint refused them, which rendered every dashboard counter as 0.
    """

    flagged = _user(UserRole.ENGINEER)
    flagged.is_superuser = True

    assert await require_user_manager(flagged) is flagged


@pytest.mark.anyio
async def test_require_superuser_rejects_lead_and_accepts_flagged() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    with pytest.raises(HTTPException) as error:
        await require_superuser(lead)
    assert error.value.status_code == 403
    assert error.value.detail == "Superuser access required."

    flagged = _user(UserRole.ENGINEER)
    flagged.is_superuser = True
    assert await require_superuser(flagged) is flagged


@pytest.mark.anyio
async def test_cannot_revoke_own_superuser() -> None:
    flagged = _user(UserRole.ENGINEER)
    flagged.is_superuser = True
    session = AsyncMock()
    session.execute.return_value = _result(flagged)

    with pytest.raises(HTTPException) as error:
        await update_user_superuser(
            flagged.id, UserSuperuserUpdate(is_superuser=False), session, flagged
        )

    assert error.value.status_code == 400
    assert "your own superuser" in str(error.value.detail)
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_cannot_revoke_last_superuser() -> None:
    actor = _user(UserRole.ENGINEER)
    actor.is_superuser = True
    target = _user(UserRole.ENGINEER)
    target.is_superuser = True
    session = AsyncMock()
    session.execute.return_value = _result(target)
    # No other flagged account remains.
    session.scalar.return_value = 0

    with pytest.raises(HTTPException) as error:
        await update_user_superuser(
            target.id, UserSuperuserUpdate(is_superuser=False), session, actor
        )

    assert error.value.status_code == 400
    assert "last superuser" in str(error.value.detail)
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_grant_superuser_persists_the_flag() -> None:
    actor = _user(UserRole.ENGINEER)
    actor.is_superuser = True
    target = _user(UserRole.ENGINEER)
    session = AsyncMock()
    session.execute.return_value = _result(target)
    session.scalar.return_value = 0

    result = await update_user_superuser(
        target.id, UserSuperuserUpdate(is_superuser=True), session, actor
    )

    assert target.is_superuser is True
    assert result.is_superuser is True
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_portfolio_stats_maps_distinct_owner_counts() -> None:
    """Owner counts must survive the two outer joins without multiplying."""

    owner_id = uuid4()
    session = AsyncMock()
    session.scalar.side_effect = [3, 0, 4]

    def result(rows: Any) -> Any:
        return type(
            "Result",
            (),
            {"all": lambda self: rows},
        )()

    session.execute.side_effect = [
        result([("COMPLETED", 4)]),
        result([("ANALYZING", 4)]),
        result([(owner_id, "Local Lead Engineer", 2, 2)]),
    ]

    stats = await get_portfolio_stats(session, _user(UserRole.ENGINEER))

    assert stats.total_projects == 3
    assert stats.finished_projects == 0
    assert stats.total_documents == 4
    assert stats.documents_by_status == {"COMPLETED": 4}
    assert stats.documents_by_workflow == {"ANALYZING": 4}
    assert len(stats.projects_by_owner) == 1
    owner = stats.projects_by_owner[0]
    assert owner.owner_id == owner_id
    assert owner.owner_name == "Local Lead Engineer"
    assert owner.project_count == 2
    assert owner.document_count == 2
