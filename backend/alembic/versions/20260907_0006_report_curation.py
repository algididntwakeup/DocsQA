"""replace approval workflow fields with report curation

Revision ID: 20260907_0006
Revises: 20260906_0005
"""

import sqlalchemy as sa

from alembic import op

revision = "20260907_0006"
down_revision = "20260906_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column("included_in_report", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("issues", sa.Column("reviewer_note", sa.Text(), nullable=True))
    op.drop_column("documents", "review_status")
    op.drop_table("audit_events")
    legacy_columns = (
        "decision",
        "decision_comment",
        "decision_by",
        "disposition",
        "disposition_justification",
        "disposition_by",
        "version",
    )
    for column in legacy_columns:
        op.drop_column("issues", column)


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="PENDING"),
    )
    op.add_column(
        "issues",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("issues", sa.Column("disposition_by", sa.String(length=100), nullable=True))
    op.add_column("issues", sa.Column("disposition_justification", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("disposition", sa.String(length=32), nullable=True))
    op.add_column("issues", sa.Column("decision_by", sa.String(length=100), nullable=True))
    op.add_column("issues", sa.Column("decision_comment", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("decision", sa.String(length=32), nullable=True))
    op.drop_column("issues", "reviewer_note")
    op.drop_column("issues", "included_in_report")
