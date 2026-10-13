"""Role-based folder and project-creation rules.

Covers the folder RBAC matrix (engineering prefix ``13`` vs internal prefix
``03``) and the visibility helper that guards the project listing.
"""

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import Select

from api.projects import _visible_projects_query, create_project
from domain.enums import UserRole
from schemas.project import ImportBimaProjectRequest, ProjectCreate
from services.permission_service import (
    ProjectKind,
    can_create_project,
    can_manage_folders,
    folder_permission_message,
    is_privileged,
    project_kind,
)

ENGINEERING_NUMBER = "13726486.01"
INTERNAL_NUMBER = "03-2026-001"


def _user(role: UserRole) -> Any:
    from models.user import User

    return User(
        id=uuid4(),
        email=f"{role.value.lower()}@rbac.test",
        hashed_password="unused",
        full_name=role.value,
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (ENGINEERING_NUMBER, ProjectKind.ENGINEERING),
        ("13", ProjectKind.ENGINEERING),
        (" 13726486.01 ", ProjectKind.ENGINEERING),
        (INTERNAL_NUMBER, ProjectKind.INTERNAL),
        ("03", ProjectKind.INTERNAL),
        ("99001", ProjectKind.UNCLASSIFIED),
        (None, ProjectKind.UNCLASSIFIED),
        ("", ProjectKind.UNCLASSIFIED),
    ],
)
def test_project_kind_classification(number: str | None, expected: str) -> None:
    assert project_kind(number) == expected


@pytest.mark.parametrize(
    ("role", "number", "allowed"),
    [
        # Engineering projects: engineering roles only.
        (UserRole.ENGINEER, ENGINEERING_NUMBER, True),
        (UserRole.LEAD_ENGINEER, ENGINEERING_NUMBER, True),
        (UserRole.SUPERUSER, ENGINEERING_NUMBER, True),
        (UserRole.HRGA, ENGINEERING_NUMBER, False),
        (UserRole.FINANCE, ENGINEERING_NUMBER, False),
        # Internal projects: HR/GA and finance only.
        (UserRole.HRGA, INTERNAL_NUMBER, True),
        (UserRole.FINANCE, INTERNAL_NUMBER, True),
        (UserRole.SUPERUSER, INTERNAL_NUMBER, True),
        (UserRole.ENGINEER, INTERNAL_NUMBER, False),
        (UserRole.LEAD_ENGINEER, INTERNAL_NUMBER, False),
        # Unclassified projects keep the legacy unrestricted behaviour.
        (UserRole.ENGINEER, None, True),
        (UserRole.HRGA, "99001", True),
    ],
)
def test_can_manage_folders_matrix(role: UserRole, number: str | None, allowed: bool) -> None:
    assert can_manage_folders(role, number) is allowed


@pytest.mark.parametrize(
    ("role", "number", "allowed"),
    [
        (UserRole.ENGINEER, ENGINEERING_NUMBER, True),
        (UserRole.HRGA, INTERNAL_NUMBER, True),
        (UserRole.ENGINEER, INTERNAL_NUMBER, False),
        (UserRole.HRGA, ENGINEERING_NUMBER, False),
        # Unnumbered creation stays lead-only.
        (UserRole.ENGINEER, None, False),
        (UserRole.HRGA, None, False),
        (UserRole.LEAD_ENGINEER, None, True),
        (UserRole.SUPERUSER, None, True),
    ],
)
def test_can_create_project_matrix(role: UserRole, number: str | None, allowed: bool) -> None:
    assert can_create_project(role, number) is allowed


def test_is_privileged_excludes_internal_roles() -> None:
    assert is_privileged(UserRole.LEAD_ENGINEER)
    assert is_privileged(UserRole.SUPERUSER)
    assert not is_privileged(UserRole.ENGINEER)
    assert not is_privileged(UserRole.HRGA)
    assert not is_privileged(UserRole.FINANCE)
    assert not is_privileged("UNKNOWN")


