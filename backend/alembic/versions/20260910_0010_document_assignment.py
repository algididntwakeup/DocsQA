"""Add per-document assignment ownership."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0010"
down_revision: str | Sequence[str] | None = "20260910_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "assigned_to_id" not in columns:
        op.add_column("documents", sa.Column("assigned_to_id", sa.Uuid(), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("documents")}
    if "ix_documents_assigned_to_id" not in indexes:
        op.create_index("ix_documents_assigned_to_id", "documents", ["assigned_to_id"])
    foreign_keys = {foreign_key["name"] for foreign_key in inspector.get_foreign_keys("documents")}
    if "fk_documents_assigned_to_id_users" not in foreign_keys:
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
