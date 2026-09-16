"""Add BIMA project identity and status fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260916_0014"
down_revision: str | Sequence[str] | None = "20260916_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("bima_project_id", sa.Integer(), nullable=True))
    op.add_column(
        "projects", sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE")
    )
    op.create_index("ix_projects_bima_project_id", "projects", ["bima_project_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_projects_bima_project_id", table_name="projects")
    op.drop_column("projects", "status")
    op.drop_column("projects", "bima_project_id")
