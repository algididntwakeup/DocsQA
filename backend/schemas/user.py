"""User request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from domain.enums import UserRole
from schemas.base import ApiModel


class UserCreate(ApiModel):
    """Payload for creating a user account."""

    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=150)
    role: UserRole = UserRole.ENGINEER


class UserRead(ApiModel):
    """Public user representation."""

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserManagementRead(UserRead):
    """User representation used by the lead user-management console."""

    total_documents_owned: int = 0


class ManagedUserCreate(ApiModel):
    """Payload for creating an engineer or lead account."""

    email: str = Field(max_length=255)
    full_name: str = Field(min_length=1, max_length=150)
    role: Literal[UserRole.ENGINEER, UserRole.LEAD_ENGINEER] = UserRole.ENGINEER
    temporary_password: str = Field(min_length=8, max_length=255)


class UserStatusUpdate(ApiModel):
    """Explicit account activation state update."""

    is_active: bool


class UserPasswordReset(ApiModel):
    """Password replacement requested by an authorized administrator."""

    temporary_password: str = Field(min_length=8, max_length=255)
