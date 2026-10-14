"""Project lifecycle and project-scoped document visibility tests."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.projects import delete_project, finish_project
from core.dependencies import require_lead
from domain.enums import DocumentStatus, DocumentWorkflowStatus, UserRole
from models.document import Document
from models.project import Project
from models.user import User


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


def _project(lead: User, documents: list[Document] | None = None) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=uuid4(),
        name="Plant Lifecycle",
        owner_id=lead.id,
        owner=lead,
        documents=documents or [],
        created_at=now,
        updated_at=now,
    )


def _superuser() -> User:
    """An account carrying the local PRISM superuser flag."""
    user = _user(UserRole.ENGINEER)
    user.is_superuser = True
    return user


def _bima_project(lead: User, bima_project_id: int = 4242) -> Project:
    project = _project(lead)
    project.bima_project_id = bima_project_id
    return project


def _stub_session(project: Project) -> AsyncMock:
    session = AsyncMock()
    result = type(
        "Result", (), {"unique": lambda self: self, "scalar_one_or_none": lambda self: project}
    )()
    session.execute.return_value = result
    session.add = MagicMock()
    return session


@pytest.mark.anyio
async def test_only_lead_holds_project_admin_privileges() -> None:
    with pytest.raises(HTTPException) as error:
        await require_lead(_user(UserRole.ENGINEER))
    assert error.value.status_code == 403


@pytest.mark.anyio
async def test_lead_can_create_project() -> None:
    from api.projects import create_project
    from schemas.project import ProjectCreate

    lead = _user(UserRole.LEAD_ENGINEER)
    session = AsyncMock()
    session.add = MagicMock()

    async def refresh(val: Any, *args: Any, **kwargs: Any) -> None:
        val.id = uuid4()
        now = datetime.now(UTC)
        val.created_at = now
        val.updated_at = now
        val.owner = lead
        val.documents = []

    session.refresh.side_effect = refresh

    created = await create_project(
        ProjectCreate(name="New Plant"),
        session,
        lead,
    )
    assert created.name == "New Plant"
    assert created.owner_id == lead.id
    assert created.owner_name == lead.full_name
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


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


@pytest.mark.anyio
async def test_delete_rejects_bima_imported_project() -> None:
    """Imported folders mirror BIMA, so PRISM must refuse to drop them."""
    lead = _user(UserRole.LEAD_ENGINEER)
    project = _bima_project(lead)
    session = _stub_session(project)

    with pytest.raises(HTTPException) as error:
        await delete_project(project.id, session, lead)

    assert error.value.status_code == 403
    assert "BIMA" in str(error.value.detail)
    session.delete.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_rejects_foreign_custom_project() -> None:
    """A custom project is private to its owner unless a superuser asks."""
    owner = _user(UserRole.LEAD_ENGINEER)
    intruder = _user(UserRole.LEAD_ENGINEER)
    project = _project(owner)
    session = _stub_session(project)

    with pytest.raises(HTTPException) as error:
        await delete_project(project.id, session, intruder)

    assert error.value.status_code == 403
    session.delete.assert_not_awaited()


@pytest.mark.anyio
async def test_superuser_can_delete_foreign_custom_project() -> None:
    owner = _user(UserRole.LEAD_ENGINEER)
    project = _project(owner)
    session = _stub_session(project)

    await delete_project(project.id, session, _superuser())

    session.delete.assert_awaited_once_with(project)


@pytest.mark.anyio
async def test_superuser_bypasses_prefix_validation_on_create() -> None:
    """The local flag outranks the BIMA prefix rules, including no number."""
    from api.projects import create_project
    from schemas.project import ProjectCreate

    admin = _superuser()
    session = _stub_session(_project(admin))

    async def refresh(value: Any, *args: Any, **kwargs: Any) -> None:
        value.id = uuid4()
        now = datetime.now(UTC)
        value.created_at = now
        value.updated_at = now
        value.owner = admin
        value.documents = []

    session.refresh.side_effect = refresh

    for number in ("03-2026-001", "13-9999", None):
        created = await create_project(
            ProjectCreate(name="Admin Project", project_number=number), session, admin
        )
        assert created.name == "Admin Project"


@pytest.mark.anyio
async def test_plain_engineer_still_blocked_by_prefix_rules() -> None:
    """The bypass must not leak to accounts without the flag."""
    from api.projects import create_project
    from schemas.project import ProjectCreate

    engineer = _user(UserRole.ENGINEER)
    session = _stub_session(_project(engineer))

    with pytest.raises(HTTPException) as error:
        await create_project(
            ProjectCreate(name="Internal", project_number="03-2026-001"), session, engineer
        )

    assert error.value.status_code == 403
    session.commit.assert_not_awaited()


def _document_owned_by(project: Project, owner: User) -> Document:
    now = datetime.now(UTC)
    document = Document(
        id=uuid4(),
        original_filename="member-visible.pdf",
        safe_filename="member-visible",
        media_type="application/pdf",
        size_bytes=1,
        sha256="b" * 64,
        storage_uri="local://member-visible.pdf",
        status=DocumentStatus.COMPLETED,
        progress_pct=100,
        project_id=project.id,
        workflow_status=DocumentWorkflowStatus.ANALYZING,
        created_at=now,
        updated_at=now,
    )
    document.project = project
    document.owner = owner
    document.assigned_to = None
    return document


@pytest.mark.anyio
async def test_project_owner_lists_all_project_documents() -> None:
    from api.projects import list_project_documents

    lead = _user(UserRole.LEAD_ENGINEER)
    project = _project(lead)
    document = _document_owned_by(project, lead)
    session = AsyncMock()
    session.execute.side_effect = [
        type("CountResult", (), {"scalar_one": lambda self: 1})(),
        type(
            "Result",
            (),
            {"scalars": lambda self: type("Scalars", (), {"all": lambda _s: [document]})()},
        )(),
    ]

    response = await list_project_documents(project.id, session, lead)

    assert [item.id for item in response.documents] == [document.id]


@pytest.mark.anyio
async def test_unrelated_engineer_sees_no_documents_in_foreign_project() -> None:
    from api.projects import list_project_documents

    lead = _user(UserRole.LEAD_ENGINEER)
    outsider = _user(UserRole.ENGINEER)
    project = _project(lead)
    session = AsyncMock()
    session.execute.side_effect = [
        type("CountResult", (), {"scalar_one": lambda self: 0})(),
        type(
            "Result",
            (),
            {"scalars": lambda self: type("Scalars", (), {"all": lambda _s: []})()},
        )(),
    ]

    response = await list_project_documents(project.id, session, outsider)

    assert response.documents == []
