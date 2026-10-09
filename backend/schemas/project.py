"""Project request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from schemas.base import ApiModel
from schemas.report import HeaderTemplateConfig


class ProjectCreate(ApiModel):
    """Payload for creating a project."""

    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None
    bima_project_id: int | None = None
    project_number: str | None = Field(default=None, max_length=100)
    status: str = "ACTIVE"
    plant_area: str | None = Field(default=None, max_length=100)


class ProjectRead(ApiModel):
    """Project representation returned by the API."""

    id: UUID
    name: str
    code: str | None = None
    description: str | None = None
    bima_project_id: int | None = None
    project_number: str | None = None
    client_name: str | None = None
    header_config: HeaderTemplateConfig = Field(default_factory=HeaderTemplateConfig)
    plant_area: str | None = None
    created_by_id: UUID
    created_by_name: str | None = None
    assigned_to_id: UUID | None = None
    assigned_to_name: str | None = None
    total_documents: int = 0
    status: str = "NO_DOCUMENTS"
    finished_at: datetime | None = None
    created_at: datetime

    @field_validator("header_config", mode="before")
    @classmethod
    def default_missing_header_config(cls, value: object) -> object:
        """Support projects created before the header-config migration and simple mocks."""
        return value or {}

    @field_validator("status", mode="before")
    @classmethod
    def default_missing_status(cls, value: str | None) -> str:
        return value or "ACTIVE"


class ProjectAssignment(ApiModel):
    """Payload used by leads to assign a project to an engineer."""

    assigned_to_id: UUID | None = None


class ProjectHeaderConfigUpdate(ApiModel):
    header_config: HeaderTemplateConfig


class BimaProjectItem(ApiModel):
    """Project listed by BIMA with its local import state."""

    id: int
    number: str
    name: str
    client_name: str
    is_imported: bool = False
    prism_project_id: str | None = None


class ImportBimaProjectRequest(ApiModel):
    """Request to import one BIMA project into PRISM."""

    bima_project_id: int = Field(ge=1)


class BimaProjectListResponse(ApiModel):
    """BIMA project directory and import-state envelope."""

    success: bool
    data: list[BimaProjectItem]
