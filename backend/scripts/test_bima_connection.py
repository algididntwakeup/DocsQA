"""Standalone BIMA connectivity diagnostics.

Run this from the same environment/container that serves the API to see exactly
what the upstream BIMA returns before FastAPI maps it to a gateway error:

    python -m scripts.test_bima_connection --token "<bima_token>"

Every test prints the real upstream status code, response headers, and the first
500 characters of the body, so an HTML login page can be told apart from a JSON
payload or a redirect.
"""

import argparse
import asyncio
import json
import socket
import ssl
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.config import settings  # noqa: E402
from services.bima_http import (  # noqa: E402
    bima_authorization_header,
    bima_timeout,
    build_bima_client,
    clean_bima_token,
    login_redirect_target,
)

BODY_PREVIEW_LIMIT = 500
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_USER_AGENT = "python-httpx"


@dataclass
class ProbeResult:
    """One diagnostic probe and everything the operator needs to judge it."""

    name: str
    status: str
    detail: str = ""
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body_preview: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "OK"


def _preview(response: httpx.Response) -> str:
    try:
        return " ".join(response.text[:BODY_PREVIEW_LIMIT].split())
    except Exception:  # pragma: no cover - defensive
        return "<unreadable body>"


def _headers(response: httpx.Response) -> dict[str, str]:
    interesting = (
        "content-type",
        "location",
        "server",
        "set-cookie",
        "www-authenticate",
        "x-powered-by",
    )
    return {key: value for key, value in response.headers.items() if key.lower() in interesting}


def _record(response: httpx.Response, name: str, detail: str = "") -> ProbeResult:
    login_url = login_redirect_target(response)
    note = detail
    if login_url is not None:
        note = f"{note} | HTML login redirect detected ({login_url})".strip(" |")
    return ProbeResult(
        name=name,
        status="OK",
        detail=note,
        status_code=response.status_code,
        headers=_headers(response),
        body_preview=_preview(response),
    )


def test_dns(host: str) -> ProbeResult:
    """Test 1: resolve the hostname and open a TCP connection to port 443."""

    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        return ProbeResult(
            name="1. DNS lookup & TCP connect",
            status="FAIL",
            detail=f"DNS resolution failed: {type(exc).__name__}: {exc}",
        )

    addresses = sorted({info[4][0] for info in infos})
    try:
        with socket.create_connection((host, 443), timeout=8) as sock:
            peer = sock.getpeername()
    except OSError as exc:
        return ProbeResult(
            name="1. DNS lookup & TCP connect",
            status="FAIL",
            detail=f"DNS resolved to {addresses} but TCP connect failed: {exc}",
        )
    return ProbeResult(
        name="1. DNS lookup & TCP connect",
        status="OK",
        detail=f"{host} -> {addresses} | connected to {peer}",
    )


def test_tls(host: str) -> ProbeResult:
    """Test 5a: inspect the TLS certificate presented by BIMA."""

    try:
        context = ssl.create_default_context()
        with (
            socket.create_connection((host, 443), timeout=8) as sock,
            context.wrap_socket(sock, server_hostname=host) as tls_sock,
        ):
            cert = tls_sock.getpeercert()
            version = tls_sock.version()
    except ssl.SSLCertVerificationError as exc:
        return ProbeResult(
            name="5. TLS certificate",
            status="FAIL",
            detail=(
                f"Certificate verification failed: {exc}. "
                "Set BIMA_SSL_VERIFY=false only for dev/internal CA environments."
            ),
        )
    except OSError as exc:
        return ProbeResult(
            name="5. TLS certificate", status="FAIL", detail=f"TLS handshake failed: {exc}"
        )

    if not isinstance(cert, dict):
        return ProbeResult(
            name="5. TLS certificate",
            status="WARN",
            detail=f"TLS {version} established but no certificate details were returned.",
        )
    issuer_parts: list[str] = []
    for rdn in cert.get("issuer", ()):
        for entry in rdn:
            if isinstance(entry, tuple) and len(entry) == 2:
                issuer_parts.append(f"{entry[0]}={entry[1]}")
    issuer = next(
        (part.split("=", 1)[1] for part in issuer_parts if part.startswith("organizationName=")),
        "<unknown>",
    )
    not_after = str(cert.get("notAfter", "<unknown>"))
    return ProbeResult(
        name="5. TLS certificate",
        status="OK",
        detail=(
            f"TLS {version} | issuer={issuer} | notAfter={not_after} | "
            f"subject={cert.get('subject')}"
        ),
    )


