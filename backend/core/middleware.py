"""ASGI middleware for end-to-end request correlation IDs."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.exceptions import internal_server_error_handler
from core.logging import correlation_id_context, request_path_context


def _correlation_id_from_scope(scope: Scope) -> str:
    """Return a safe caller-provided ID or generate a UUID4."""

    for name, value in scope.get("headers", []):
        if name.lower() != b"x-correlation-id":
            continue
        candidate = cast(str, value.decode("ascii", errors="ignore")).strip()
        if candidate and len(candidate) <= 128 and all(
            character.isalnum() or character in "-_.:" for character in candidate
        ):
            return candidate
        break
    return str(uuid4())


class CorrelationIDMiddleware:
    """Attach a correlation ID to request state, log context, and response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = _correlation_id_from_scope(scope)
        correlation_token = correlation_id_context.set(correlation_id)
        path_token = request_path_context.set(str(scope.get("path", "-")))
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        response_started = False

        async def send_with_correlation_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-correlation-id"
                ]
                headers.append((b"x-correlation-id", correlation_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_with_correlation_id)
            except Exception as exc:
                if response_started:
                    raise
                request = Request(scope, receive=receive)
                response = await internal_server_error_handler(request, exc)
                await response(scope, receive, send_with_correlation_id)
        finally:
            request_path_context.reset(path_token)
            correlation_id_context.reset(correlation_token)
