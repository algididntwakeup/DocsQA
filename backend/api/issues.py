"""Minimal report-curation endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from db.session import get_session
from domain.enums import UserRole
from models.document import Document
from models.issue import Issue
from models.user import User
from schemas.issues import IssueCurationRequest, IssueRead

router = APIRouter(prefix="/issues", tags=["issues"])


@router.patch("/{issue_id}/curation", response_model=IssueRead)
async def curate_issue(
    issue_id: UUID,
    payload: IssueCurationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueRead:
    """Include/exclude a finding from the generated report and attach a note."""
    query = (
        select(Issue)
        .join(Document, Issue.document_id == Document.id)
        .where(Issue.id == issue_id)
    )
    if current_user.role != UserRole.LEAD_ENGINEER:
        query = query.where(Document.owner_id == current_user.id)
    issue = (await session.execute(query)).scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found.")
    issue.included_in_report = payload.included_in_report
    issue.reviewer_note = payload.reviewer_note
    await session.commit()
    await session.refresh(issue)
    return IssueRead.model_validate(issue)