async def test_plain_get(url: str) -> ProbeResult:
    """Test 2: plain GET with the default httpx User-Agent and no credentials."""

    try:
        async with httpx.AsyncClient(
            timeout=bima_timeout(), follow_redirects=False
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        return ProbeResult(
            name="2. Plain GET (no auth)",
            status="FAIL",
            detail=f"{type(exc).__name__}: {exc}",
        )
    return _record(response, "2. Plain GET (no auth)")


async def test_bearer_get(url: str, token: str) -> ProbeResult:
    """Test 3: GET with the real Authorization bearer token using production headers."""

    try:
        async with build_bima_client() as client:
            response = await client.get(url, headers=bima_authorization_header(token))
    except httpx.HTTPError as exc:
        return ProbeResult(
            name="3. Authenticated GET (Bearer)",
            status="FAIL",
            detail=f"{type(exc).__name__}: {exc}",
        )
    return _record(
        response,
        "3. Authenticated GET (Bearer)",
        detail=f"production client config (Accept + User-Agent) | final URL: {response.url}",
    )


async def test_user_agents(url: str) -> ProbeResult:
    """Test 4: compare the default httpx User-Agent against a browser one."""

    results: list[str] = []
    for label, agent in (
        ("default", DEFAULT_USER_AGENT),
        ("browser", BROWSER_USER_AGENT),
    ):
        try:
            async with httpx.AsyncClient(
                timeout=bima_timeout(), follow_redirects=False
            ) as client:
                response = await client.get(url, headers={"User-Agent": agent})
            results.append(
                f"{label}: HTTP {response.status_code} "
                f"content-type={response.headers.get('content-type', '<none>')}"
            )
        except httpx.HTTPError as exc:
            results.append(f"{label}: {type(exc).__name__}: {exc}")

    blocked = "default: HTTP 403" in " ".join(results) or "default: HTTP 406" in " ".join(results)
    return ProbeResult(
        name="4. User-Agent variation",
        status="WARN" if blocked else "OK",
        detail=" | ".join(results)
        + (" | WAF appears to filter the default User-Agent" if blocked else ""),
    )


async def test_accept_header(url: str, token: str) -> ProbeResult:
    """Test 6: show how the Accept header changes BIMA's answer (302 HTML vs 401 JSON)."""

    results: list[str] = []
    for label, headers in (
        ("no Accept", bima_authorization_header(token)),
        (
            "Accept: application/json",
            {**bima_authorization_header(token), "Accept": "application/json"},
        ),
    ):
        try:
            async with httpx.AsyncClient(
                timeout=bima_timeout(), follow_redirects=False
            ) as client:
                response = await client.get(url, headers=headers)
            results.append(
                f"{label}: HTTP {response.status_code} "
                f"content-type={response.headers.get('content-type', '<none>')}"
            )
        except httpx.HTTPError as exc:
            results.append(f"{label}: {type(exc).__name__}: {exc}")

    diverged = len({entry.split(": HTTP ")[1][:3] for entry in results}) > 1
    return ProbeResult(
        name="6. Accept header negotiation",
        status="WARN" if diverged else "OK",
        detail=" | ".join(results)
        + (
            " | BIMA answers an HTML redirect without Accept: application/json"
            if diverged
            else ""
        ),
    )


async def test_redirect_follow(url: str, token: str) -> ProbeResult:
    """Test 7: follow redirects and report the final landing page."""

    try:
        async with httpx.AsyncClient(
            timeout=bima_timeout(), follow_redirects=True
        ) as client:
            response = await client.get(url, headers=bima_authorization_header(token))
    except httpx.HTTPError as exc:
        return ProbeResult(
            name="7. Redirect following",
            status="FAIL",
            detail=f"{type(exc).__name__}: {exc}",
        )
    hops = " -> ".join(
        f"{hop.status_code} {hop.headers.get('location', '')}" for hop in response.history
    )
    return _record(
        response,
        "7. Redirect following",
        detail=f"final URL: {response.url} | hops: {hops or '<none>'}",
    )


async def test_ssl_bypass(url: str, token: str) -> ProbeResult:
    """Test 5b: retry with verification disabled to detect an internal CA requirement."""

    try:
        async with httpx.AsyncClient(
            timeout=bima_timeout(), follow_redirects=False, verify=False
        ) as client:
            response = await client.get(url, headers=bima_authorization_header(token))
    except httpx.HTTPError as exc:
        return ProbeResult(
            name="5b. TLS bypass (verify=False)",
            status="FAIL",
            detail=f"{type(exc).__name__}: {exc}",
        )
    return _record(
        response,
        "5b. TLS bypass (verify=False)",
        detail="verification disabled; only useful when the default TLS test failed",
    )


def _print_result(result: ProbeResult, *, show_body: bool = True) -> None:
    marker = "OK  " if result.ok else ("WARN" if result.status == "WARN" else "FAIL")
    print(f"[{marker}] {result.name}")
    if result.detail:
        print(f"       {result.detail}")
    if result.status_code is not None:
        print(f"       HTTP {result.status_code}")
    if result.headers:
        print(f"       headers: {json.dumps(result.headers, indent=None)}")
    if show_body and result.body_preview:
        print(f"       body[:{BODY_PREVIEW_LIMIT}]: {result.body_preview}")


async def run(args: argparse.Namespace) -> int:
    """Execute every diagnostic and return a process exit code."""

    base_url = (args.base_url or settings.BIMA_BASE_URL).rstrip("/")
    host = httpx.URL(base_url).host
    url = f"{base_url}{args.path}"

    print("=" * 78)
    print("BIMA connectivity diagnostics")
    print(f"base_url       : {base_url}")
    print(f"target         : {url}")
    print(f"token supplied : {'yes' if args.token else 'no'}")
    print(f"ssl verify     : {settings.BIMA_SSL_VERIFY}")
    print(f"user agent     : {settings.BIMA_USER_AGENT}")
    print("=" * 78)

    results: list[ProbeResult] = [test_dns(host), test_tls(host)]

    async_probes: list[tuple[str, Any]] = [
        ("2", test_plain_get(url)),
        ("4", test_user_agents(url)),
    ]
    if args.token:
        token = clean_bima_token(args.token)
        async_probes.extend(
            [
                ("3", test_bearer_get(url, token)),
                ("6", test_accept_header(url, token)),
                ("7", test_redirect_follow(url, token)),
                ("5b", test_ssl_bypass(url, token)),
            ]
        )

    for _key, coro in async_probes:
        results.append(await coro)

    print()
    for result in results:
        _print_result(result)
        print()

    authenticated = next(
        (item for item in results if item.name.startswith("3. Authenticated GET")), None
    )
    if args.token and authenticated is not None and authenticated.status_code == 200:
        try:
            payload = json.loads(authenticated.body_preview)
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("projects", [])
            else:
                rows = []
            print(f"Upstream returned {len(rows)} project row(s) on the first page.")
            for row in rows[:5]:
                if isinstance(row, dict):
                    print(
                        "  - id={id} number={number} name={name}".format(
                            id=row.get("id", row.get("bima_project_id")),
                            number=row.get("number", row.get("project_number")),
                            name=row.get("name", row.get("project_name")),
                        )
                    )
            print()

    failures = [item for item in results if item.status == "FAIL"]
    warnings = [item for item in results if item.status == "WARN"]
    print("=" * 78)
    print(f"Summary: {len(results) - len(failures) - len(warnings)} ok, "
          f"{len(warnings)} warn, {len(failures)} failed")
    if failures:
        print("First failure:", failures[0].name, "-", failures[0].detail)
    print("=" * 78)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="BIMA bearer token used for authenticated probes.")
    parser.add_argument("--base-url", help="Override BIMA_BASE_URL (default: from settings).")
    parser.add_argument("--path", default="/api/projects", help="API path to probe.")
    args = parser.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
