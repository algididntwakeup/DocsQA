"""DictionaryTerm model for custom engineering dictionary governance."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.document import TimestampMixin
from schemas.dictionary import DictionaryTermStatus


class DictionaryTerm(TimestampMixin, Base):
    """Governed engineering dictionary term."""

    __tablename__ = "dictionary_terms"
    __table_args__ = (
        Index("ix_dictionary_terms_scope_status", "scope", "status"),
        Index("ix_dictionary_terms_scope_term", "scope", "term", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    term: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DictionaryTermStatus.PROPOSED.value, index=True
    )
    rationale: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
