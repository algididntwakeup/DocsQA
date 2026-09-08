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
from schemas.issues import (
    BoundingBox,
    BudinskiEvidence,
    LayoutEvidence,
    LinguisticEvidence,
    TableMathEvidence,
)

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


def test_list_document_issues_layout_category_and_blocker_severity() -> None:
    """Document issues with LAYOUT category and BLOCKER severity are serialized properly."""
    doc_id = uuid4()
    issue_id = uuid4()
    now = datetime.now(UTC)

    mock_doc = Document(
        id=doc_id,
        original_filename="ale_report.pdf",
        status=DocumentStatus.COMPLETED,
    )
    evidence_payload = LayoutEvidence(
        extractor_version="1.0",
        rule_version="layout/1.0",
        anomaly_type="CROSS_PAGE_SENTENCE_BREAK",
        page_index=20,
        bounding_box=BoundingBox(
            page_index=20,
            x0=0.0,
            y0=0.0,
            x1=612.0,
            y1=792.0,
            page_width=612.0,
            page_height=792.0,
        ),
        snippet="Table 6-3 and",
        suggested_fix="Ensure sentence flows continuously without page-boundary cutoffs.",
    ).model_dump(mode="json")

    mock_issue = Issue(
        id=issue_id,
        document_id=doc_id,
        category="LAYOUT",
        type="CROSS_PAGE_SENTENCE_BREAK",
        severity="BLOCKER",
        confidence=0.95,
        message="Cross-page sentence break detected",
        page_number=21,
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
    counts_result.all.return_value = [(Severity.BLOCKER, 1)]

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
        url = f"/api/v1/documents/{doc_id}/issues?category=LAYOUT&page=1&page_size=10"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        assert data["pagination"]["total"] == 1
        assert data["counts_by_severity"]["BLOCKER"] == 1
        item = data["issues"][0]
        assert item["id"] == str(issue_id)
        assert item["category"] == "LAYOUT"
        assert item["type"] == "CROSS_PAGE_SENTENCE_BREAK"
        assert item["severity"] == "BLOCKER"
        assert item["evidence"]["kind"] == "LAYOUT"
        assert item["evidence"]["anomaly_type"] == "CROSS_PAGE_SENTENCE_BREAK"
        assert item["evidence"]["snippet"] == "Table 6-3 and"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_list_document_issues_budinski_category() -> None:
    """Document issues with BUDINSKI category and evidence serialize correctly."""
    doc_id = uuid4()
    issue_id = uuid4()
    now = datetime.now(UTC)

    mock_doc = Document(
        id=doc_id,
        original_filename="ale_report.pdf",
        status=DocumentStatus.COMPLETED,
    )
    evidence_payload = BudinskiEvidence(
        extractor_version="1.0",
        rule_version="budinski/1.0",
        rule_number="12.1",
        measure="conclusions_valid",
        where_location="Section 8 Conclusion",
        what_it_says="Criticality 2 defined as 0-6 years",
        what_body_has="Section 6.2 states Criticality 2 is 6-14 years",
        why_it_matters="Contradictory remaining life definitions across report sections",
        what_would_fix_it="Align Section 8 conclusions with Section 6 criteria",
    ).model_dump(mode="json")

    mock_issue = Issue(
        id=issue_id,
        document_id=doc_id,
        category="BUDINSKI",
        type="BUDINSKI_REWORK",
        severity="MAJOR",
        confidence=1.0,
        message="Contradictory criticality definitions",
        page_number=28,
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
    counts_result.all.return_value = [(Severity.MAJOR, 1)]

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
        url = f"/api/v1/documents/{doc_id}/issues?category=BUDINSKI"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        assert data["counts_by_severity"]["MAJOR"] == 1
        item = data["issues"][0]
        assert item["category"] == "BUDINSKI"
        assert item["severity"] == "MAJOR"
        assert item["evidence"]["kind"] == "BUDINSKI"
        assert item["evidence"]["rule_number"] == "12.1"
        assert item["evidence"]["what_it_says"] == "Criticality 2 defined as 0-6 years"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_backward_compatibility_issue_payload() -> None:
    """Legacy categories and severities remain valid and counts_by_severity includes all tiers."""
    doc_id = uuid4()
    now = datetime.now(UTC)

    mock_doc = Document(id=doc_id, original_filename="legacy.pdf", status=DocumentStatus.COMPLETED)
    legacy_issue = Issue(
        id=uuid4(),
        document_id=doc_id,
        category=IssueCategory.LINGUISTIC,
        type="SPELLCHECK_TYPO",
        severity=Severity.LOW,
        confidence=0.8,
        message="Spelling typo",
        page_number=2,
        evidence=LinguisticEvidence(
            extractor_version="1.0",
            rule_version="spell/1.0",
            original_text="teh",
            suggestion="the",
            location=BoundingBox(
                page_index=1,
                x0=10.0,
                y0=20.0,
                x1=50.0,
                y1=30.0,
                page_width=612.0,
                page_height=792.0,
            ),
        ).model_dump(mode="json"),
        included_in_report=True,
        reviewer_note=None,
        created_at=now,
        updated_at=now,
    )

    mock_session = AsyncMock()
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    counts_result = MagicMock()
    counts_result.all.return_value = [(Severity.LOW, 1)]

    total_result = MagicMock()
    total_result.scalar_one.return_value = 1

    issues_result = MagicMock()
    issues_result.scalars.return_value.all.return_value = [legacy_issue]

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
        url = f"/api/v1/documents/{doc_id}/issues"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        item = data["issues"][0]
        assert item["category"] == "LINGUISTIC"
        assert item["severity"] == "LOW"
        # Verify counts_by_severity has keys for all canonical and alias severities
        for sev in Severity:
            assert sev.value in data["counts_by_severity"]
        assert data["counts_by_severity"]["LOW"] == 1
    finally:
        app.dependency_overrides.pop(get_session, None)

