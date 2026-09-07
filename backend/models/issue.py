"""Persistence model for detected document issues."""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from domain.enums import IssueCategory, Severity
from models.document import TimestampMixin

if TYPE_CHECKING:
    from models.document import Document


class Issue(TimestampMixin, Base):
    """Normalized finding emitted by the linguistic or traceability pipeline."""

    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="confidence_range"),
        Index("ix_issues_document_category", "document_id", "category"),
        Index("ix_issues_document_severity", "document_id", "severity"),
        Index("ix_issues_document_page", "document_id", "page_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[IssueCategory] = mapped_column(
        Enum(IssueCategory, name="issue_category", native_enum=False),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity", native_enum=False),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    included_in_report: Mapped[bool] = mapped_column(default=True, nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="issues")
