"""Authentication endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.dependencies import get_current_user, require_lead, require_user_manager
from core.security import (
    access_token_cookie_kwargs,
    create_access_token,
    hash_password,
    verify_password,
)
from db.session import get_session
from domain.enums import UserRole
from models.document import Document
from models.project import Project
from models.user import User
from schemas.user import (
    ChangePasswordRequest,
    ManagedUserCreate,
    UserManagementRead,
    UserPasswordReset,
    UserProfileUpdate,
    UserRead,
    UserStatusUpdate,
)
from services import bima_client

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(validation_alias=AliasChoices("username", "email"))
    password: str


class SsoExchangeRequest(BaseModel):
    token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RegisterEngineerRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=150)


class AssignedProjectDocument(BaseModel):
    id: UUID
    title: str
    workflow_status: str


async def upsert_bima_user(
    session: AsyncSession,
    bima_user_dict: dict[str, Any],
    *,
    commit: bool = True,
) -> User:
    """Provision or synchronize a BIMA identity without creating local passwords."""
    bima_id = bima_user_dict.get("bima_id")
    email = str(bima_user_dict.get("email", "")).strip().lower()
    user: User | None = None
    if bima_id is not None:
        user = (
            await session.execute(select(User).where(User.bima_id == bima_id))
        ).scalar_one_or_none()
    if user is None and email:
        user = (
            await session.execute(select(User).where(func.lower(User.email) == email))
        ).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name=bima_user_dict["full_name"], is_active=True)
        session.add(user)
    user.bima_id = bima_id
    user.email = email
    user.full_name = bima_user_dict["full_name"]
    user.role = bima_user_dict["role"]
    user.department = bima_user_dict.get("department")
    user.position = bima_user_dict.get("position")
    if commit:
        await session.commit()
        await session.refresh(user)
    else:
        await session.flush()
    return user


def _token_response(response: Response, user: User, bima_token: str | None = None) -> TokenResponse:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response.set_cookie(key="access_token", value=f"Bearer {token}", **access_token_cookie_kwargs())
    if bima_token:
        response.set_cookie(
            key="bima_access_token",
            value=bima_token,
            **access_token_cookie_kwargs(),
        )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


class AssignedProject(BaseModel):
    id: UUID
    name: str
    code: str | None = None
    documents: list[AssignedProjectDocument]


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate an active user and issue a JWT."""
    try:
        bima_user = await bima_client.login_with_bima_credentials(
            payload.username, payload.password
        )
        user = await upsert_bima_user(
            session,
            bima_user,
        )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive."
            )
        return _token_response(response, user, bima_user.get("bima_token"))
    except HTTPException as bima_error:
        if bima_error.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    fallback_user = (
        await session.execute(
            select(User).where(func.lower(User.email) == payload.username.strip().lower())
        )
    ).scalar_one_or_none()
    if (
        fallback_user is None
        or not fallback_user.is_active
        or not fallback_user.hashed_password
        or not verify_password(payload.password, fallback_user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    response.delete_cookie(key="bima_access_token")
    return _token_response(response, fallback_user)


@router.post("/sso/exchange", response_model=TokenResponse)
async def exchange_sso(
    payload: SsoExchangeRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    bima_user = await bima_client.verify_sso_token(payload.token)
    user = await upsert_bima_user(session, bima_user)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive."
        )
    return _token_response(response, user, bima_user.get("bima_token"))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the browser session cookie."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="bima_access_token")


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )
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
    rows = (
        await session.execute(
            select(User, func.count(Document.id).label("total_documents_owned"))
            .outerjoin(Document, Document.owner_id == User.id)
            .group_by(User.id)
            .order_by(User.created_at.desc())
        )
    ).all()
    return [
        UserManagementRead(
            **UserRead.model_validate(user).model_dump(),
            total_documents_owned=int(count or 0),
        )
        for user, count in rows
    ]


@router.get("/users/{user_id}/projects", response_model=list[AssignedProject])
async def list_user_assigned_projects(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> list[AssignedProject]:
    """List projects containing documents assigned to the selected user."""
    projects = (
        (
            await session.execute(
                select(Project)
                .join(Document, Document.project_id == Project.id)
                .where(Document.assigned_to_id == user_id)
                .options(joinedload(Project.documents))
                .order_by(Project.created_at.desc())
            )
        )
        .unique()
        .scalars()
        .all()
    )
    return [
        AssignedProject(
            id=project.id,
            name=project.name,
            code=project.code,
            documents=[
                AssignedProjectDocument(
                    id=document.id,
                    title=document.original_filename,
                    workflow_status=document.workflow_status.value,
                )
                for document in project.documents
                if document.assigned_to_id == user_id
            ],
        )
        for project in projects
    ]


@router.post("/users", response_model=UserManagementRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: ManagedUserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_user_manager)],
) -> UserManagementRead:
    """Create an engineer or lead account with a temporary password."""
    if payload.role not in {UserRole.ENGINEER, UserRole.LEAD_ENGINEER}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SUPERUSER cannot be created here.",
        )
    existing = (
        await session.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )
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
    current_user: Annotated[User, Depends(require_user_manager)],
) -> UserManagementRead:
    """Activate or deactivate an account."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user_id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    if user.role == UserRole.LEAD_ENGINEER and user.is_active and not payload.is_active:
        active_leads = await session.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.LEAD_ENGINEER,
                User.is_active.is_(True),
            )
        )
        if int(active_leads or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active lead engineer",
            )
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
