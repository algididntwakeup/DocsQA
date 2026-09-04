"""Organization standards-registry API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from schemas.base import ApiModel
from schemas.common import PageInfo


class StandardPatternCreate(ApiModel):
    """Admin request to register a normalized standards-code pattern."""

    code_family: str = Field(min_length=1, max_length=32)
    code_pattern: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=500)
    organization_scope: str = Field(min_length=1, max_length=128)


class StandardPatternRead(StandardPatternCreate):
    """Persisted standards-registry entry."""

    id: UUID
    created_at: datetime


class StandardPatternListResponse(ApiModel):
    """Paginated standards-registry collection."""

    standards: list[StandardPatternRead]
    pagination: PageInfo
