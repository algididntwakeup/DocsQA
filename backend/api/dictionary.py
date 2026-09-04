"""Contract-first custom engineering dictionary endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query

from core.errors import feature_not_ready
from schemas.common import ProblemDetail
from schemas.dictionary import (
    DictionaryTermApprovalRequest,
    DictionaryTermCreate,
    DictionaryTermListResponse,
    DictionaryTermRead,
)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.post("/terms", response_model=DictionaryTermRead, status_code=201, responses=NOT_READY)
async def create_dictionary_term(payload: DictionaryTermCreate) -> DictionaryTermRead:
    """Propose a project- or organization-scoped dictionary term."""

    feature_not_ready("Dictionary term creation")


@router.get("/terms", response_model=DictionaryTermListResponse, responses=NOT_READY)
async def list_dictionary_terms(
    scope: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DictionaryTermListResponse:
    """List governed dictionary terms with optional scope filtering."""

    feature_not_ready("Dictionary term listing")


@router.patch(
    "/terms/{term_id}/approve",
    response_model=DictionaryTermRead,
    responses=NOT_READY,
)
async def approve_dictionary_term(
    term_id: UUID, payload: DictionaryTermApprovalRequest
) -> DictionaryTermRead:
    """Approve or reject a proposed dictionary term."""

    feature_not_ready("Dictionary governance")
