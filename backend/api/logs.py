"""Client-side error ingestion endpoints."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from core.logging import correlation_id_context

router = APIRouter(prefix="/logs", tags=["logs"])
logger = logging.getLogger(__name__)


class ClientErrorPayload(BaseModel):
    """A bounded browser error report suitable for structured logs."""

    message: str = Field(min_length=1, max_length=4_000)
    stack: str | None = Field(default=None, max_length=30_000)
    component_stack: str | None = Field(default=None, max_length=30_000)
    url: str | None = Field(default=None, max_length=2_048)
    user_agent: str | None = Field(default=None, max_length=512)
    correlation_id: str | None = Field(default=None, max_length=128)
    timestamp: datetime | None = None


class ClientErrorAccepted(BaseModel):
    success: bool
    correlation_id: str


@router.post("/client", status_code=202, response_model=ClientErrorAccepted)
async def ingest_client_error(
    payload: ClientErrorPayload,
    request: Request,
) -> ClientErrorAccepted:
    """Record a frontend error without exposing the report back to the user."""

    request_correlation_id = str(
        getattr(request.state, "correlation_id", correlation_id_context.get())
    )
    event: dict[str, Any] = payload.model_dump(mode="json", exclude_none=True)
    logger.error(
        "[CLIENT_ERROR] %s",
        payload.message,
        extra={
            # sendBeacon cannot set request headers; in that case the payload ID
            # keeps the client report tied to the ID shown by the error fallback.
            "correlation_id": payload.correlation_id or request_correlation_id,
            "path": request.url.path,
            "client_error": event,
        },
    )
    return ClientErrorAccepted(success=True, correlation_id=request_correlation_id)
