"""Store BIMA project numbers and client names."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_0019"
down_revision: str | Sequence[str] | None = "20261006_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("project_number", sa.String(length=100), nullable=True))
    op.add_column("projects", sa.Column("client_name", sa.String(length=255), nullable=True))
    op.create_index("ix_projects_project_number", "projects", ["project_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_projects_project_number", table_name="projects")
    op.drop_column("projects", "client_name")
    op.drop_column("projects", "project_number")
