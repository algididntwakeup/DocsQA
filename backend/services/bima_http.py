"""Shared httpx plumbing for every outbound BIMA request.

BIMA is a Laravel application behind nginx. When a request does not look like an
API client it answers with an HTML ``302`` to ``/login`` instead of a JSON
``401``. Every caller therefore has to send a real ``User-Agent`` and
``Accept: application/json``, follow redirects, and surface upstream HTML
instead of trying to parse it as JSON (which used to surface as a bogus 502).
"""

import httpx

from core.config import settings


def bima_json_headers() -> dict[str, str]:
    """Build the headers that make BIMA answer with JSON instead of an HTML redirect."""

    return {
        "Accept": "application/json",
        "User-Agent": settings.BIMA_USER_AGENT,
    }


def clean_bima_token(token: str) -> str:
    """Return the raw credential, dropping any duplicated ``Bearer`` prefix.

    Callers sometimes forward the cookie value verbatim while others pass the
    ``Authorization`` header, so a token can arrive as ``Bearer Bearer <token>``.
    """

    cleaned = token.strip()
    while cleaned.lower().startswith("bearer "):
        cleaned = cleaned[len("bearer ") :].strip()
    return cleaned


def bima_authorization_header(token: str) -> dict[str, str]:
    """Build the single ``Authorization`` header forwarded to BIMA."""

    return {"Authorization": f"Bearer {clean_bima_token(token)}"}


def bima_timeout(total_seconds: float | None = None) -> httpx.Timeout:
    """Build a timeout with a fast connect budget and a slower read budget."""

    total = settings.BIMA_TIMEOUT_SECONDS if total_seconds is None else total_seconds
    return httpx.Timeout(total, connect=settings.BIMA_CONNECT_TIMEOUT_SECONDS)


def build_bima_client(
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float | None = None,
) -> httpx.AsyncClient:
    """Build an ``AsyncClient`` configured for the BIMA upstream."""

    return httpx.AsyncClient(
        timeout=bima_timeout(timeout_seconds),
        follow_redirects=True,
        verify=settings.BIMA_SSL_VERIFY,
        transport=transport,
        headers=bima_json_headers(),
    )


def _location_of(hop: object) -> str:
    """Return the ``Location`` header of a response/hop when it exposes one."""

    headers = getattr(hop, "headers", None)
    if headers is None:
        return ""
    try:
        return str(headers.get("location", "") or "")
    except Exception:  # pragma: no cover - defensive against exotic test doubles
        return ""


def login_redirect_target(response: httpx.Response) -> str | None:
    """Return the BIMA login URL when an HTML login redirect answered the request.

    BIMA sends ``302 -> /login`` (HTML) instead of a JSON ``401`` when a request
    is not recognised as an API call, so landing on ``/login`` means the upstream
    credential was missing or expired rather than that the payload was malformed.
    """

    history = getattr(response, "history", None) or []
    for hop in history:
        location = _location_of(hop)
        if "/login" in location:
            return location
    url = getattr(response, "url", None)
    path = getattr(url, "path", "") if url is not None else ""
    if path.rstrip("/").endswith("/login"):
        return str(url)
    return None


def body_preview(response: httpx.Response, limit: int = 500) -> str:
    """Return a single-line preview of the response body for server-side logs."""

    try:
        text = response.text
    except Exception:  # pragma: no cover - only exotic transports lack a body
        return "<unreadable body>"
    return " ".join(text[:limit].split())
