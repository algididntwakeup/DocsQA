"""Authentication and document ownership policy tests."""

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest

from core.config import settings
from core.dependencies import get_current_user, require_lead
from core.security import create_access_token, hash_password, verify_password
from domain.enums import UserRole
from models.user import User
from fastapi import HTTPException
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from api.auth import logout


def test_passwords_and_tokens_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)

    token = create_access_token({"sub": str(uuid4())}, timedelta(minutes=5))
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert claims["sub"]
    assert claims["exp"]


def test_engineer_scope_query_excludes_other_engineers() -> None:
    """The ownership predicate is present in engineer document queries."""
    from core.dependencies import accessible_document_query

    engineer = User(
        id=uuid4(),
        email="engineer@example.test",
        hashed_password="unused",
        full_name="Engineer",
        role=UserRole.ENGINEER,
    )
    query = accessible_document_query(uuid4(), engineer)
    compiled = str(query.compile(compile_kwargs={"literal_binds": False}))
    assert "documents.owner_id" in compiled


def test_lead_scope_query_does_not_add_owner_filter() -> None:
    from core.dependencies import accessible_document_query

    lead = User(
        id=uuid4(),
        email="lead@example.test",
        hashed_password="unused",
        full_name="Lead",
        role=UserRole.LEAD_ENGINEER,
    )
    query = accessible_document_query(uuid4(), lead)
    compiled = str(query.compile(compile_kwargs={"literal_binds": False}))
    assert "owner_id =" not in compiled


def _request_with_cookie(value: str | None) -> Request:
    headers = [(b"cookie", f"access_token={value}".encode())] if value else []
    return Request({"type": "http", "headers": headers})


@pytest.mark.anyio
async def test_cookie_token_has_priority_over_authorization_header() -> None:
    user = User(
        id=uuid4(), email="cookie@example.test", hashed_password="unused",
        full_name="Cookie User", role=UserRole.ENGINEER, is_active=True,
    )
    session = AsyncMock()
    session.execute.return_value = type("Result", (), {"scalar_one_or_none": lambda self: user})()
    cookie_token = create_access_token({"sub": str(user.id)})
    header_token = create_access_token({"sub": str(uuid4())})

    result = await get_current_user(
        _request_with_cookie(f"Bearer {cookie_token}"),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=header_token),
        session,
    )

    assert result is user


@pytest.mark.anyio
async def test_expired_cookie_is_reported_explicitly() -> None:
    expired = create_access_token({"sub": str(uuid4())}, timedelta(seconds=-1))

    with pytest.raises(HTTPException) as error:
        await get_current_user(_request_with_cookie(f"Bearer {expired}"), None, AsyncMock())

    assert error.value.status_code == 401
    assert error.value.detail == "Token has expired"


@pytest.mark.anyio
async def test_engineer_cannot_pass_lead_guard() -> None:
    engineer = User(
        id=uuid4(), email="engineer@example.test", hashed_password="unused",
        full_name="Engineer", role=UserRole.ENGINEER, is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        await require_lead(engineer)

    assert error.value.status_code == 403


def test_logout_expires_access_cookie() -> None:
    response = Response()

    import asyncio
    asyncio.run(logout(response))

    assert 'access_token="";' in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
