"""Unit tests for deterministic DOCX review report generator (services/report.py)."""

from __future__ import annotations

import io
from uuid import uuid4

import docx

from domain.enums import DocumentStatus, IssueCategory, Severity
from models.document import Document
from models.issue import Issue
from services.report import build_review_report


def test_build_review_report_empty_findings() -> None:
    """DOCX report generates cleanly when there are zero included findings."""
    doc = Document(
        id=uuid4(),
        original_filename="CLEAN_DOC.pdf",
        safe_filename="clean_doc",
        status=DocumentStatus.COMPLETED,
    )
    docx_bytes = build_review_report(doc, [])
    assert len(docx_bytes) > 0

    word_doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)
    assert "DOCUMENT REVIEW ENGINEERING" in full_text
    assert "CLEAN_DOC.pdf" in full_text
    assert "0 findings" in full_text
    assert "No included findings in this section." in full_text


def test_build_review_report_full_composition() -> None:
    """DOCX report categorizes blockers, other findings, and language findings."""
    doc = uuid4()
    document = Document(
        id=doc,
        original_filename="VESSEL_CALC.pdf",
        safe_filename="vessel_calc",
        status=DocumentStatus.COMPLETED,
    )

    issue_blocker = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.TRACEABILITY,
        type="TABLE_MATH_MISMATCH",
        severity=Severity.CRITICAL,
        message="Total 1500 != computed 1600",
        page_number=3,
        evidence={"suggestion": "Adjust row 4 to match sum"},
        included_in_report=True,
        reviewer_note="Confirmed with senior pressure vessel engineer.",
    )

    issue_other = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.TRACEABILITY,
        type="REFERENCE_DRIFT",
        severity=Severity.MEDIUM,
        message="Section 3.2 references Appendix B which was moved to Appendix C",
        page_number=12,
        evidence={},
        included_in_report=True,
        reviewer_note=None,
    )

    issue_lang = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.LINGUISTIC,
        type="SPELLING_ERROR",
        severity=Severity.LOW,
        message="Typo 'tempature'",
        page_number=5,
        evidence={"suggestion": "temperature"},
        included_in_report=True,
        reviewer_note="Reviewer approved typo fix.",
    )

    issue_excluded = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.LINGUISTIC,
        type="AMBIGUITY",
        severity=Severity.INFO,
        message="Ambiguous phrasing",
        page_number=8,
        evidence={},
        included_in_report=False,
        reviewer_note="Not relevant for this rev",
    )

    docx_bytes = build_review_report(
        document,
        [issue_blocker, issue_other, issue_lang, issue_excluded],
    )
    assert len(docx_bytes) > 0

    word_doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)

    assert "VESSEL_CALC.pdf" in full_text
    assert "TABLE_MATH_MISMATCH - page 3" in full_text
    assert "Confirmed with senior pressure vessel engineer." in full_text
    assert "Adjust row 4 to match sum" in full_text

    assert "REFERENCE_DRIFT - page 12" in full_text
    assert "Verify this statement against the cited source" in full_text

    assert "SPELLING_ERROR - page 5" in full_text
    assert "temperature" in full_text

    # Excluded finding must NOT be present
    assert "Ambiguous phrasing" not in full_text

    # Verify scorecard table
    table = word_doc.tables[0]
    data = {row.cells[0].text: row.cells[1].text for row in table.rows[1:]}
    assert data["Included findings"] == "3"
    assert data["Blockers"] == "1"
    assert data["Language and mechanics"] == "1"
    assert data["Other consistency findings"] == "1"
