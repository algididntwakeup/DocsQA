"""Prevent concurrent active scans of identical document bytes.

Revision ID: 20260904_0002
Revises: 20260904_0001
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0002"
down_revision: str | Sequence[str] | None = "20260904_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow a content hash to have at most one queued or processing scan."""

    op.create_index(
        "uq_documents_active_sha256",
        "documents",
        ["sha256"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'PROCESSING')"),
    )


def downgrade() -> None:
    """Remove the active-scan deduplication constraint."""

    op.drop_index("uq_documents_active_sha256", table_name="documents")
