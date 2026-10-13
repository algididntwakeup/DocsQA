"""Add the local ``users.is_superuser`` privilege flag.

BIMA only exposes a flat project directory and has no notion of
cross-department oversight, so PRISM grants workspace-wide visibility with a
local flag instead of overloading ``users.role`` (which mirrors the BIMA role).
Existing rows default to ``false``; accounts listed in ``SUPERUSER_EMAILS`` are
promoted by the backfill below and re-promoted on every sign-in.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013_0022"
down_revision: str | Sequence[str] | None = "20261013_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Keep in sync with ``core.config.Settings.SUPERUSER_EMAILS``.
PROMOTED_EMAILS = ("m.alghifari@reksolindo.co.id",)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE users SET is_superuser = true WHERE lower(email) IN :emails"
        ).bindparams(sa.bindparam("emails", value=PROMOTED_EMAILS, expanding=True))
    )


def downgrade() -> None:
    op.drop_column("users", "is_superuser")
