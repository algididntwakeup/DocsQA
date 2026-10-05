"""Persist per-project report header settings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_0017"
down_revision: str | Sequence[str] | None = "20261002_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("header_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("projects", "header_config")
