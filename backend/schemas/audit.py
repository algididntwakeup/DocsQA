"""Audit event and document disposition schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from domain.enums import ReviewStatus
from schemas.base import ApiModel


class AuditEventRead(ApiModel):
    """Immutable audit event record consumed by review and compliance interfaces."""

    id: UUID
    document_id: UUID
    issue_id: UUID | None = None
    actor_id: str
    actor_role: str
    action: str
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any]
    notes: str | None = None
    created_at: datetime


class AuditEventListResponse(ApiModel):
    """Collection of immutable audit events for a document."""

    events: list[AuditEventRead]
    total: int = Field(ge=0)


class DocumentDispositionRequest(ApiModel):
    """Lead Reviewer final document-level sign-off."""

    disposition: ReviewStatus
    justification: str = Field(min_length=1, max_length=4000)
    actor_id: str = Field(default="reviewer@local", min_length=1, max_length=100)
    actor_role: str = Field(default="LEAD_REVIEWER", min_length=1, max_length=50)
