"""Project assignment authorization tests."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.projects import assign_project, delete_project, finish_project
from core.dependencies import require_lead
from domain.enums import DocumentStatus, UserRole
from models.document import Document
from models.project import Project
from models.user import User
from schemas.project import ProjectAssignment


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value.lower()}@project.test",
        hashed_password="unused",
        full_name=role.value,
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.mark.anyio
async def test_only_lead_can_assign_projects() -> None:
    with pytest.raises(HTTPException) as error:
        await require_lead(_user(UserRole.ENGINEER))
    assert error.value.status_code == 403


@pytest.mark.anyio
async def test_lead_can_create_project() -> None:
    from api.projects import create_project
    from schemas.project import ProjectCreate

    lead = _user(UserRole.LEAD_ENGINEER)
    session = AsyncMock()

    async def refresh(val: Any, *args: Any, **kwargs: Any) -> None:
        val.id = uuid4()
        val.created_at = datetime.now(UTC)
        val.created_by = lead
        val.assigned_to = None
        val.documents = []

    session.refresh.side_effect = refresh

    created = await create_project(
        ProjectCreate(name="New Plant"),
        session,
        lead,
    )
    assert created.name == "New Plant"
    assert created.created_by_name == lead.full_name
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_lead_can_assign_active_engineer() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    project = Project(
        id=uuid4(),
        name="Plant",
        created_by_id=lead.id,
        created_by=lead,
        documents=[],
        assigned_to=None,
        created_at=datetime.now(UTC),
    )
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result
    assigned_result = type("AssignedResult", (), {"scalar_one_or_none": lambda self: engineer})()
    session.execute.side_effect = [result, assigned_result]

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
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


@pytest.mark.anyio
async def test_assign_project_refreshes_relationships() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    project = Project(
        id=uuid4(),
        name="Plant Alpha",
        created_by_id=lead.id,
        created_by=lead,
        documents=[],
        assigned_to=None,
        created_at=datetime.now(UTC),
    )
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    assigned_result = type("AssignedResult", (), {"scalar_one_or_none": lambda self: engineer})()
    session.execute.side_effect = [result, assigned_result]

    refresh_calls = []

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        refresh_calls.append((value, args, kwargs))
        value.assigned_to = engineer

    session.refresh.side_effect = refresh

    updated = await assign_project(
        project.id,
        ProjectAssignment(assigned_to_id=engineer.id),
        session,
        lead,
    )

    assert updated.assigned_to_id == engineer.id
    assert updated.assigned_to_name == engineer.full_name
    session.refresh.assert_awaited_once()
    assert refresh_calls[0][2].get("attribute_names") == ["created_by", "assigned_to", "documents"]


def _project(lead: User, documents: list[Document] | None = None) -> Project:
    return Project(
        id=uuid4(),
        name="Plant Lifecycle",
        created_by_id=lead.id,
        created_by=lead,
        documents=documents or [],
        assigned_to=None,
        created_at=datetime.now(UTC),
    )


@pytest.mark.anyio
async def test_lead_can_finish_terminal_project() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    project = _project(lead)
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        return None

    session.refresh.side_effect = refresh

    finished = await finish_project(project.id, session, lead)

    assert finished.status == "FINISHED"
    assert project.finished_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_finish_rejects_processing_document() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    document = Document(
        id=uuid4(),
        original_filename="queued.pdf",
        safe_filename="queued",
        media_type="application/pdf",
        size_bytes=1,
        sha256="a" * 64,
        storage_uri="local://queued.pdf",
        status=DocumentStatus.PROCESSING,
        progress_pct=42,
    )
    project = _project(lead, [document])
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        await finish_project(project.id, session, lead)

    assert error.value.status_code == 409
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_only_allows_empty_project() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    project = _project(lead)
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result

    await delete_project(project.id, session, lead)

    session.delete.assert_awaited_once_with(project)
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_finished_project_rejects_assignment() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    project = _project(lead)
    project.finished_at = datetime.now(UTC)
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        await assign_project(
            project.id,
            ProjectAssignment(assigned_to_id=engineer.id),
            session,
            lead,
        )

    assert error.value.status_code == 409
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_rejects_project_with_documents() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    project = _project(lead, [Document(id=uuid4(), original_filename="review.pdf")])
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        await delete_project(project.id, session, lead)

    assert error.value.status_code == 409
    session.delete.assert_not_awaited()
