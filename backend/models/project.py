"""Persistence model for project-level document grouping."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.document import TimestampMixin

if TYPE_CHECKING:
    from models.document import Document
    from models.user import User


class Project(TimestampMixin, Base):
    """Project hierarchy node that groups related documents."""

    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_owner_id", "owner_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    header_config: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    bima_project_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, index=True, nullable=True
    )
    project_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    plant_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(
        back_populates="owned_projects", foreign_keys=[owner_id]
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
