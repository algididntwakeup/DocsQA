"""Small client for the BIMA credential and SSO identity APIs."""

from typing import Any

import httpx
from fastapi import HTTPException, status

from core.config import settings
from domain.enums import UserRole


def _roles(payload: dict[str, Any]) -> list[str]:
    roles = payload.get("roles", payload.get("role", []))
    if isinstance(roles, str):
        return [roles]
    return [str(role) for role in roles or []]


def _profile(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, dict) and data.get("valid") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA identity.")
    if isinstance(data, dict):
        data = data.get("user", data)
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA profile.")
    roles = _roles(data)
    position = str(data.get("position") or "")
    if data.get("is_admin") is True or "super-administrator" in roles:
        role = UserRole.SUPERUSER
    elif any(value in roles for value in ("lead-engineer", "manager", "project-manager")) or "Lead" in position:
        role = UserRole.LEAD_ENGINEER
    else:
        role = UserRole.ENGINEER
    bima_id = data.get("bima_id", data.get("id"))
    email = str(data.get("email") or data.get("username") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="BIMA profile has no email.")
    return {
        "bima_id": int(bima_id) if bima_id is not None else None,
        "email": email,
        "full_name": str(data.get("full_name") or data.get("name") or data.get("username") or "BIMA User"),
        "role": role,
        "department": data.get("department"),
        "position": data.get("position"),
    }


async def login_with_bima_credentials(username: str, password: str) -> dict[str, Any]:
    """Authenticate at BIMA, then resolve the complete profile from /me."""
    base = settings.BIMA_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=settings.BIMA_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{base}/api/auth/login", json={"username": username, "password": password})
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA credentials.")
            body = response.json()
            token_data = body.get("data", body)
            token = token_data.get("token", token_data.get("access_token")) if isinstance(token_data, dict) else None
            if not token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA response.")
            profile = await client.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            if profile.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to resolve BIMA profile.")
            return _profile(profile.json())
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable.") from exc


async def verify_sso_token(token: str) -> dict[str, Any]:
    """Exchange a BIMA SSO token for a normalized user profile."""
    try:
        async with httpx.AsyncClient(timeout=settings.BIMA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.BIMA_BASE_URL.rstrip('/')}/api/sso/verify",
                json={"token": token, "client_id": settings.BIMA_CLIENT_ID},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA SSO token.")
            return _profile(response.json())
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable.") from exc
