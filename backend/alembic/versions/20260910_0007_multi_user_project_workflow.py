"""Add users, projects, and document review workflow.

Revision ID: 20260910_0007
Revises: 20260907_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0007"
down_revision: str | Sequence[str] | None = "20260907_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEAD_USER_ID = "00000000-0000-0000-0000-000000000001"
ENGINEER_USER_ID = "00000000-0000-0000-0000-000000000002"
LOCAL_PASSWORD_HASH = "$2b$12$RxnVDS.fJ5BOgngoWsHaJeFnC5BPhdyh/GtcGKKUubSa74xiizHem"


def upgrade() -> None:
    """Create account/project tables and extend document workflow metadata."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ENGINEER", "LEAD_ENGINEER", name="user_role", native_enum=False),
            server_default="ENGINEER",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("plant_area", sa.String(length=100), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], name=op.f("fk_projects_created_by_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("owner_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("verified_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "workflow_status",
                sa.Enum(
                    "ANALYZING",
                    "REVIEWED_BY_ENGINEER",
                    "VERIFIED_BY_LEAD",
                    name="document_workflow_status",
                    native_enum=False,
                ),
                server_default="ANALYZING",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_documents_project_id_projects"), "projects", ["project_id"], ["id"]
        )
        batch_op.create_foreign_key(
            op.f("fk_documents_owner_id_users"), "users", ["owner_id"], ["id"]
        )
        batch_op.create_foreign_key(
            op.f("fk_documents_verified_by_id_users"), "users", ["verified_by_id"], ["id"]
        )

    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("role", sa.String()),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": LEAD_USER_ID,
                "email": "lead.engineer@localhost",
                "hashed_password": LOCAL_PASSWORD_HASH,
                "full_name": "Local Lead Engineer",
                "role": "LEAD_ENGINEER",
            },
            {
                "id": ENGINEER_USER_ID,
                "email": "engineer@localhost",
                "hashed_password": LOCAL_PASSWORD_HASH,
                "full_name": "Local Engineer",
                "role": "ENGINEER",
            },
        ],
    )


def downgrade() -> None:
    """Remove workflow metadata, project table, and seeded accounts."""
    users = sa.table("users", sa.column("id", sa.Uuid()))
    op.execute(
        users.delete().where(
            users.c.id.in_([sa.literal(LEAD_USER_ID), sa.literal(ENGINEER_USER_ID)])
        )
    )
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint(op.f("fk_documents_verified_by_id_users"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_documents_owner_id_users"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_documents_project_id_projects"), type_="foreignkey")
        for column in (
            "verification_notes",
            "verified_at",
            "reviewed_at",
            "workflow_status",
            "verified_by_id",
            "owner_id",
            "project_id",
        ):
            batch_op.drop_column(column)
    op.drop_table("projects")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
