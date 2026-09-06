"""Document Retention Policy and Cleanup Service.

Enforces ephemeral upload retention boundaries (default 30 days) by pruning
expired document records, storage files, and extraction artifacts per PRD §4.3 and
Acceptance Matrix §2.
"""

from __future__ import annotations

import contextlib
import shutil
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select

from models.document import Document

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.storage.local import LocalStorage


async def get_retention_metrics(
    session: AsyncSession,
    retention_days: int = 30,
) -> dict[str, Any]:
    """Calculate current retention metrics and count documents eligible for expiration."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    total_docs = (await session.execute(select(func.count(Document.id)))).scalar_one()

    expired_count = (
        await session.execute(select(func.count(Document.id)).where(Document.created_at < cutoff))
    ).scalar_one()

    oldest_created = (
        await session.execute(select(func.min(Document.created_at)))
    ).scalar_one_or_none()

    return {
        "retention_days": retention_days,
        "cutoff_timestamp": cutoff.isoformat(),
        "total_documents": total_docs,
        "expired_documents": expired_count,
        "oldest_document_date": oldest_created.isoformat() if oldest_created else None,
    }


async def cleanup_expired_documents(
    session: AsyncSession,
    storage: LocalStorage,
    retention_days: int = 30,
) -> int:
    """Purge documents and their disk artifacts that exceed the retention boundary."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    stmt = select(Document).where(Document.created_at < cutoff)
    expired_documents = (await session.execute(stmt)).scalars().all()

    if not expired_documents:
        return 0

    cleaned_count = 0
    for doc in expired_documents:
        doc_id_str = str(doc.id)

        # 1. Clean up storage files
        for uri in (doc.storage_uri, doc.canonical_pdf_uri):
            if uri:
                with contextlib.suppress(Exception):
                    if uri.startswith(storage.scheme):
                        storage.delete(uri)
                    else:
                        suffix = uri.split("://", 1)[-1] if "://" in uri else uri
                        target = storage.root / suffix
                        if target.exists() and target.is_file():
                            target.unlink()

        # 2. Clean up artifact directory (e.g. artifacts/{document_id})
        artifacts_dir = storage.root / "artifacts" / doc_id_str
        if artifacts_dir.exists() and artifacts_dir.is_dir():
            with contextlib.suppress(OSError):
                shutil.rmtree(artifacts_dir, ignore_errors=True)

        # 3. Clean up database record (foreign keys cascade to stage_runs, issues, audit_events)
        await session.execute(delete(Document).where(Document.id == doc.id))
        cleaned_count += 1

    await session.commit()
    return cleaned_count
