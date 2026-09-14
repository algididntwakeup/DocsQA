"""Add project finish timestamp."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260914_0012"
down_revision: str | Sequence[str] | None = "20260911_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "finished_at")
