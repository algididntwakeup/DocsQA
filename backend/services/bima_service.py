"""Authenticated HTTP client for BIMA project ingestion."""

from typing import Any

import httpx
from fastapi import HTTPException, status

from core.config import settings


class BimaService:
    """Fetch project data from BIMA using the current engineer's bearer token."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.BIMA_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
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
        """Return one BIMA project, accepting the common project/detail envelopes."""

        payload = await self._get_json(
            f"/api/projects/{project_id}", token, resource="project", missing_is_404=True
        )
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

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self.transport
            ) as client:
                response = await client.get(
                    f"{self.base_url}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="BIMA request timed out.",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="BIMA is unreachable.",
            ) from exc

        if response.status_code in {401, 403}:
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
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="BIMA did not respond in time.",
            )
        if response.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="BIMA is rate limiting project requests.",
            )
        if response.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA returned an upstream error for the {resource} (HTTP "
                f"{response.status_code}).",
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA rejected the {resource} request (HTTP {response.status_code}).",
            )

        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"BIMA returned invalid JSON for the {resource}.",
            ) from exc
