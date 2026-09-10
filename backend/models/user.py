"""Persistence model for application users."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from domain.enums import UserRole

if TYPE_CHECKING:
    from models.document import Document
    from models.project import Project


class User(Base):
    """User account used to own projects and participate in review workflow."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.ENGINEER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    projects: Mapped[list["Project"]] = relationship(
        back_populates="created_by", foreign_keys="Project.created_by_id"
    )
    assigned_projects: Mapped[list["Project"]] = relationship(
        back_populates="assigned_to", foreign_keys="Project.assigned_to_id"
    )
    owned_documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", foreign_keys="Document.owner_id"
    )
    verified_documents: Mapped[list["Document"]] = relationship(
        back_populates="verified_by", foreign_keys="Document.verified_by_id"
    )
