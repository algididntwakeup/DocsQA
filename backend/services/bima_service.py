"""Authenticated HTTP client for BIMA project ingestion."""

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from core.config import settings
from services.bima_http import (
    bima_authorization_header,
    body_preview,
    build_bima_client,
    login_redirect_target,
)

logger = logging.getLogger(__name__)


class BimaService:
    """Fetch project data from BIMA using the current engineer's bearer token."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.BIMA_BASE_URL).rstrip("/")
        self.timeout_seconds = (
            settings.BIMA_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        )
        self.transport = transport

    async def list_projects(self, token: str) -> list[dict[str, Any]]:
        """Return the BIMA project directory, unwrapping the supported response envelopes."""

        payload = await self._get_json("/api/projects", token, resource="project directory")
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(data, dict):
            data = next(
                (data[key] for key in ("projects", "items") if isinstance(data.get(key), list)),
                None,
            )
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA project directory response is malformed.",
            )
        return data

    async def get_project(self, project_id: int, token: str) -> dict[str, Any]:
        """Return one BIMA project, accepting the common project/detail envelopes.

        BIMA's ``/api/projects/{id}`` endpoint answers 404 for some deployments
        even though the project is present in the directory listing. When that
        happens the listing row is used instead so the import flow keeps
        working.
        """

        try:
            payload = await self._get_json(
                f"/api/projects/{project_id}", token, resource="project", missing_is_404=True
            )
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            records = await self.list_projects(token)
            match = next(
                (record for record in records if str(record.get("id")) == str(project_id)),
                None,
            )
            if match is None:
                raise
            return match
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(data, dict):
            for key in ("project", "item"):
                if isinstance(data.get(key), dict):
                    data = data[key]
                    break
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA project detail response is malformed.",
            )
        return data

    async def _get_json(
        self,
        path: str,
        token: str,
        *,
        resource: str,
        missing_is_404: bool = False,
    ) -> Any:
        """Perform a bounded GET and map upstream/network failures to gateway errors."""

        url = f"{self.base_url}{path}"
        try:
            async with build_bima_client(
                transport=self.transport, timeout_seconds=self.timeout_seconds
            ) as client:
                response = await client.get(url, headers=bima_authorization_header(token))
        except httpx.TimeoutException as exc:
            logger.warning(
                "Request timeout ke BIMA for the %s (url=%s, error=%s)",
                resource,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="BIMA request timed out.",
            ) from exc
        except httpx.TooManyRedirects as exc:
            # A redirect loop that ends on /login means BIMA kept bouncing the
            # request to its login page: the upstream credential is not accepted.
            last_path = getattr(getattr(exc.request, "url", None), "path", "")
            if "/login" in last_path:
                logger.warning(
                    "BIMA looped the %s request back to its login page (%s); the stored BIMA "
                    "token is missing or expired.",
                    resource,
                    last_path,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=(
                        "BIMA rejected the supplied access token; the session may have expired. "
                        "Sign in again to refresh the BIMA session."
                    ),
                ) from exc
            logger.error(
                "BIMA redirected the %s request too many times (url=%s, error=%r)",
                resource,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA returned a redirect loop for the request.",
            ) from exc
        except httpx.ConnectError as exc:
            logger.error(
                "Gagal koneksi ke server BIMA (cek VPN/DNS/Firewall) for the %s "
                "(url=%s, error=%s)",
                resource,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA is unreachable.",
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "BIMA transport failure for the %s (url=%s, error=%r)",
                resource,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA is unreachable.",
            ) from exc

        logger.debug(
            "BIMA %s responded with HTTP %s (url=%s, redirects=%s)",
            resource,
            response.status_code,
            response.url,
            [hop.status_code for hop in response.history],
        )

        # BIMA answers an unauthenticated API call with an HTML login redirect when
        # the request does not carry an API-style Accept header. Treat landing on
        # /login as an expired/missing credential instead of a malformed payload.
        login_url = login_redirect_target(response)
        if login_url is not None:
            logger.warning(
                "BIMA redirected the %s request to its login page (%s); the stored BIMA "
                "token is missing or expired.",
                resource,
                login_url,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "BIMA rejected the supplied access token; the session may have expired. "
                    "Sign in again to refresh the BIMA session."
                ),
            )

        if response.status_code in {401, 403}:
            logger.warning(
                "BIMA rejected the %s request with HTTP %s (url=%s, body=%s)",
                resource,
                response.status_code,
                response.url,
                body_preview(response),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="BIMA rejected the supplied access token.",
            )
        if response.status_code == 404 and missing_is_404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project was not found in BIMA.",
            )
        if response.status_code in {408, 504}:
            logger.warning(
                "BIMA did not respond in time for the %s (HTTP %s, url=%s)",
                resource,
                response.status_code,
                response.url,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="BIMA did not respond in time.",
            )
        if response.status_code == 429:
            logger.warning("BIMA is rate limiting the %s request (url=%s)", resource, response.url)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="BIMA is rate limiting project requests.",
            )
        if response.status_code >= 500:
            logger.error(
                "BIMA returned an upstream error for the %s (HTTP %s, url=%s, body=%s)",
                resource,
                response.status_code,
                response.url,
                body_preview(response),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA returned an upstream error for the {resource} (HTTP "
                f"{response.status_code}).",
            )
        if response.status_code >= 400:
            logger.error(
                "BIMA rejected the %s request (HTTP %s, url=%s, body=%s)",
                resource,
                response.status_code,
                response.url,
                body_preview(response),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA rejected the {resource} request (HTTP {response.status_code}).",
            )

        try:
            return response.json()
        except ValueError as exc:
            content_type = response.headers.get("content-type", "<unknown>")
            logger.error(
                "BIMA returned a non-JSON body for the %s (HTTP %s, url=%s, "
                "content-type=%s, body=%s)",
                resource,
                response.status_code,
                response.url,
                content_type,
                body_preview(response),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA returned invalid JSON for the {resource}.",
            ) from exc
