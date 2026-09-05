"""Persistence models for documents and versioned pipeline stage runs."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from domain.enums import DocumentStatus, ReviewStatus, StageStatus

if TYPE_CHECKING:
    from models.audit import AuditEvent
    from models.issue import Issue


class TimestampMixin:
    """UTC-aware creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Document(TimestampMixin, Base):
    """Immutable upload identity plus mutable processing/review state."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="size_bytes_non_negative"),
        CheckConstraint(
            "progress_pct >= 0 AND progress_pct <= 100",
            name="progress_pct_range",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 1",
            name="page_count_positive",
        ),
        Index("ix_documents_status_created_at", "status", "created_at"),
        Index(
            "uq_documents_active_sha256",
            "sha256",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'PROCESSING')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    canonical_pdf_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=False),
        default=DocumentStatus.QUEUED,
        nullable=False,
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status", native_enum=False),
        default=ReviewStatus.PENDING,
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    stage_runs: Mapped[list["StageRun"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="StageRun.created_at",
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Issue.created_at",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="AuditEvent.created_at",
    )


class StageRun(TimestampMixin, Base):
    """Appendable attempt record for one pipeline stage execution."""

    __tablename__ = "stage_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "stage_name", "attempt"),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
        CheckConstraint(
            "progress_pct >= 0 AND progress_pct <= 100",
            name="progress_pct_range",
        ),
        Index("ix_stage_runs_document_status", "document_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus, name="stage_status", native_enum=False),
        default=StageStatus.PENDING,
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[Document] = relationship(back_populates="stage_runs")
