"""Persistence model for application users."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func, text
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
    bima_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.ENGINEER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Local PRISM privilege flag. BIMA's flat project API cannot express
    # cross-department oversight, so workspace-wide access is granted here
    # instead of through ``role`` (which mirrors the BIMA role).
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owned_projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", foreign_keys="Project.owner_id"
    )
    owned_documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", foreign_keys="Document.owner_id"
    )
    assigned_documents: Mapped[list["Document"]] = relationship(
        back_populates="assigned_to", foreign_keys="Document.assigned_to_id"
    )
    verified_documents: Mapped[list["Document"]] = relationship(
        back_populates="verified_by", foreign_keys="Document.verified_by_id"
    )
    reviewed_documents: Mapped[list["Document"]] = relationship(
        back_populates="reviewed_by", foreign_keys="Document.reviewed_by_id"
    )