def test_folder_permission_messages_are_descriptive() -> None:
    assert "13" in folder_permission_message(ENGINEERING_NUMBER)
    assert "03" in folder_permission_message(INTERNAL_NUMBER)
    assert folder_permission_message(None)


@pytest.mark.anyio
async def test_engineer_can_create_engineering_project() -> None:
    engineer = _user(UserRole.ENGINEER)
    session = AsyncMock()
    session.add = MagicMock()

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        value.id = uuid4()
        now = datetime.now(UTC)
        value.created_at = now
        value.updated_at = now
        value.owner = engineer
        value.documents = []

    session.refresh.side_effect = refresh
    created = await create_project(
        ProjectCreate(name="Plant Review", project_number=ENGINEERING_NUMBER),
        session,
        engineer,
    )
    assert created.name == "Plant Review"
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_engineer_is_rejected_from_internal_project_creation() -> None:
    engineer = _user(UserRole.ENGINEER)
    session = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await create_project(
            ProjectCreate(name="HR Onboarding", project_number=INTERNAL_NUMBER),
            session,
            engineer,
        )
    assert error.value.status_code == 403
    assert "03" in str(error.value.detail)
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_hrga_is_rejected_from_engineering_project_creation() -> None:
    hrga = _user(UserRole.HRGA)
    session = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await create_project(
            ProjectCreate(name="Inspection", project_number=ENGINEERING_NUMBER),
            session,
            hrga,
        )
    assert error.value.status_code == 403
    assert "13" in str(error.value.detail)


@pytest.mark.anyio
async def test_hrga_can_create_internal_project() -> None:
    hrga = _user(UserRole.HRGA)
    session = AsyncMock()
    session.add = MagicMock()

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        value.id = uuid4()
        now = datetime.now(UTC)
        value.created_at = now
        value.updated_at = now
        value.owner = hrga
        value.documents = []

    session.refresh.side_effect = refresh
    created = await create_project(
        ProjectCreate(name="GA Budget", project_number=INTERNAL_NUMBER),
        session,
        hrga,
    )
    assert created.name == "GA Budget"


@pytest.mark.anyio
async def test_engineer_cannot_create_unnumbered_project() -> None:
    engineer = _user(UserRole.ENGINEER)
    session = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await create_project(ProjectCreate(name="Unnumbered"), session, engineer)
    assert error.value.status_code == 403
    session.add.assert_not_called()


def _compiled(query: Any) -> str:
    return str(query)


@pytest.mark.parametrize(
    "role",
    [
        UserRole.ENGINEER,
        UserRole.HRGA,
        UserRole.FINANCE,
        UserRole.LEAD_ENGINEER,
        UserRole.SUPERUSER,
    ],
)
def test_visible_projects_query_scopes_every_role_to_owner(role: UserRole) -> None:
    """Regression: every role lists only its own projects.

    PRISM has no hierarchical role that may read another user's workspace, so
    the listing must filter by ``projects.owner_id`` and must never widen the
    scope with the old cross-user document EXISTS.
    """

    user = _user(role)
    query = _visible_projects_query(user)
    compiled = cast(Select[Any], query).compile()
    sql = str(compiled)
    assert "EXISTS" not in sql.upper()
    assert any(value == user.id for value in compiled.params.values())
    assert "projects.id" in sql


@pytest.mark.anyio
async def test_bima_import_rejects_role_project_mismatch() -> None:
    """Folder RBAC still gates the on-demand import by project-number prefix."""

    from api import projects as projects_api

    engineer = _user(UserRole.ENGINEER)
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    with pytest.raises(HTTPException) as error:
        await projects_api.import_bima_project(
            ImportBimaProjectRequest(
                bima_project_id=901,
                project_number=INTERNAL_NUMBER,
                name="Internal HR Project",
                client_name="Internal",
            ),
            Response(),
            session,
            engineer,
            MagicMock(),
        )

    assert error.value.status_code == 403
    assert "03" in str(error.value.detail)
    session.add.assert_not_called()
