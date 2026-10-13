"""Scope BIMA imports per owner instead of globally.

The on-demand BIMA import must be idempotent *per user*: two engineers may each
import the same BIMA directory project into their own workspace. The previous
global unique index on ``projects.bima_project_id`` prevented the second import
and made the BIMA catalog report another user's project as the caller's import,
so the global uniqueness is replaced by a composite
``(owner_id, bima_project_id)`` constraint.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261013_0021"
down_revision: str | Sequence[str] | None = "20261012_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_projects_bima_project_id", table_name="projects")
    op.create_index("ix_projects_bima_project_id", "projects", ["bima_project_id"], unique=False)
    op.create_unique_constraint(
        "uq_projects_owner_bima_project_id", "projects", ["owner_id", "bima_project_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_projects_owner_bima_project_id", "projects", type_="unique")
    op.drop_index("ix_projects_bima_project_id", table_name="projects")
    op.create_index("ix_projects_bima_project_id", "projects", ["bima_project_id"], unique=True)
