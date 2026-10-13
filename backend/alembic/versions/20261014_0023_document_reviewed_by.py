"""Record who submitted a document's engineer review.

``reviewed_at`` already stored *when* a document was reviewed but not *who*
reviewed it, so the Document Control Log could not show a "Reviewed By"
column. This adds the missing actor alongside the existing timestamp.

Rows reviewed before this migration keep a NULL actor and surface as pending
in the UI; ``verified_by_id`` is deliberately untouched because it records the
lead's approval, which is a different step of the workflow.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261014_0023"
down_revision: str | Sequence[str] | None = "20261013_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("reviewed_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_documents_reviewed_by_id_users",
        "documents",
        "users",
        ["reviewed_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_reviewed_by_id_users", "documents", type_="foreignkey")
    op.drop_column("documents", "reviewed_by_id")
