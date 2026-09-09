"""Document lifecycle request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from domain.enums import DocumentStatus, PipelineStage, StageStatus
from schemas.base import ApiModel
from schemas.common import PageInfo


class StageRunRead(ApiModel):
    """Latest observable state for one pipeline stage execution."""

    id: UUID
    name: str = Field(
        min_length=1,
        max_length=64,
        validation_alias="stage_name",
        json_schema_extra={"enum": [stage.value for stage in PipelineStage]},
    )
    status: StageStatus
    progress_pct: int = Field(ge=0, le=100)
    attempt: int = Field(ge=1)
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DocumentRead(ApiModel):
    """Safe document metadata returned to clients."""

    id: UUID
    filename: str = Field(validation_alias="original_filename")
    media_type: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: DocumentStatus
    progress_pct: int = Field(ge=0, le=100)
    page_count: int | None = Field(default=None, ge=1)
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(ApiModel):
    """Response after a valid upload is persisted and queued."""

    id: UUID
    filename: str
    status: DocumentStatus
    created_at: datetime
    deduplicated: bool = False

    model_config = {
        "extra": "forbid",
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "ed846165-102f-49f9-9fd0-f25c0d4cfe6e",
                    "filename": "Inspection_Report_Rev-A.pdf",
                    "status": "QUEUED",
                    "created_at": "2026-09-04T04:00:00Z",
                    "deduplicated": False,
                }
            ]
        },
    }


class DocumentStatusResponse(ApiModel):
    """Processing and stage status used for polling."""

    id: UUID
    status: DocumentStatus
    progress_pct: int = Field(ge=0, le=100)
    stages: list[StageRunRead]
    updated_at: datetime


class DocumentListResponse(ApiModel):
    """Paginated document collection."""

    documents: list[DocumentRead]
    pagination: PageInfo


class TraceabilitySummaryResponse(ApiModel):
    """Counts required by the audit-focused dashboard."""

    document_id: UUID
    counts_by_type: dict[str, int]
    counts_by_severity: dict[str, int]
    critical_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)


class ReviewReportPreview(ApiModel):
    """Summary used by the report-first review screen."""

    document_id: UUID
    included_findings: int = Field(ge=0)
    blockers: int = Field(ge=0)
    counts_by_severity: dict[str, int]
    summary_judgement: str
