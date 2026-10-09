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


def _normalized(value: str) -> str:
    """Casefold and strip separators so 'IT_ADMIN', 'it-admin' match one token."""

    return value.strip().casefold().replace("_", "-").replace(" ", "-")


# BIMA declares roles either in the ``roles``/``role`` claim, in the
# ``department``/``position`` text, or through ``is_admin``. Tokens are matched
# after separator normalization, and the most privileged match wins first.
_SUPERUSER_TOKENS = {
    "super-administrator",
    "superadmin",
    "it-admin",
    "administrator",
}
_LEAD_TOKENS = {"lead-engineer", "manager", "project-manager", "lead"}
_LEAD_POSITION_TOKENS = {"lead", "lead-engineer", "engineering-manager"}
_HRGA_TOKENS = {
    "hrga",
    "hr-ga",
    "human-resource",
    "human-resources",
    "hrd",
    "hr",
    "general-affair",
    "general-affairs",
    "ga",
}
_HRGA_POSITION_TOKENS = {
    "hrga",
    "hr-ga",
    "hrd",
    "hr",
    "human-resource",
    "general-affair",
    "general-affairs",
}
_FINANCE_TOKENS = {"finance", "financial", "accounting", "accountant", "treasury"}


def _matches(tokens: set[str], *values: str | None) -> bool:
    """Return whether any candidate text contains one of the role tokens.

    Short tokens (``hr``, ``ga``) only match whole words; longer tokens also
    match inside composite labels such as ``hrga-department``.
    """

    for value in values:
        if not value:
            continue
        normalized = _normalized(str(value))
        if normalized in tokens:
            return True
        words = set(normalized.replace("/", "-").split("-"))
        if words & tokens:
            return True
        if any(len(token) > 2 and token in normalized for token in tokens):
            return True
    return False


def _profile(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, dict) and data.get("valid") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA identity."
        )
    if isinstance(data, dict):
        data = data.get("user", data)
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA profile."
        )
    roles = _roles(data)
    department = str(data.get("department") or "")
    position = str(data.get("position") or "")
    declared = str(data.get("role") or "")
    # Most privileged identity first, then domain roles, then lead. Domain
    # (HR/GA, finance) outranks a "manager" position so a "Finance Manager"
    # is never promoted to lead engineer access. Position-only matching for
    # lead stays limited to the "Lead" token, as before.
    if data.get("is_admin") is True or _matches(
        _SUPERUSER_TOKENS, declared, *roles, department, position
    ):
        role = UserRole.SUPERUSER
    elif _matches(_HRGA_TOKENS, declared, *roles, department) or _matches(
        _HRGA_POSITION_TOKENS, position
    ):
        role = UserRole.HRGA
    elif _matches(_FINANCE_TOKENS, declared, *roles, department, position):
        role = UserRole.FINANCE
    elif _matches(_LEAD_TOKENS, declared, *roles) or _matches(
        _LEAD_POSITION_TOKENS, position
    ):
        role = UserRole.LEAD_ENGINEER
    else:
        role = UserRole.ENGINEER
    bima_id = data.get("bima_id", data.get("id"))
    email = str(data.get("email") or data.get("username") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="BIMA profile has no email."
        )
    return {
        "bima_id": int(bima_id) if bima_id is not None else None,
        "email": email,
        "full_name": str(
            data.get("full_name") or data.get("name") or data.get("username") or "BIMA User"
        ),
        "role": role,
        "department": data.get("department"),
        "position": data.get("position"),
    }


async def login_with_bima_credentials(username: str, password: str) -> dict[str, Any]:
    """Authenticate at BIMA, then resolve the complete profile from /me."""
    base = settings.BIMA_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=settings.BIMA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base}/api/auth/login", json={"username": username, "password": password}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA credentials."
                )
            body = response.json()
            token_data = body.get("data", body)
            token = (
                token_data.get("token", token_data.get("access_token"))
                if isinstance(token_data, dict)
                else None
            )
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA response."
                )
            profile = await client.get(
                f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            if profile.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to resolve BIMA profile.",
                )
            normalized = _profile(profile.json())
            normalized["bima_token"] = str(token)
            return normalized
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc


async def verify_sso_token(token: str) -> dict[str, Any]:
    """Exchange a BIMA SSO token for a normalized user profile."""
    try:
        async with httpx.AsyncClient(timeout=settings.BIMA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.BIMA_BASE_URL.rstrip('/')}/api/sso/verify",
                json={"token": token, "client_id": settings.BIMA_CLIENT_ID},
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA SSO token."
                )
            normalized = _profile(response.json())
            normalized["bima_token"] = token
            return normalized
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc


def _directory_rows(
    payload: Any, keys: tuple[str, ...], malformed_detail: str
) -> list[dict[str, Any]]:
    """Unwrap a BIMA directory envelope, rejecting unrecognized shapes."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        for key in keys:
            candidate = data.get(key)
            if isinstance(candidate, list):
                data = candidate
                break
        else:
            data = None
    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=malformed_detail,
        )
    return [item for item in data if isinstance(item, dict)]


async def _fetch_bima_directory(
    bima_token: str,
    path: str,
    keys: tuple[str, ...],
    unauthorized_detail: str,
    malformed_detail: str,
) -> list[dict[str, Any]]:
    """Fetch one BIMA directory endpoint using a user bearer token."""
    try:
        async with httpx.AsyncClient(timeout=settings.BIMA_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{settings.BIMA_BASE_URL.rstrip('/')}{path}",
                headers={"Authorization": f"Bearer {bima_token}"},
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=unauthorized_detail,
                )
            return _directory_rows(response.json(), keys, malformed_detail)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc


async def fetch_bima_projects(bima_token: str) -> list[dict[str, Any]]:
    """Fetch active/reference projects from BIMA using a user bearer token."""
    return await _fetch_bima_directory(
        bima_token,
        "/api/projects",
        ("projects", "items"),
        "BIMA project access is unauthorized.",
        "BIMA project directory response is malformed.",
    )


async def fetch_bima_users(bima_token: str) -> list[dict[str, Any]]:
    """Fetch the BIMA user directory using a user bearer token."""
    return await _fetch_bima_directory(
        bima_token,
        "/api/users",
        ("users", "items"),
        "BIMA project access is unauthorized.",
        "BIMA user directory response is malformed.",
    )
