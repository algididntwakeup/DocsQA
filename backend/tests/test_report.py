"""Unit tests for deterministic DOCX review report generator (services/report.py)."""

from __future__ import annotations

import io
from uuid import uuid4

import docx
import pytest

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


def _reference_rule_issue(
    doc: docx.types.Document | object,
    standard: str = "ASME BPVC.VIII.1",
) -> Issue:
    from uuid import UUID

    return Issue(
        id=uuid4(),
        document_id=UUID(int=0),
        category=IssueCategory.TRACEABILITY,
        type="REFERENCE_RULE",
        severity=Severity.HIGH,
        message="Hydrostatic test ratio below the mandatory UG-99(b) factor.",
        page_number=4,
        evidence={
            "kind": "REFERENCE_RULE",
            "standard": standard,
            "edition": "2021",
            "clause": "UG-99(b)",
            "standard_page": 76,
            "rule_kind": "numeric_limit",
            "detected_parameter": "Hydrostatic test pressure ratio",
            "detected_value": "1.15",
            "location": {
                "page_index": 3,
                "x0": 0.0,
                "y0": 0.0,
                "x1": 612.0,
                "y1": 792.0,
                "page_width": 612.0,
                "page_height": 792.0,
            },
        },
        included_in_report=True,
        reviewer_note=None,
    )


def test_standards_and_reference_checks_section() -> None:
    """New section renders sub-tables, columns, and per-standard metrics; DOCX stays valid."""
    document = Document(
        id=uuid4(),
        original_filename="VESSEL_SPEC.pdf",
        safe_filename="vessel_spec",
        status=DocumentStatus.COMPLETED,
    )
    governing = _reference_rule_issue(uuid4(), standard="ASME BPVC.VIII.1")
    company = _reference_rule_issue(uuid4(), standard="Company Spec CS-101 Addenda")
    company.evidence = dict(company.evidence, compliance_status="UNRESOLVED")

    docx_bytes = build_review_report(document, [governing, company])
    assert len(docx_bytes) > 0

    word_doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)
    assert "Standards and Reference Checks" in full_text

    all_table_text = "\n".join(
        " ".join(cell.text for cell in row.cells)
        for t in word_doc.tables
        for row in t.rows
    )
    assert "Governing Industry Standards" in full_text
    assert "Company Specifications & Addenda" in full_text
    assert "Standard Code" in all_table_text
    assert "Clause/Page Ref" in all_table_text
    assert "Finding/Condition" in all_table_text
    assert "Recommendation Template" in all_table_text
    assert "Evidence Text" in all_table_text

    # Column data and text-only standard locator
    assert "ASME BPVC.VIII.1" in all_table_text
    assert "Clause UG-99(b), p. 76" in all_table_text
    assert "document evidence on page 4" in all_table_text
    assert "1.15" in all_table_text

    # Per-standard summary metrics
    for t in word_doc.tables:
        headers = [c.text for c in t.rows[0].cells]
        if headers[:2] == ["Standard", "Total Checks"]:
            rows = {
                r.cells[0].text: [c.text for c in r.cells[1:]]
                for r in t.rows[1:]
            }
            assert rows["ASME BPVC.VIII.1"] == ["1", "1", "0"]
            assert rows["Company Spec CS-101 Addenda"] == ["1", "1", "1"]
            break
    else:
        pytest.fail("Per-standard summary table not found")


def test_report_rejects_invalid_bounding_boxes() -> None:
    """Evidence boxes outside the scanned page geometry are dropped, DOCX still valid."""
    document = Document(
        id=uuid4(),
        original_filename="BROKEN_BOX.pdf",
        safe_filename="broken_box",
        status=DocumentStatus.COMPLETED,
    )
    bad = _reference_rule_issue(uuid4())
    bad.evidence = dict(
        bad.evidence,
        location={
            "page_index": 0,
            "x0": -5.0,
            "y0": 0.0,
            "x1": 9999.0,
            "y1": 792.0,
            "page_width": 612.0,
            "page_height": 792.0,
        },
    )

    docx_bytes = build_review_report(document, [bad])
    assert len(docx_bytes) > 0

    word_doc = docx.Document(io.BytesIO(docx_bytes))
    all_table_text = "\n".join(
        " ".join(cell.text for cell in row.cells)
        for t in word_doc.tables
        for row in t.rows
    )
    assert "document evidence on page" not in all_table_text
    assert "Clause UG-99(b), p. 76" in all_table_text
