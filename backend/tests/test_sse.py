"""Unit and integration tests for Server-Sent Events (SSE) Real-Time Scan Progress (M5.2)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from db.session import get_session
from domain.enums import DocumentStatus, ReviewStatus, StageStatus
from main import app
from models.document import Document, StageRun


@pytest.mark.anyio
async def test_stream_document_events_success() -> None:
    """SSE endpoint streams valid progress payloads and closes when extracted."""
    doc_id = uuid4()
    now = datetime.now(UTC)

    doc = Document(
        id=doc_id,
        original_filename="PROC-001.pdf",
        safe_filename="proc_001",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="abc123hash",
        status=DocumentStatus.COMPLETED,
        review_status=ReviewStatus.PENDING,
        storage_uri=f"file://documents/{doc_id}.pdf",
        canonical_pdf_uri=f"file://documents/{doc_id}.pdf",
        created_at=now,
        updated_at=now,
    )

    stage1 = StageRun(
        id=uuid4(),
        document_id=doc_id,
        stage_name="extract",
        status=StageStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    stage2 = StageRun(
        id=uuid4(),
        document_id=doc_id,
        stage_name="table_math",
        status=StageStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )

    class MockAsyncSession:
        async def execute(self, stmt: Any) -> Any:
            class MockResult:
                def scalar_one_or_none(self) -> Any:
                    return doc

                def scalars(self) -> Any:
                    class MockScalars:
                        def all(self) -> list[Any]:
                            return [stage1, stage2]

                    return MockScalars()

            return MockResult()

    async def override_get_session() -> Any:
        yield MockAsyncSession()

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(f"/api/v1/documents/{doc_id}/events")
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]

            content = res.text
            assert "event: progress" in content
            assert "event: close" in content

            # Parse SSE data chunk
            data_line = [line for line in content.splitlines() if line.startswith("data: ")][0]
            payload = json.loads(data_line[len("data: ") :])
            assert payload["document_id"] == str(doc_id)
            assert payload["status"] == "COMPLETED"
            assert payload["progress_pct"] == 100
            assert len(payload["stages"]) == 2
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_stream_document_events_not_found() -> None:
    """SSE endpoint returns 404 when document does not exist."""
    missing_id = uuid4()

    class MockEmptySession:
        async def execute(self, stmt: Any) -> Any:
            class MockResult:
                def scalar_one_or_none(self) -> Any:
                    return None

            return MockResult()

    async def override_get_session() -> Any:
        yield MockEmptySession()

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(f"/api/v1/documents/{missing_id}/events")
            assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()
