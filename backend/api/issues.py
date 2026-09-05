"""Issue decision, disposition, and bulk review endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.enums import IssueCategory
from models.audit import AuditEvent
from models.issue import Issue
from schemas.common import ProblemDetail
from schemas.issues import (
    BulkDecisionRequest,
    BulkDecisionResponse,
    IssueDecisionRequest,
    IssueDispositionRequest,
    IssueRead,
)

router = APIRouter(prefix="/issues", tags=["issues"])

CONFLICT_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "model": ProblemDetail,
        "description": "Optimistic concurrency conflict",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ProblemDetail,
        "description": "Issue not found",
    },
}


@router.patch(
    "/{issue_id}/decision",
    response_model=IssueRead,
    responses=CONFLICT_RESPONSE,
)
async def decide_issue(
    issue_id: UUID,
    payload: IssueDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IssueRead:
    """Apply an optimistically locked QA decision."""

    issue = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found.",
        )

    if issue.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Conflict: issue version is {issue.version}, but "
                f"expected {payload.expected_version}."
            ),
        )

    previous_state = {
        "decision": issue.decision.value if issue.decision else None,
        "decision_comment": issue.decision_comment,
        "decision_by": issue.decision_by,
        "version": issue.version,
    }

    issue.decision = payload.decision
    issue.decision_comment = payload.comment
    issue.decision_by = payload.actor_id
    issue.version += 1

    new_state = {
        "decision": issue.decision.value,
        "decision_comment": issue.decision_comment,
        "decision_by": issue.decision_by,
        "version": issue.version,
    }

    audit_event = AuditEvent(
        document_id=issue.document_id,
        issue_id=issue.id,
        actor_id=payload.actor_id,
        actor_role=payload.actor_role,
        action="ISSUE_DECISION",
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.comment,
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(issue)

    return IssueRead.model_validate(issue)


@router.patch(
    "/{issue_id}/disposition",
    response_model=IssueRead,
    responses=CONFLICT_RESPONSE,
)
async def dispose_issue(
    issue_id: UUID,
    payload: IssueDispositionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IssueRead:
    """Append an optimistically locked Lead Reviewer disposition."""

    issue = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found.",
        )

    if issue.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Conflict: issue version is {issue.version}, but "
                f"expected {payload.expected_version}."
            ),
        )

    previous_state = {
        "disposition": issue.disposition.value if issue.disposition else None,
        "disposition_justification": issue.disposition_justification,
        "disposition_by": issue.disposition_by,
        "version": issue.version,
    }

    issue.disposition = payload.disposition
    issue.disposition_justification = payload.justification
    issue.disposition_by = payload.actor_id
    issue.version += 1

    new_state = {
        "disposition": issue.disposition.value,
        "disposition_justification": issue.disposition_justification,
        "disposition_by": issue.disposition_by,
        "version": issue.version,
    }

    audit_event = AuditEvent(
        document_id=issue.document_id,
        issue_id=issue.id,
        actor_id=payload.actor_id,
        actor_role=payload.actor_role,
        action="ISSUE_DISPOSITION",
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.justification,
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(issue)

    return IssueRead.model_validate(issue)


@router.post(
    "/bulk-decision",
    response_model=BulkDecisionResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ProblemDetail,
            "description": "Traceability bulk accept prohibited",
        }
    },
)
async def bulk_decide_issues(
    payload: BulkDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BulkDecisionResponse:
    """Apply a decision to multiple issues, strictly prohibiting traceability bulk-accept."""

    if not payload.issue_ids:
        return BulkDecisionResponse(
            updated_count=0,
            decision=payload.decision,
            updated_issue_ids=[],
        )

    rows = (
        (await session.execute(select(Issue).where(Issue.id.in_(payload.issue_ids))))
        .scalars()
        .all()
    )

    # Acceptance Scenario A-10: Traceability bulk accept rejected by API
    traceability_issues = [i for i in rows if i.category == IssueCategory.TRACEABILITY]
    if traceability_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Traceability findings require individual human review; "
                "bulk acceptance is strictly prohibited."
            ),
        )

    updated_ids: list[UUID] = []
    for issue in rows:
        previous_state = {
            "decision": issue.decision.value if issue.decision else None,
            "version": issue.version,
        }
        issue.decision = payload.decision
        issue.decision_comment = payload.comment
        issue.decision_by = payload.actor_id
        issue.version += 1
        new_state = {
            "decision": issue.decision.value,
            "version": issue.version,
        }
        audit_event = AuditEvent(
            document_id=issue.document_id,
            issue_id=issue.id,
            actor_id=payload.actor_id,
            actor_role=payload.actor_role,
            action="ISSUE_DECISION",
            previous_state=previous_state,
            new_state=new_state,
            notes=f"Bulk action: {payload.comment or 'Applied bulk decision'}",
        )
        session.add(audit_event)
        updated_ids.append(issue.id)

    await session.commit()

    return BulkDecisionResponse(
        updated_count=len(updated_ids),
        decision=payload.decision,
        updated_issue_ids=updated_ids,
    )
