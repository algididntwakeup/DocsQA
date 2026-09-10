"""Seed known local account credentials for authenticated Docker development."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0008"
down_revision: str | Sequence[str] | None = "20260910_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_ID = "00000000-0000-0000-0000-000000000003"
ADMIN_PASSWORD_HASH = "$2b$12$2BUtSZMA0fGW5tbOu65hE.KbaXNThfpdjmF1STRFLRyg/L6WQ4SXG"
ENGINEER_PASSWORD_HASH = "$2b$12$MnR2KgK8LGMOPffExPJXCeph5CT0BJrGCgM0zK3FKiiSLmP6TfXNO"


def upgrade() -> None:
    """Reset documented local credentials and add the local superuser."""
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("role", sa.String()),
    )
    op.execute(
        users.update()
        .where(users.c.email == "lead.engineer@localhost")
        .values(hashed_password=ADMIN_PASSWORD_HASH)
    )
    op.execute(
        users.update()
        .where(users.c.email == "engineer@localhost")
        .values(hashed_password=ENGINEER_PASSWORD_HASH)
    )
    connection = op.get_bind()
    if connection.execute(
        sa.select(users.c.id).where(users.c.email == "admin@localhost")
    ).scalar_one_or_none() is None:
        op.bulk_insert(
            users,
            [
                {
                    "id": ADMIN_ID,
                    "email": "admin@localhost",
                    "hashed_password": ADMIN_PASSWORD_HASH,
                    "full_name": "Local Superuser",
                    "role": "SUPERUSER",
                }
            ],
        )


def downgrade() -> None:
    """Remove the seeded superuser without changing existing account passwords."""
    users = sa.table("users", sa.column("id", sa.Uuid()))
    op.execute(users.delete().where(users.c.id == sa.literal(ADMIN_ID)))
