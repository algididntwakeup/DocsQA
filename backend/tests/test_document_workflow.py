"""Tests for document review workflow transitions."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.documents import (
    mark_document_reviewed,
    request_document_revision,
    verify_document,
)
from domain.enums import DocumentStatus, DocumentWorkflowStatus, UserRole
from models.document import Document
from models.project import Project
from models.user import User
from schemas.documents import DocumentWorkflowUpdate


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value.lower()}@test.local",
        hashed_password="unused",
        full_name=role.value,
        role=role,
    )


def _document(owner: User) -> Document:
    return Document(
        id=uuid4(),
        original_filename="review.pdf",
        safe_filename="review",
        media_type="application/pdf",
        size_bytes=10,
        sha256="a" * 64,
        storage_uri="local://review.pdf",
        owner_id=owner.id,
        owner=owner,
        assigned_to_id=owner.id,
        assigned_to=owner,
        status=DocumentStatus.COMPLETED,
        progress_pct=100,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.anyio
async def test_owner_can_mark_document_reviewed() -> None:
    engineer = _user(UserRole.ENGINEER)
    document = _document(engineer)
    session = AsyncMock()

    result = await mark_document_reviewed(document.id, session, engineer, document)

    assert result.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    assert document.reviewed_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_assigned_engineer_can_mark_reviewed() -> None:
    owner = _user(UserRole.LEAD_ENGINEER)
    assignee = _user(UserRole.ENGINEER)
    document = _document(owner)
    document.assigned_to_id = assignee.id
    document.assigned_to = assignee
    session = AsyncMock()

    result = await mark_document_reviewed(document.id, session, assignee, document)

    assert result.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    assert document.reviewed_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_project_owner_can_mark_document_reviewed() -> None:
    """The workspace owner may finish the review of a document they did not upload."""

    uploader = _user(UserRole.ENGINEER)
    project_owner = _user(UserRole.LEAD_ENGINEER)
    document = _document(uploader)
    document.project = Project(
        id=uuid4(),
        name="Plant Upgrade",
        owner_id=project_owner.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document.project_id = document.project.id
    session = AsyncMock()

    result = await mark_document_reviewed(document.id, session, project_owner, document)

    assert result.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    assert document.reviewed_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_local_superuser_can_mark_document_reviewed() -> None:
    """A locally flagged superuser bypasses the ownership rules entirely."""

    uploader = _user(UserRole.ENGINEER)
    superuser = _user(UserRole.ENGINEER)
    superuser.is_superuser = True
    document = _document(uploader)
    session = AsyncMock()

    result = await mark_document_reviewed(document.id, session, superuser, document)

    assert result.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    assert document.reviewed_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_unrelated_engineer_cannot_mark_document_reviewed() -> None:
    """An unrelated engineer still cannot submit someone else's review."""

    owner = _user(UserRole.ENGINEER)
    document = _document(owner)
    session = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await mark_document_reviewed(document.id, session, _user(UserRole.ENGINEER), document)

    assert error.value.status_code == 403
    assert "superuser" in str(error.value.detail)
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_non_owner_cannot_mark_document_reviewed() -> None:
    owner = _user(UserRole.ENGINEER)
    document = _document(owner)
    document.assigned_to_id = None
    document.assigned_to = None
    session = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await mark_document_reviewed(document.id, session, _user(UserRole.ENGINEER), document)

    assert error.value.status_code == 403
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_lead_can_verify_and_request_revision() -> None:
    owner = _user(UserRole.ENGINEER)
    lead = _user(UserRole.LEAD_ENGINEER)
    document = _document(owner)
    session = AsyncMock()

    verified = await verify_document(
        document.id,
        session,
        lead,
        document,
        DocumentWorkflowUpdate(verification_notes="Approved after review."),
    )
    assert verified.workflow_status == DocumentWorkflowStatus.VERIFIED_BY_LEAD
    assert document.verified_by_id == lead.id
    assert document.verification_notes == "Approved after review."

    revised = await request_document_revision(
        document.id,
        session,
        lead,
        document,
        DocumentWorkflowUpdate(
            workflow_status=DocumentWorkflowStatus.ANALYZING,
            verification_notes="Please correct the traceability gaps.",
        ),
    )
    assert revised.workflow_status == DocumentWorkflowStatus.ANALYZING
    assert document.verified_by_id is None
    assert document.verified_at is None
    assert document.reviewed_at is None
    assert document.verification_notes == "Please correct the traceability gaps."
