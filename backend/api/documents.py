"""Contract-first document lifecycle endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

from core.errors import feature_not_ready
from domain.enums import IssueCategory
from schemas.common import ProblemDetail
from schemas.documents import (
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
    TraceabilitySummaryResponse,
)
from schemas.issues import IssueListResponse

router = APIRouter(prefix="/documents", tags=["documents"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.get("", response_model=DocumentListResponse, responses=NOT_READY)
async def list_documents(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    """List documents visible to the current user."""

    feature_not_ready("Document listing")


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    responses=NOT_READY,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Native-text PDF or DOCX")],
) -> DocumentUploadResponse:
    """Persist a validated document and enqueue canonical extraction."""

    feature_not_ready("Document upload")


@router.get("/{document_id}", response_model=DocumentRead, responses=NOT_READY)
async def get_document(document_id: UUID) -> DocumentRead:
    """Return safe metadata for one document."""

    feature_not_ready("Document detail")


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses=NOT_READY,
)
async def get_document_status(document_id: UUID) -> DocumentStatusResponse:
    """Return processing progress and latest stage states."""

    feature_not_ready("Document status")


@router.get(
    "/{document_id}/issues",
    response_model=IssueListResponse,
    responses=NOT_READY,
)
async def list_document_issues(
    document_id: UUID,
    category: IssueCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssueListResponse:
    """List issues with optional canonical category filtering."""

    feature_not_ready("Document issue listing")


@router.get(
    "/{document_id}/traceability-summary",
    response_model=TraceabilitySummaryResponse,
    responses=NOT_READY,
)
async def get_traceability_summary(document_id: UUID) -> TraceabilitySummaryResponse:
    """Return traceability counts for audit triage."""

    feature_not_ready("Traceability summary")


@router.get(
    "/{document_id}/export",
    response_class=Response,
    responses=NOT_READY,
)
async def export_document(
    document_id: UUID,
    format: Annotated[str, Query(pattern=r"^(pdf|xlsx|csv)$")],
) -> Response:
    """Export the annotated rendition or structured issue log."""

    feature_not_ready("Document export")
