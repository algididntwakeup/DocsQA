"""Small client for the BIMA credential and SSO identity APIs."""

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from core.config import settings
from domain.enums import UserRole
from services.bima_http import (
    bima_authorization_header,
    body_preview,
    build_bima_client,
)

logger = logging.getLogger(__name__)


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
    # The BIMA user directory nests the identity under ``profile`` (email and
    # full_name live there), while the SSO ``/me`` payload is flat. Unwrap the
    # nested profile but keep the account-level fields as fallback.
    profile = data.get("profile")
    if isinstance(profile, dict):
        merged = {**data, **profile}
        if "id" in data:
            # ``profile.id`` identifies the profile record, not the account.
            merged["id"] = data["id"]
        if not merged.get("email") and data.get("username"):
            merged["email"] = data["username"]
        data = merged
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
    if "@" not in email:
        # The user directory exposes only the account ``username`` for some
        # accounts; PRISM needs a syntactically valid, unique address.
        email = f"{email}@bima.local"
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
        async with build_bima_client() as client:
            response = await client.post(
                f"{base}/api/auth/login", json={"username": username, "password": password}
            )
            if response.status_code != 200:
                logger.warning(
                    "BIMA rejected the credential login (HTTP %s, body=%s)",
                    response.status_code,
                    body_preview(response),
                )
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
                f"{base}/api/auth/me", headers=bima_authorization_header(str(token))
            )
            if profile.status_code != 200:
                logger.warning(
                    "BIMA refused to resolve the authenticated profile (HTTP %s, body=%s)",
                    profile.status_code,
                    body_preview(profile),
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to resolve BIMA profile.",
                )
            normalized = _profile(profile.json())
            normalized["bima_token"] = str(token)
            return normalized
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        logger.warning("Request timeout ke BIMA during credential login: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="BIMA login timed out."
        ) from exc
    except httpx.ConnectError as exc:
        logger.error(
            "Gagal koneksi ke server BIMA (cek VPN/DNS/Firewall) during credential login: %s", exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("BIMA transport failure during credential login: %r", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc


async def verify_sso_token(token: str) -> dict[str, Any]:
    """Exchange a BIMA SSO token for a normalized user profile."""
    try:
        async with build_bima_client() as client:
            response = await client.post(
                f"{settings.BIMA_BASE_URL.rstrip('/')}/api/sso/verify",
                json={"token": token, "client_id": settings.BIMA_CLIENT_ID},
            )
            if response.status_code != 200:
                logger.warning(
                    "BIMA rejected the SSO token exchange (HTTP %s, body=%s)",
                    response.status_code,
                    body_preview(response),
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid BIMA SSO token."
                )
            try:
                payload = response.json()
            except ValueError as exc:
                logger.error(
                    "BIMA returned a non-JSON SSO verification body (content-type=%s, body=%s)",
                    response.headers.get("content-type", "<unknown>"),
                    body_preview(response),
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="BIMA returned an invalid SSO verification response.",
                ) from exc
            normalized = _profile(payload)
            normalized["bima_token"] = token
            return normalized
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        logger.warning("Request timeout ke BIMA during SSO verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="BIMA SSO verification timed out.",
        ) from exc
    except httpx.ConnectError as exc:
        logger.error(
            "Gagal koneksi ke server BIMA (cek VPN/DNS/Firewall) during SSO verification: %s", exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("BIMA transport failure during SSO verification: %r", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc













