"""Persistence model for immutable audit events."""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.document import TimestampMixin

if TYPE_CHECKING:
    from models.document import Document
    from models.issue import Issue


class AuditEvent(TimestampMixin, Base):
    """Append-only audit record capturing human decisions and document lifecycle events."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_document_created", "document_id", "created_at"),
        Index("ix_audit_events_issue_created", "issue_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="audit_events")
    issue: Mapped["Issue | None"] = relationship(back_populates="audit_events")
