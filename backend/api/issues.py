"""Contract-first issue decision and disposition endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from core.errors import feature_not_ready
from schemas.common import ProblemDetail
from schemas.issues import IssueDecisionRequest, IssueDispositionRequest, IssueRead

router = APIRouter(prefix="/issues", tags=["issues"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.patch("/{issue_id}/decision", response_model=IssueRead, responses=NOT_READY)
async def decide_issue(issue_id: UUID, payload: IssueDecisionRequest) -> IssueRead:
    """Apply an optimistically locked QA decision."""

    feature_not_ready("Issue decisions")


@router.patch("/{issue_id}/disposition", response_model=IssueRead, responses=NOT_READY)
async def dispose_issue(issue_id: UUID, payload: IssueDispositionRequest) -> IssueRead:
    """Append an optimistically locked Lead Reviewer disposition."""

    feature_not_ready("Issue dispositions")
