"""Add BIMA identity metadata and allow SSO accounts without passwords."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260916_0013"
down_revision: str | Sequence[str] | None = "20260914_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bima_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(length=150), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=150), nullable=True))
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=True)
    op.create_index("ix_users_bima_id", "users", ["bima_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_bima_id", table_name="users")
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "position")
    op.drop_column("users", "department")
    op.drop_column("users", "bima_id")
