"""Project request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from schemas.base import ApiModel


class ProjectCreate(ApiModel):
    """Payload for creating a project."""

    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None
    plant_area: str | None = Field(default=None, max_length=100)


class ProjectRead(ApiModel):
    """Project representation returned by the API."""

    id: UUID
    name: str
    code: str | None = None
    description: str | None = None
    plant_area: str | None = None
    created_by_id: UUID
    created_at: datetime
