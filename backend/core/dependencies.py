"""FastAPI dependencies that expose locally configured infrastructure."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.config import settings
from db.session import get_session
from domain.enums import UserRole
from models.document import Document
from models.user import User
from services.storage import LocalStorage
from services.uploads import UploadService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Decode a bearer token and load the active user."""
    cookie_value = request.cookies.get("access_token")
    token = cookie_value.removeprefix("Bearer ").strip() if cookie_value else None
    if token is None and credentials is not None:
        token = credentials.credentials
    if settings.AUTH_MODE == "disabled" and token is None:
        local_user = (
            await session.execute(
                select(User)
                .where(User.email.in_(["admin@localhost", "lead.engineer@localhost"]))
                .order_by(User.email.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if local_user is not None:
            return local_user
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No local development account is available.",
        )
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = UUID(str(payload.get("sub")))
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise unauthorized from exc
    user = (
        await session.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise unauthorized
    return user


async def require_lead(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an active lead engineer."""
    if current_user.role not in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Lead engineer access required."
        )
    return current_user


async def require_user_manager(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require a lead engineer or superuser for account administration."""
    if current_user.role not in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User management access required."
        )
    return current_user


def check_document_read_access(document: Document, current_user: User) -> bool:
    """Return whether a user may read and review a document."""
    if current_user.role in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}:
        return True
    # 1. Direct PIC
    if document.assigned_to_id == current_user.id:
        return True
    # 2. Document uploader / owner
    if document.owner_id == current_user.id:
        return True
    # 3. Assigned to parent project, project creator, or project member
    project = getattr(document, "project", None)
    if project is not None:
        if project.assigned_to_id == current_user.id:
            return True
        if getattr(project, "created_by_id", None) == current_user.id:
            return True
        members = getattr(project, "members", None)
        if members:
            member_ids = {m.id if hasattr(m, "id") else m for m in members}
            if current_user.id in member_ids:
                return True
    return False


def accessible_document_query(document_id: UUID, current_user: User):
    """Build the eager-loaded document query used by document read endpoints."""
    query = select(Document).where(Document.id == document_id).options(
        joinedload(Document.owner),
        joinedload(Document.assigned_to),
        joinedload(Document.project),
    )
    return query


async def get_accessible_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Document:
    """Load a document only when the current user is allowed to access it."""
    document = (
        await session.execute(accessible_document_query(document_id, current_user))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if not check_document_read_access(document, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document.",
        )
    return document


@lru_cache
def get_storage() -> LocalStorage:
    """Return the process-local development storage adapter."""

    return LocalStorage(settings.STORAGE_ROOT)


def get_upload_service() -> UploadService:
    """Return the upload service bound to the configured local storage."""

    return UploadService(get_storage(), settings)
