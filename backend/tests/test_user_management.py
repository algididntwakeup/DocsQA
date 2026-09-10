"""Tests for lead/superuser account administration."""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.auth import create_user, list_users, reset_user_password, update_user_status
from core.dependencies import require_user_manager
from core.security import verify_password
from domain.enums import UserRole
from models.user import User
from schemas.user import ManagedUserCreate, UserPasswordReset, UserStatusUpdate


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


def _result(value):
    return type("Result", (), {"scalar_one_or_none": lambda self: value, "scalars": lambda self: type("Scalars", (), {"all": lambda self: value})()})()


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
    session.execute.return_value = _result([lead, engineer])
    session.scalar.return_value = 4

    result = await list_users(session, lead)

    assert [item.email for item in result] == [lead.email, engineer.email]
    assert result[0].total_documents_owned == 4
    session.scalar.assert_awaited()


@pytest.mark.anyio
async def test_create_user_hashes_temporary_password() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    session = AsyncMock()
    session.execute.return_value = _result(None)
    session.scalar.return_value = 0
    session.add = Mock()

    async def refresh(user, *args):
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

    status_result = await update_user_status(target.id, UserStatusUpdate(is_active=False), session, lead)
    assert status_result.is_active is False

    old_hash = target.hashed_password
    reset_result = await reset_user_password(
        target.id, UserPasswordReset(temporary_password="new-temporary-secret"), session, lead
    )
    assert reset_result.email == target.email
    assert target.hashed_password != old_hash
    assert verify_password("new-temporary-secret", target.hashed_password)
    assert session.commit.await_count == 2
