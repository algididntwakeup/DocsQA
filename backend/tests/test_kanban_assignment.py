"""Tests for per-engineer document assignment and the WIP=1 policy."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.documents import WIP_ERROR, assign_document, check_engineer_wip_available, claim_document
from domain.enums import DocumentStatus, DocumentWorkflowStatus, UserRole
from models.document import Document
from models.user import User
from schemas.documents import DocumentAssignment


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value.lower()}-{uuid4()}@test.local",
        hashed_password="unused",
        full_name=role.value,
        role=role,
        is_active=True,
    )


def _document(
    *, assigned_to: User | None = None, status=DocumentWorkflowStatus.ANALYZING
) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        original_filename="review.pdf",
        safe_filename="review",
        media_type="application/pdf",
        size_bytes=10,
        sha256=uuid4().hex + uuid4().hex,
        storage_uri=f"local://{uuid4()}.pdf",
        owner_id=assigned_to.id if assigned_to else None,
        owner=assigned_to,
        assigned_to_id=assigned_to.id if assigned_to else None,
        assigned_to=assigned_to,
        status=DocumentStatus.COMPLETED,
        workflow_status=status,
        progress_pct=100,
        created_at=now,
        updated_at=now,
    )


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.anyio
async def test_claim_succeeds_when_slot_is_empty() -> None:
    engineer = _user(UserRole.ENGINEER)
    document = _document()
    session = AsyncMock()
    session.execute.side_effect = [Result(engineer), Result(document), Result(None)]

    result = await claim_document(document.id, session, engineer)

    assert result.assigned_to_id == engineer.id
    assert result.owner_id == engineer.id
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_claim_is_rejected_when_wip_is_full() -> None:
    engineer = _user(UserRole.ENGINEER)
    document = _document()
    active = _document(assigned_to=engineer)
    session = AsyncMock()
    session.execute.side_effect = [Result(engineer), Result(document), Result(active)]

    with pytest.raises(HTTPException) as error:
        await claim_document(document.id, session, engineer)

    assert error.value.status_code == 400
    assert error.value.detail == WIP_ERROR
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_reviewed_document_frees_wip_slot() -> None:
    engineer = _user(UserRole.ENGINEER)
    reviewed = _document(assigned_to=engineer, status=DocumentWorkflowStatus.REVIEWED_BY_ENGINEER)
    session = AsyncMock()
    session.execute.return_value = Result(None)

    available, active = await check_engineer_wip_available(session, engineer.id)

    assert available is True
    assert active is None
    assert reviewed.workflow_status == DocumentWorkflowStatus.REVIEWED_BY_ENGINEER


@pytest.mark.anyio
async def test_lead_assign_normal_and_override() -> None:
    lead = _user(UserRole.LEAD_ENGINEER)
    engineer = _user(UserRole.ENGINEER)
    first = _document(assigned_to=engineer)
    normal_target = _document()
    override_target = _document()

    session = AsyncMock()
    session.execute.side_effect = [
        Result(normal_target),
        Result(engineer),
        Result(first),
        Result(override_target),
        Result(engineer),
    ]

    with pytest.raises(HTTPException) as error:
        await assign_document(
            normal_target.id,
            DocumentAssignment(engineer_id=engineer.id),
            session,
            lead,
        )
    assert error.value.status_code == 400
    assert error.value.detail["active_document"]["id"] == str(first.id)

    result = await assign_document(
        override_target.id,
        DocumentAssignment(engineer_id=engineer.id, override_wip=True),
        session,
        lead,
    )

    assert result.assigned_to_id == engineer.id
    assert result.owner_id == engineer.id
    assert session.commit.await_count == 1
