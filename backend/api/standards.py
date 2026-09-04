"""Contract-first standards registry endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from core.errors import feature_not_ready
from schemas.common import ProblemDetail
from schemas.standards import (
    StandardPatternCreate,
    StandardPatternListResponse,
    StandardPatternRead,
)

router = APIRouter(prefix="/standards-registry", tags=["standards"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.post("", response_model=StandardPatternRead, status_code=201, responses=NOT_READY)
async def create_standard_pattern(payload: StandardPatternCreate) -> StandardPatternRead:
    """Register an organization-scoped standards-code pattern."""

    feature_not_ready("Standards registry creation")


@router.get("", response_model=StandardPatternListResponse, responses=NOT_READY)
async def list_standard_patterns(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StandardPatternListResponse:
    """List configured standards-code patterns."""

    feature_not_ready("Standards registry listing")
