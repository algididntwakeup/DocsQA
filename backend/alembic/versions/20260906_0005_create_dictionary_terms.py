"""Create dictionary_terms table for engineering dictionary governance.

Revision ID: 20260906_0005
Revises: 20260905_0004
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_0005"
down_revision: str | Sequence[str] | None = "20260905_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dictionary_terms table and indexes."""
    op.create_table(
        "dictionary_terms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.String(length=1000), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dictionary_terms")),
    )
    op.create_index(
        op.f("ix_dictionary_terms_term"),
        "dictionary_terms",
        ["term"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dictionary_terms_scope"),
        "dictionary_terms",
        ["scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dictionary_terms_status"),
        "dictionary_terms",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_dictionary_terms_scope_status",
        "dictionary_terms",
        ["scope", "status"],
        unique=False,
    )
    op.create_index(
        "ix_dictionary_terms_scope_term",
        "dictionary_terms",
        ["scope", "term"],
        unique=True,
    )


def downgrade() -> None:
    """Drop dictionary_terms table and its indexes."""
    op.drop_index("ix_dictionary_terms_scope_term", table_name="dictionary_terms")
    op.drop_index("ix_dictionary_terms_scope_status", table_name="dictionary_terms")
    op.drop_index(op.f("ix_dictionary_terms_status"), table_name="dictionary_terms")
    op.drop_index(op.f("ix_dictionary_terms_scope"), table_name="dictionary_terms")
    op.drop_index(op.f("ix_dictionary_terms_term"), table_name="dictionary_terms")
    op.drop_table("dictionary_terms")
