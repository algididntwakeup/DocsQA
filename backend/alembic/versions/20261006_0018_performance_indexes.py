"""Add indexes for document and project filters."""

from collections.abc import Sequence

from alembic import op

revision: str = "20261006_0018"
down_revision: str | Sequence[str] | None = "20261002_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_workflow_status", "documents", ["workflow_status"])
    op.create_index("ix_projects_created_by_id", "projects", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_projects_created_by_id", table_name="projects")
    op.drop_index("ix_documents_workflow_status", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
