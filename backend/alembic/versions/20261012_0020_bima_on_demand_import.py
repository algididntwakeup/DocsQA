"""Drop BIMA assignment mirroring and rename project ownership to owner_id.

BIMA only exposes a flat project directory, so PRISM no longer mirrors BIMA
membership or project assignment: the ``project_members`` association and
``projects.assigned_to_id`` are removed, the single project owner is renamed
from ``created_by_id`` to ``owner_id``, and ``projects.updated_at`` is added to
match the shared timestamp mixin.

``documents.assigned_to_id`` is intentionally untouched: document-level kanban
assignment is a PRISM workflow concept, not BIMA mirroring.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261012_0020"
down_revision: str | Sequence[str] | None = "20261007_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_table("project_members")

    op.drop_constraint("fk_projects_assigned_to_id_users", "projects", type_="foreignkey")
    op.drop_index("ix_projects_assigned_to_id", table_name="projects")
    op.drop_column("projects", "assigned_to_id")

    op.drop_constraint("fk_projects_created_by_id_users", "projects", type_="foreignkey")
    op.drop_index("ix_projects_created_by_id", table_name="projects")
    op.alter_column(
        "projects",
        "created_by_id",
        new_column_name="owner_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_foreign_key("fk_projects_owner_id_users", "projects", "users", ["owner_id"], ["id"])

    op.add_column(
        "projects",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "updated_at")

    op.drop_constraint("fk_projects_owner_id_users", "projects", type_="foreignkey")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.alter_column(
        "projects",
        "owner_id",
        new_column_name="created_by_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.create_index("ix_projects_created_by_id", "projects", ["created_by_id"])
    op.create_foreign_key(
        "fk_projects_created_by_id_users", "projects", "users", ["created_by_id"], ["id"]
    )

    op.add_column("projects", sa.Column("assigned_to_id", sa.Uuid(), nullable=True))
    op.create_index("ix_projects_assigned_to_id", "projects", ["assigned_to_id"])
    op.create_foreign_key(
        "fk_projects_assigned_to_id_users", "projects", "users", ["assigned_to_id"], ["id"]
    )

    op.create_table(
        "project_members",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_members_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_project_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "user_id", name=op.f("pk_project_members")),
    )
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
