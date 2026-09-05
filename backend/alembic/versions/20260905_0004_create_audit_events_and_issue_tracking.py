"""Create audit_events table and issue decision/disposition tracking columns.

Revision ID: 20260905_0004
Revises: 20260905_0003
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0004"
down_revision: str | Sequence[str] | None = "20260905_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tracking columns to issues and create audit_events table."""

    # 1. Add tracking columns to issues
    op.add_column("issues", sa.Column("decision_comment", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("decision_by", sa.String(length=100), nullable=True))
    op.add_column("issues", sa.Column("disposition_justification", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("disposition_by", sa.String(length=100), nullable=True))

    # 2. Create audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_audit_events_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name="fk_audit_events_issue_id_issues",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index(
        "ix_audit_events_document_id",
        "audit_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_issue_id",
        "audit_events",
        ["issue_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_document_created",
        "audit_events",
        ["document_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_issue_created",
        "audit_events",
        ["issue_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop audit_events table and issue tracking columns."""

    op.drop_index("ix_audit_events_issue_created", table_name="audit_events")
    op.drop_index("ix_audit_events_document_created", table_name="audit_events")
    op.drop_index("ix_audit_events_issue_id", table_name="audit_events")
    op.drop_index("ix_audit_events_document_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_column("issues", "disposition_by")
    op.drop_column("issues", "disposition_justification")
    op.drop_column("issues", "decision_by")
    op.drop_column("issues", "decision_comment")
