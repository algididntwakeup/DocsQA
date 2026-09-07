"""Unit tests for Retention Policy and Cleanup Service (M5.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DocumentStatus
from models.document import Document
from services.retention import cleanup_expired_documents, get_retention_metrics
from services.storage.local import LocalStorage


@pytest.mark.anyio
async def test_retention_metrics_and_cleanup(tmp_path: Path) -> None:
    """Expired documents are purged while valid recent documents are retained."""
    storage = LocalStorage(root=tmp_path)
    now = datetime.now(UTC)

    recent_doc_id = uuid4()
    expired_doc_id = uuid4()

    _recent_doc = Document(
        id=recent_doc_id,
        original_filename="recent.pdf",
        safe_filename="recent",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="recenthash",
        status=DocumentStatus.COMPLETED,
        storage_uri=f"local://documents/{recent_doc_id}.pdf",
        canonical_pdf_uri=None,
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=5),
    )

    expired_doc = Document(
        id=expired_doc_id,
        original_filename="expired.pdf",
        safe_filename="expired",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="expiredhash",
        status=DocumentStatus.COMPLETED,
        storage_uri=f"local://documents/{expired_doc_id}.pdf",
        canonical_pdf_uri=None,
        created_at=now - timedelta(days=45),
        updated_at=now - timedelta(days=45),
    )

    # Create dummy files in storage
    doc_dir = tmp_path / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    recent_file = doc_dir / f"{recent_doc_id}.pdf"
    recent_file.write_text("recent-pdf-content")
    expired_file = doc_dir / f"{expired_doc_id}.pdf"
    expired_file.write_text("expired-pdf-content")

    # Create dummy artifact directory
    art_dir = tmp_path / "artifacts" / str(expired_doc_id)
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "extraction.json").write_text("{}")

    deleted_ids: list[Any] = []

    class MockAsyncSession:
        async def execute(self, stmt: Any) -> Any:
            stmt_str = str(stmt).lower()

            class MockResult:
                def scalar_one(self) -> Any:
                    if "count" in stmt_str:
                        if "where" in stmt_str:
                            return 1  # 1 expired
                        return 2  # 2 total
                    return 0

                def scalar_one_or_none(self) -> Any:
                    if "min" in stmt_str:
                        return expired_doc.created_at
                    return None

                def scalars(self) -> Any:
                    class MockScalars:
                        def all(self) -> list[Document]:
                            return [expired_doc]

                    return MockScalars()

            if "delete from documents" in stmt_str:
                deleted_ids.append(expired_doc_id)

            return MockResult()

        async def commit(self) -> None:
            pass

    session = MockAsyncSession()

    # 1. Test retention metrics
    metrics = await get_retention_metrics(cast(AsyncSession, session), retention_days=30)
    assert metrics["retention_days"] == 30
    assert metrics["total_documents"] == 2
    assert metrics["expired_documents"] == 1
    assert metrics["oldest_document_date"] is not None

    # 2. Test cleanup
    cleaned = await cleanup_expired_documents(
        cast(AsyncSession, session), storage, retention_days=30
    )
    assert cleaned == 1
    assert expired_doc_id in deleted_ids

    # Expired file and artifact directory must be deleted
    assert not expired_file.exists()
    assert not art_dir.exists()

    # Recent file must remain intact
    assert recent_file.exists()
