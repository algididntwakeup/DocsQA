"""Application-wide handlers for unexpected server exceptions."""

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log an uncaught error and return a stable, non-sensitive response."""

    correlation_id = str(getattr(request.state, "correlation_id", "-"))
    logger.error(
        "Unhandled server exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    response_body: dict[str, Any] = {
        "success": False,
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "Terjadi kesalahan internal pada server",
        "correlation_id": correlation_id,
    }
    return JSONResponse(
        status_code=500,
        content=response_body,
        headers={"X-Correlation-ID": correlation_id},
    )
