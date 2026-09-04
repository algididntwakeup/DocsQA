"""Custom engineering dictionary API schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from schemas.base import ApiModel
from schemas.common import PageInfo


class DictionaryTermStatus(StrEnum):
    """Governance state for a proposed dictionary term."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DictionaryTermCreate(ApiModel):
    """Request to propose a term for a project or organization."""

    term: str = Field(min_length=1, max_length=128)
    scope: str = Field(pattern=r"^(organization|project:[0-9a-fA-F-]{36})$")
    rationale: str | None = Field(default=None, max_length=1000)


class DictionaryTermRead(ApiModel):
    """Governed dictionary entry."""

    id: UUID
    term: str
    scope: str
    status: DictionaryTermStatus
    created_at: datetime


class DictionaryTermListResponse(ApiModel):
    """Paginated dictionary collection."""

    terms: list[DictionaryTermRead]
    pagination: PageInfo


class DictionaryTermApprovalRequest(ApiModel):
    """Admin approval or rejection of a proposed term."""

    status: DictionaryTermStatus
    comment: str | None = Field(default=None, max_length=1000)
