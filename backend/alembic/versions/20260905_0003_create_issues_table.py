"""Create issues table for unified finding persistence.

Revision ID: 20260905_0003
Revises: 20260904_0002
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0003"
down_revision: str | Sequence[str] | None = "20260904_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create issues table with indexes and constraints."""

    op.create_table(
        "issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "LINGUISTIC",
                "TRACEABILITY",
                "SYSTEM",
                name="issue_category",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "INFO",
                name="severity",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "ACCEPTED",
                "REJECTED",
                "EDITED",
                "FLAGGED",
                name="decision",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "disposition",
            sa.Enum(
                "JUSTIFIED_EXCEPTION",
                "REQUIRES_CORRECTION",
                name="disposition",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
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
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_issues_confidence_range"
        ),
        sa.CheckConstraint("version >= 1", name="ck_issues_version_positive"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_issues_document_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_issues"),
    )
    op.create_index(
        "ix_issues_document_category", "issues", ["document_id", "category"], unique=False
    )
    op.create_index(
        "ix_issues_document_severity", "issues", ["document_id", "severity"], unique=False
    )
    op.create_index(
        "ix_issues_document_page", "issues", ["document_id", "page_number"], unique=False
    )


def downgrade() -> None:
    """Drop issues table."""

    op.drop_index("ix_issues_document_page", table_name="issues")
    op.drop_index("ix_issues_document_severity", table_name="issues")
    op.drop_index("ix_issues_document_category", table_name="issues")
    op.drop_table("issues")
