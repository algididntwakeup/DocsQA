"""Persist identity metadata extracted from document cover pages."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_0016"
down_revision: str | Sequence[str] | None = "20260923_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "extracted_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "extracted_metadata")
