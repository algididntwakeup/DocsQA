"""Add per-document assignment ownership."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0010"
down_revision: str | Sequence[str] | None = "20260910_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # This migration runs against the schema created by 0007 and must also
    # support Alembic's offline SQL generation, where inspection is unavailable.
    op.add_column("documents", sa.Column("assigned_to_id", sa.Uuid(), nullable=True))
    op.create_index("ix_documents_assigned_to_id", "documents", ["assigned_to_id"])
    op.create_foreign_key(
        "fk_documents_assigned_to_id_users",
        "documents",
        "users",
        ["assigned_to_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_assigned_to_id_users", "documents", type_="foreignkey")
    op.drop_index("ix_documents_assigned_to_id", table_name="documents")
    op.drop_column("documents", "assigned_to_id")
