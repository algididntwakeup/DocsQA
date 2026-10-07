"""Tests for the workspace's stage-aware progress scale."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.documents import _stage_progress, get_document_status, retry_document_analysis
from domain.enums import DocumentStatus, DocumentWorkflowStatus, StageStatus, UserRole
from models.document import Document, StageRun
from models.user import User
from schemas.documents import DocumentRead


@pytest.mark.parametrize(
    ("stage_name", "stage_progress", "expected_stage", "expected_progress"),
    [
        ("extraction", 0, "Text extraction", 10),
        ("EXTRACTING", 100, "Text extraction", 25),
        ("BUDINSKI_AUDIT", 0, "Budinski checks", 30),
        ("ref_drift", 100, "Table/reference checks", 80),
        ("AGGREGATING", 100, "Report synthesis", 99),
    ],
)
def test_stage_progress_maps_pipeline_steps(
    stage_name: str,
    stage_progress: int,
    expected_stage: str,
    expected_progress: int,
) -> None:
    assert _stage_progress(stage_name, stage_progress) == (expected_stage, expected_progress)


def test_status_endpoint_returns_failure_context() -> None:
    document_id = uuid4()
    now = datetime.now(UTC)
    failed_stage = StageRun(
        id=uuid4(),
        document_id=document_id,
        stage_name="extraction",
        status=StageStatus.FAILED,
        progress_pct=0,
        attempt=1,
        error_message="The source file could not be read.",
        created_at=now,
        updated_at=now,
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [failed_stage]
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = result
    document = SimpleNamespace(
        id=document_id,
        status=DocumentStatus.FAILED,
        progress_pct=0,
        updated_at=now,
    )

    response = asyncio.run(
        get_document_status(
            document_id,
            cast(AsyncSession, session),
            cast(Document, document),
        )
    )

    assert response.current_stage == "Text extraction"
    assert response.error_message == "The source file could not be read."


def test_document_owner_can_retry_failed_analysis() -> None:
    document_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(UTC)
    document = SimpleNamespace(
        id=document_id,
        owner_id=owner_id,
        assigned_to_id=None,
        status=DocumentStatus.FAILED,
        progress_pct=54,
    )
    current_user = SimpleNamespace(id=owner_id, role=UserRole.ENGINEER)
    session = AsyncMock(spec=AsyncSession)
    expected_response = DocumentRead(
        id=document_id,
        original_filename="retry.pdf",
        media_type="application/pdf",
        size_bytes=1,
        sha256="0" * 64,
        status=DocumentStatus.QUEUED,
        progress_pct=0,
        workflow_status=DocumentWorkflowStatus.ANALYZING,
        created_at=now,
        updated_at=now,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        enqueue = AsyncMock()
        serialize = MagicMock(return_value=expected_response)
        monkeypatch.setattr("api.documents.enqueue_extraction", enqueue)
        monkeypatch.setattr("api.documents._document_read", serialize)

        response = asyncio.run(
            retry_document_analysis(
                document_id,
                cast(AsyncSession, session),
                cast(User, current_user),
                cast(Document, document),
            )
        )

    assert document.status == DocumentStatus.QUEUED
    assert document.progress_pct == 0
    session.commit.assert_awaited_once()
    enqueue.assert_awaited_once_with(document, session)
    assert response.status == DocumentStatus.QUEUED


def test_read_only_user_cannot_retry_failed_analysis() -> None:
    document_id = uuid4()
    current_user = SimpleNamespace(id=uuid4(), role=UserRole.ENGINEER)
    document = SimpleNamespace(
        id=document_id,
        owner_id=uuid4(),
        assigned_to_id=None,
        status=DocumentStatus.FAILED,
        progress_pct=0,
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            retry_document_analysis(
                document_id,
                cast(AsyncSession, AsyncMock(spec=AsyncSession)),
                cast(User, current_user),
                cast(Document, document),
            )
        )

    assert raised.value.status_code == 403
