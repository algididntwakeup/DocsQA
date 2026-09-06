"""Custom engineering dictionary endpoints with governance approval workflow."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.dictionary import DictionaryTerm
from schemas.common import PageInfo, ProblemDetail
from schemas.dictionary import (
    DictionaryTermApprovalRequest,
    DictionaryTermCreate,
    DictionaryTermListResponse,
    DictionaryTermRead,
    DictionaryTermStatus,
)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])

CONFLICT_OR_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "model": ProblemDetail,
        "description": "Term already exists for the given scope",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ProblemDetail,
        "description": "Dictionary term not found",
    },
}


@router.post(
    "/terms",
    response_model=DictionaryTermRead,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_OR_NOT_FOUND,
)
async def create_dictionary_term(
    payload: DictionaryTermCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DictionaryTermRead:
    """Propose a project- or organization-scoped dictionary term."""
    clean_term = payload.term.strip()

    # Check for duplicate in the same scope
    existing = await session.execute(
        select(DictionaryTerm).where(
            DictionaryTerm.scope == payload.scope,
            DictionaryTerm.term.ilike(clean_term),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Term '{clean_term}' already exists in scope '{payload.scope}'.",
        )

    term_obj = DictionaryTerm(
        term=clean_term,
        scope=payload.scope,
        status=DictionaryTermStatus.PROPOSED.value,
        rationale=payload.rationale,
    )
    session.add(term_obj)
    await session.commit()
    await session.refresh(term_obj)

    return DictionaryTermRead(
        id=term_obj.id,
        term=term_obj.term,
        scope=term_obj.scope,
        status=DictionaryTermStatus(term_obj.status),
        created_at=term_obj.created_at,
    )


@router.get(
    "/terms",
    response_model=DictionaryTermListResponse,
)
async def list_dictionary_terms(
    session: Annotated[AsyncSession, Depends(get_session)],
    scope: str | None = None,
    term_status: Annotated[DictionaryTermStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DictionaryTermListResponse:
    """List governed dictionary terms with optional scope and status filtering."""
    base_query = select(DictionaryTerm)
    count_query = select(func.count(DictionaryTerm.id))

    if scope:
        base_query = base_query.where(DictionaryTerm.scope == scope)
        count_query = count_query.where(DictionaryTerm.scope == scope)

    if term_status:
        base_query = base_query.where(DictionaryTerm.status == term_status.value)
        count_query = count_query.where(DictionaryTerm.status == term_status.value)

    total_count = (await session.execute(count_query)).scalar_one() or 0

    records = (
        (
            await session.execute(
                base_query.order_by(DictionaryTerm.term.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return DictionaryTermListResponse(
        terms=[
            DictionaryTermRead(
                id=t.id,
                term=t.term,
                scope=t.scope,
                status=DictionaryTermStatus(t.status),
                created_at=t.created_at,
            )
            for t in records
        ],
        pagination=PageInfo(
            page=page,
            page_size=page_size,
            total=total_count,
        ),
    )


@router.patch(
    "/terms/{term_id}/approve",
    response_model=DictionaryTermRead,
    responses=CONFLICT_OR_NOT_FOUND,
)
async def approve_dictionary_term(
    term_id: UUID,
    payload: DictionaryTermApprovalRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DictionaryTermRead:
    """Approve or reject a proposed dictionary term."""
    term_obj = (
        await session.execute(select(DictionaryTerm).where(DictionaryTerm.id == term_id))
    ).scalar_one_or_none()

    if term_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dictionary term '{term_id}' not found.",
        )

    term_obj.status = payload.status.value
    if payload.status == DictionaryTermStatus.APPROVED:
        term_obj.approved_at = datetime.now(UTC)
        term_obj.approved_by = "admin@local"
    else:
        term_obj.approved_at = None
        term_obj.approved_by = None

    if payload.comment:
        existing_rationale = term_obj.rationale or ""
        term_obj.rationale = f"{existing_rationale}\nReview comment: {payload.comment}".strip()

    await session.commit()
    await session.refresh(term_obj)

    return DictionaryTermRead(
        id=term_obj.id,
        term=term_obj.term,
        scope=term_obj.scope,
        status=DictionaryTermStatus(term_obj.status),
        created_at=term_obj.created_at,
    )
