"""Unit and contract tests for report curation and report preview endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from db.session import get_session
from domain.enums import DocumentStatus, IssueCategory, Severity
from main import app
from models.document import Document
from models.issue import Issue
from schemas.issues import BoundingBox, LinguisticEvidence

client = TestClient(app)


def _make_dummy_issue(
    issue_id: UUID,
    doc_id: UUID,
    category: IssueCategory = IssueCategory.LINGUISTIC,
    severity: Severity = Severity.MEDIUM,
    included_in_report: bool = True,
    reviewer_note: str | None = None,
) -> Issue:
    now = datetime.now(UTC)
    return Issue(
        id=issue_id,
        document_id=doc_id,
        category=category,
        type="SPELLING_ERROR" if category == IssueCategory.LINGUISTIC else "TABLE_MATH_MISMATCH",
        severity=severity,
        confidence=0.95,
        message="Typo in domain word",
        page_number=1,
        evidence=LinguisticEvidence(
            extractor_version="1.0",
            rule_version="spell/1.0.0",
            original_text="austentic",
            suggestion="austenitic",
            location=BoundingBox(
                page_index=0,
                x0=10.0,
                y0=10.0,
                x1=40.0,
                y1=20.0,
                page_width=612.0,
                page_height=792.0,
            ),
        ).model_dump(mode="json"),
        included_in_report=included_in_report,
        reviewer_note=reviewer_note,
        created_at=now,
        updated_at=now,
    )


def test_curate_issue_include_and_exclude() -> None:
    """Reviewer can toggle included_in_report and update reviewer_note."""
    doc_id = uuid4()
    issue_id = uuid4()
    issue = _make_dummy_issue(issue_id, doc_id, included_in_report=True)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = issue
    mock_session.execute.return_value = mock_result

    async def _mock_refresh(obj: Any) -> None:
        pass

    mock_session.refresh.side_effect = _mock_refresh

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        # 1. Exclude finding
        res1 = client.patch(
            f"/api/v1/issues/{issue_id}/curation",
            json={
                "included_in_report": False,
                "reviewer_note": "False positive: project-specific abbreviation.",
            },
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["included_in_report"] is False
        assert data1["reviewer_note"] == "False positive: project-specific abbreviation."
        assert issue.included_in_report is False
        assert issue.reviewer_note == "False positive: project-specific abbreviation."

        # 2. Re-include finding
        res2 = client.patch(
            f"/api/v1/issues/{issue_id}/curation",
            json={
                "included_in_report": True,
                "reviewer_note": "Re-included after engineering consultation.",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["included_in_report"] is True
        assert data2["reviewer_note"] == "Re-included after engineering consultation."
        assert issue.included_in_report is True
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_curate_issue_not_found() -> None:
    """Attempting to curate a non-existent issue returns 404."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        res = client.patch(
            f"/api/v1/issues/{uuid4()}/curation",
            json={"included_in_report": False},
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "Issue not found."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_curate_issue_validation_error() -> None:
    """Invalid payload triggers 422 validation error."""
    res = client.patch(
        f"/api/v1/issues/{uuid4()}/curation",
        json={"reviewer_note": "missing included_in_report"},
    )
    assert res.status_code == 422


def test_get_report_preview_with_blockers() -> None:
    """Report preview reflects included findings and blocker calculation."""
    doc_id = uuid4()
    doc = Document(id=doc_id, original_filename="spec.pdf", status=DocumentStatus.COMPLETED)
    issue1 = _make_dummy_issue(uuid4(), doc_id, severity=Severity.CRITICAL, included_in_report=True)
    issue2 = _make_dummy_issue(uuid4(), doc_id, severity=Severity.LOW, included_in_report=True)

    mock_session = AsyncMock()
    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = doc

    issues_res = MagicMock()
    issues_res.scalars.return_value.all.return_value = [issue1, issue2]

    mock_session.execute.side_effect = [doc_res, issues_res]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        res = client.get(f"/api/v1/documents/{doc_id}/report")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == str(doc_id)
        assert data["included_findings"] == 2
        assert data["blockers"] == 1
        assert data["summary_judgement"] == "Blockers require correction before reissue."
        assert data["counts_by_severity"]["CRITICAL"] == 1
        assert data["counts_by_severity"]["LOW"] == 1
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_get_report_preview_no_blockers() -> None:
    """Report preview with only low/medium findings indicates no blockers."""
    doc_id = uuid4()
    doc = Document(id=doc_id, original_filename="clean.pdf", status=DocumentStatus.COMPLETED)
    issue = _make_dummy_issue(uuid4(), doc_id, severity=Severity.LOW, included_in_report=True)

    mock_session = AsyncMock()
    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = doc

    issues_res = MagicMock()
    issues_res.scalars.return_value.all.return_value = [issue]

    mock_session.execute.side_effect = [doc_res, issues_res]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        res = client.get(f"/api/v1/documents/{doc_id}/report")
        assert res.status_code == 200
        data = res.json()
        assert data["included_findings"] == 1
        assert data["blockers"] == 0
        assert data["summary_judgement"] == "No blocker findings are included in the draft report."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_get_report_preview_document_not_found() -> None:
    """Report preview returns 404 when document does not exist."""
    mock_session = AsyncMock()
    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = doc_res

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        res = client.get(f"/api/v1/documents/{uuid4()}/report")
        assert res.status_code == 404
        assert res.json()["detail"] == "Document not found."
    finally:
        app.dependency_overrides.pop(get_session, None)
