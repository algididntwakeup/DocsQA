"""Metadata checks for the first persistence migration."""

from sqlalchemy import Table

from db.base import Base
from models import Document, Issue, StageRun


def test_foundation_tables_are_registered() -> None:
    """Alembic metadata includes both M1.1 persistence aggregates."""

    assert set(Base.metadata.tables) == {"documents", "stage_runs", "issues"}
    assert Document.__tablename__ == "documents"
    assert StageRun.__tablename__ == "stage_runs"
    assert Issue.__tablename__ == "issues"


def test_stage_attempt_is_unique_per_document_and_stage() -> None:
    """Retries are appendable but cannot duplicate one attempt number."""

    table = StageRun.__table__
    assert isinstance(table, Table)
    constraint_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if hasattr(constraint, "columns")
    }

    assert ("document_id", "stage_name", "attempt") in constraint_columns
