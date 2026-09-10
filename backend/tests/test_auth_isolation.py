"""Authentication and document ownership policy tests."""

from datetime import timedelta
from uuid import uuid4

import jwt

from core.config import settings
from core.security import create_access_token, hash_password, verify_password
from domain.enums import UserRole
from models.user import User


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
