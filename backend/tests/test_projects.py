"""Project assignment authorization tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.projects import assign_project
from core.dependencies import require_lead
from domain.enums import UserRole
from models.project import Project
from models.user import User
from schemas.project import ProjectAssignment


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(), email=f"{role.value.lower()}@project.test", hashed_password="unused",
        full_name=role.value, role=role, is_active=True, created_at=datetime.now(UTC),
    )


@pytest.mark.anyio
async def test_only_lead_can_assign_projects() -> None:
    with pytest.raises(HTTPException) as error:
        await require_lead(_user(UserRole.ENGINEER))
    assert error.value.status_code == 403


@pytest.mark.anyio
async def test_lead_can_assign_active_engineer() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    project = Project(
        id=uuid4(), name="Plant", created_by_id=lead.id, created_by=lead,
        documents=[], assigned_to=None, created_at=datetime.now(UTC),
    )
    session = AsyncMock()
    result = type("Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project})()
    session.execute.return_value = result
    assigned_result = type("AssignedResult", (), {"scalar_one_or_none": lambda self: engineer})()
    session.execute.side_effect = [result, assigned_result]
    async def refresh(value, *args, **kwargs):
        value.assigned_to = engineer

    session.refresh.side_effect = refresh

    updated = await assign_project(
        project.id,
        ProjectAssignment(assigned_to_id=engineer.id),
        session,
        lead,
    )

    assert updated.assigned_to_id == engineer.id
    session.commit.assert_awaited_once()
