"""Authentication endpoints."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, require_lead, require_user_manager
from core.security import access_token_cookie_kwargs, create_access_token, hash_password, verify_password
from db.session import get_session
from domain.enums import UserRole
from models.user import User
from models.document import Document
from schemas.user import (
    ChangePasswordRequest,
    ManagedUserCreate,
    UserManagementRead,
    UserPasswordReset,
    UserRead,
    UserStatusUpdate,
    UserProfileUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RegisterEngineerRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=150)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate an active user and issue a JWT."""
    user = (
        await session.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        **access_token_cookie_kwargs(),
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the browser session cookie."""
    response.delete_cookie(key="access_token")


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/change-password", response_model=UserRead)
async def change_password(
    payload: ChangePasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Change the password for the authenticated account owner."""
    if not current_user.hashed_password or not verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect."
        )
    current_user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    await session.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_profile(
    payload: UserProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Update the authenticated user's profile fields."""
    email = payload.email.strip().lower()
    existing = (
        await session.execute(
            select(User).where(func.lower(User.email) == email, User.id != current_user.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    current_user.full_name = payload.full_name.strip()
    current_user.email = email
    await session.commit()
    await session.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/register-engineer", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_engineer(
    payload: RegisterEngineerRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
) -> UserRead:
    """Allow only lead engineers to create engineer accounts."""
    existing = (
        await session.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ENGINEER,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


async def _managed_user_read(session: AsyncSession, user: User) -> UserManagementRead:
    """Build the management representation with an ownership count."""
    count = await session.scalar(
        select(func.count(Document.id)).where(Document.owner_id == user.id)
    )
    return UserManagementRead(
        **UserRead.model_validate(user).model_dump(),
        total_documents_owned=int(count or 0),
    )


@router.get("/users", response_model=list[UserManagementRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> list[UserManagementRead]:
    """List all accounts for the lead/superuser administration console."""
    users = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return [await _managed_user_read(session, user) for user in users]


@router.post("/users", response_model=UserManagementRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: ManagedUserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> UserManagementRead:
    """Create an engineer or lead account with a temporary password."""
    if payload.role == UserRole.SUPERUSER:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="SUPERUSER cannot be created here.")
    existing = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(payload.temporary_password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return await _managed_user_read(session, user)


@router.patch("/users/{user_id}/status", response_model=UserManagementRead)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> UserManagementRead:
    """Activate or deactivate an account."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = payload.is_active
    await session.commit()
    await session.refresh(user)
    return await _managed_user_read(session, user)


@router.post("/users/{user_id}/reset-password", response_model=UserManagementRead)
async def reset_user_password(
    user_id: UUID,
    payload: UserPasswordReset,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> UserManagementRead:
    """Replace an account password without exposing its hash."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.hashed_password = hash_password(payload.temporary_password)
    await session.commit()
    await session.refresh(user)
    return await _managed_user_read(session, user)
