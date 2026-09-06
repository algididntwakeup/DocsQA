"""Service functions for querying and applying the governed engineering dictionary."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dictionary import DictionaryTerm
from schemas.dictionary import DictionaryTermStatus


async def get_approved_dictionary_terms(
    session: AsyncSession,
    project_id: UUID | None = None,
) -> set[str]:
    """Return a set of approved dictionary terms for the given project and organization scope."""
    scopes = ["organization"]
    if project_id is not None:
        scopes.append(f"project:{project_id}")

    stmt = select(DictionaryTerm.term).where(
        DictionaryTerm.scope.in_(scopes),
        DictionaryTerm.status == DictionaryTermStatus.APPROVED.value,
    )
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}
