"""Persistence model for project-level document grouping."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.document import Document
    from models.user import User


class Project(Base):
    """Project hierarchy node that groups related documents."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    plant_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
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
