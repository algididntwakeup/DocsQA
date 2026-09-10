"""Password hashing and JWT access-token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from core.config import settings

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    return _password_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _password_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed bearer token containing the supplied claims."""
    expires = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {**data, "exp": expires}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def access_token_cookie_kwargs() -> dict[str, Any]:
    """Return the production-configurable cookie policy for the access token."""
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.COOKIE_SECURE,
    }
