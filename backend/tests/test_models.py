"""Metadata checks for persistence models."""

from sqlalchemy import Table

from db.base import Base
from models import DictionaryTerm, Document, Issue, Project, StageRun, User


def test_foundation_tables_are_registered() -> None:
    """Alembic metadata includes all active persistence tables."""

    assert set(Base.metadata.tables) == {
        "documents",
        "stage_runs",
        "issues",
        "dictionary_terms",
        "projects",
        "users",
    }
    assert Document.__tablename__ == "documents"
    assert StageRun.__tablename__ == "stage_runs"
    assert Issue.__tablename__ == "issues"
    assert DictionaryTerm.__tablename__ == "dictionary_terms"
    assert Project.__tablename__ == "projects"
    assert User.__tablename__ == "users"


def test_issue_has_curation_columns_and_no_legacy_columns() -> None:
    """Issue table includes included_in_report and reviewer_note, without legacy decision fields."""
    table = Issue.__table__
    column_names = {c.name for c in table.columns}
    assert "included_in_report" in column_names
    assert "reviewer_note" in column_names
    assert "decision" not in column_names
    assert "disposition" not in column_names
    assert "version" not in column_names


def test_document_has_no_review_status() -> None:
    """Document table has no review_status column."""
    table = Document.__table__
    column_names = {c.name for c in table.columns}
    assert "review_status" not in column_names


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
