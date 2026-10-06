"""Persistence model for project-level document grouping."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.document import Document
    from models.user import User

project_members = Base.metadata.tables.get("project_members") or Table(
    "project_members",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_project_members_user_id", "user_id"),
)


class Project(Base):
    """Project hierarchy node that groups related documents."""

    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_created_by_id", "created_by_id"),)
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
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    plant_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_by: Mapped["User"] = relationship(
        back_populates="projects", foreign_keys=[created_by_id]
    )
    assigned_to: Mapped["User | None"] = relationship(
        back_populates="assigned_projects", foreign_keys=[assigned_to_id]
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
    members: Mapped[list["User"]] = relationship(
        secondary=project_members,
        back_populates="member_projects",
    )
