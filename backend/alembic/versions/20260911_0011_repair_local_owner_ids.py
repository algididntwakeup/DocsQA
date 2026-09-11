"""Repair documents created by the synthetic disabled-auth user."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0011"
down_revision: str | Sequence[str] | None = "20260910_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Map legacy zero UUID owners to the seeded local superuser."""
    documents = sa.table(
        "documents",
        sa.column("owner_id", sa.Uuid()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
    )
    admin_id = sa.select(users.c.id).where(users.c.email == "admin@localhost").scalar_subquery()
    op.execute(
        documents.update()
        .where(documents.c.owner_id == UUID("00000000-0000-0000-0000-000000000000"))
        .values(owner_id=admin_id)
    )


def downgrade() -> None:
    """Do not restore synthetic zero UUID ownership."""
