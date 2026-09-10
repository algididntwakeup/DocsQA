"""Add optional project assignment ownership."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0009"
down_revision: str | Sequence[str] | None = "20260910_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("assigned_to_id", sa.Uuid(), nullable=True))
    op.create_index("ix_projects_assigned_to_id", "projects", ["assigned_to_id"])
    op.create_foreign_key(
        "fk_projects_assigned_to_id_users", "projects", "users", ["assigned_to_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_assigned_to_id_users", "projects", type_="foreignkey")
    op.drop_index("ix_projects_assigned_to_id", table_name="projects")
    op.drop_column("projects", "assigned_to_id")
