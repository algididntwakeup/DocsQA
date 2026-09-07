"""Unit and contract tests for GET /api/v1/documents/{document_id}/issues (M2.5)."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from db.session import get_session
from domain.enums import DocumentStatus, IssueCategory, Severity
from main import app
from models.document import Document
from models.issue import Issue
from schemas.issues import BoundingBox, TableMathEvidence

client = TestClient(app)


def test_list_document_issues_404_when_document_missing() -> None:
    """Non-existent document id returns 404 Not Found."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get(f"/api/v1/documents/{uuid4()}/issues")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_list_document_issues_empty_list() -> None:
    """Existing document with no issues returns empty collection and zeroed counts."""
    doc_id = uuid4()
    mock_doc = Document(id=doc_id, original_filename="doc.pdf", status=DocumentStatus.COMPLETED)

    mock_session = AsyncMock()

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    counts_result = MagicMock()
    counts_result.all.return_value = []

    total_result = MagicMock()
    total_result.scalar_one.return_value = 0

    issues_result = MagicMock()
    issues_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        doc_result,
        counts_result,
        total_result,
        issues_result,
    ]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get(f"/api/v1/documents/{doc_id}/issues")
        assert response.status_code == 200
        data = response.json()
        assert data["issues"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        assert data["counts_by_severity"] == {s.value: 0 for s in Severity}
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_list_document_issues_with_populated_issues() -> None:
    """Document issues are serialized with typed evidence, pagination, and counts."""
    doc_id = uuid4()
    issue_id = uuid4()
    now = datetime.now(UTC)

    mock_doc = Document(id=doc_id, original_filename="calc.pdf", status=DocumentStatus.COMPLETED)
    evidence_payload = TableMathEvidence(
        extractor_version="1.0",
        rule_version="table-math/1.0.0",
        computed_value=Decimal("95"),
        stated_value=Decimal("100"),
        delta=Decimal("5"),
        tolerance=Decimal("0.5"),
        total_location=BoundingBox(
            page_index=0,
            x0=10.0,
            y0=20.0,
            x1=50.0,
            y1=30.0,
            page_width=612.0,
            page_height=792.0,
        ),
        operand_locations=[],
    ).model_dump(mode="json")

    mock_issue = Issue(
        id=issue_id,
        document_id=doc_id,
        category=IssueCategory.TRACEABILITY,
        type="TABLE_MATH_MISMATCH",
        severity=Severity.CRITICAL,
        confidence=1.0,
        message="Table column calculation mismatch",
        page_number=1,
        evidence=evidence_payload,
        included_in_report=True,
        reviewer_note=None,
        created_at=now,
        updated_at=now,
    )

    mock_session = AsyncMock()

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    counts_result = MagicMock()
    counts_result.all.return_value = [(Severity.CRITICAL, 1)]

    total_result = MagicMock()
    total_result.scalar_one.return_value = 1

    issues_result = MagicMock()
    issues_result.scalars.return_value.all.return_value = [mock_issue]

    mock_session.execute.side_effect = [
        doc_result,
        counts_result,
        total_result,
        issues_result,
    ]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        url = f"/api/v1/documents/{doc_id}/issues?category=TRACEABILITY&page=1&page_size=10"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        assert data["pagination"]["total"] == 1
        assert data["counts_by_severity"]["CRITICAL"] == 1
        item = data["issues"][0]
        assert item["id"] == str(issue_id)
        assert item["category"] == "TRACEABILITY"
        assert item["type"] == "TABLE_MATH_MISMATCH"
        assert item["severity"] == "CRITICAL"
        assert item["evidence"]["kind"] == "TABLE_MATH"
        assert item["evidence"]["computed_value"] == "95"
        assert item["evidence"]["stated_value"] == "100"
    finally:
        app.dependency_overrides.pop(get_session, None)
