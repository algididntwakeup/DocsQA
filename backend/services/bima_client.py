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
    login_redirect_target,
)

logger = logging.getLogger(__name__)


def _roles(payload: dict[str, Any]) -> list[str]:
    roles = payload.get("roles", payload.get("role", []))
    if isinstance(roles, str):
        return [roles]
    return [str(role) for role in roles or []]


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
    position = str(data.get("position") or "")
    if data.get("is_admin") is True or "super-administrator" in roles:
        role = UserRole.SUPERUSER
    elif (
        any(value in roles for value in ("lead-engineer", "manager", "project-manager"))
        or "Lead" in position
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
    url = f"{settings.BIMA_BASE_URL.rstrip('/')}{path}"
    try:
        async with build_bima_client() as client:
            response = await client.get(url, headers=bima_authorization_header(bima_token))
            if login_redirect_target(response) is not None:
                logger.warning(
                    "BIMA redirected %s to its login page; the stored BIMA token is missing "
                    "or expired.",
                    path,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=unauthorized_detail,
                )
            if response.status_code != 200:
                logger.warning(
                    "BIMA rejected %s (HTTP %s, body=%s)",
                    path,
                    response.status_code,
                    body_preview(response),
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=unauthorized_detail,
                )
            try:
                payload = response.json()
            except ValueError as exc:
                logger.error(
                    "BIMA returned a non-JSON body for %s (content-type=%s, body=%s)",
                    path,
                    response.headers.get("content-type", "<unknown>"),
                    body_preview(response),
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=malformed_detail,
                ) from exc
            return _directory_rows(payload, keys, malformed_detail)
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        logger.warning("Request timeout ke BIMA for %s: %s", path, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="BIMA request timed out."
        ) from exc
    except httpx.ConnectError as exc:
        logger.error(
            "Gagal koneksi ke server BIMA (cek VPN/DNS/Firewall) for %s: %s", path, exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BIMA is unavailable."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("BIMA transport failure for %s: %r", path, exc)
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
