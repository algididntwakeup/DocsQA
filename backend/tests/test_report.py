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
    assert "Blockers" in full_text
    assert "Next revision findings" in full_text


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
    all_table_text = "\n".join(
        " ".join(cell.text for cell in row.cells)
        for table in word_doc.tables
        for row in table.rows
    )
    assert "TABLE_MATH_MISMATCH" in all_table_text
    assert "Confirmed with senior pressure vessel engineer." in all_table_text
    assert "Adjust row 4 to match sum" in all_table_text
    assert "REFERENCE_DRIFT" in all_table_text
    assert "SPELLING_ERROR" in all_table_text
    assert "temperature" in all_table_text

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
    doc: object = None,
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


def test_reference_findings_are_compact() -> None:
    """Reference findings stay in the compact action table."""
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
    assert "Blockers" in full_text
    assert "Next revision findings" in full_text

    all_table_text = "\n".join(
        " ".join(cell.text for cell in row.cells)
        for t in word_doc.tables
        for row in t.rows
    )
    assert "Governing Industry Standards" not in full_text

    # Column data and text-only standard locator
    assert "ASME BPVC.VIII.1" in all_table_text
    assert "Clause UG-99(b), standard page 76" in all_table_text
    assert "document page 4" in all_table_text
    assert "1.15" in all_table_text

    assert "ASME BPVC.VIII.1" in all_table_text
    assert "Company Spec CS-101 Addenda" in all_table_text


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
    assert "Clause UG-99(b), standard page 76" in all_table_text


def test_report_orders_severity_and_uses_printed_reference_labels() -> None:
    """Compact findings are ordered by severity, not PDF page sequence."""
    document = Document(
        id=uuid4(),
        original_filename="PAGINATED_REPORT.pdf",
        safe_filename="paginated_report",
        status=DocumentStatus.COMPLETED,
    )
    low = Issue(
        id=uuid4(),
        document_id=document.id,
        category=IssueCategory.LINGUISTIC,
        type="DICTIONARY_TERM",
        severity=Severity.LOW,
        message="Term should be checked",
        page_number=1,
        evidence={
            "kind": "LINGUISTIC",
            "original_text": "term",
            "location": {"page_index": 0, "x0": 1, "y0": 1, "x1": 2, "y1": 2},
        },
        included_in_report=True,
    )
    high = Issue(
        id=uuid4(),
        document_id=document.id,
        category=IssueCategory.TRACEABILITY,
        type="REFERENCE_DRIFT",
        severity=Severity.HIGH,
        message="TOC target does not match",
        page_number=99,
        evidence={
            "kind": "REFERENCE_DRIFT",
            "label": "Section 4",
            "referenced_page_label": "21",
            "actual_page_label": "23",
            "what_it_says": "Section 4",
        },
        included_in_report=True,
    )

    word_doc = docx.Document(io.BytesIO(build_review_report(document, [low, high])))
    findings_tables = [
        table for table in word_doc.tables if table.rows[0].cells[0].text == "Severity"
    ]
    blocker_rows = [[cell.text for cell in row.cells] for row in findings_tables[0].rows[1:]]
    next_rows = [[cell.text for cell in row.cells] for row in findings_tables[1].rows[1:]]
    assert blocker_rows[0][0] == "HIGH"
    assert "printed pages 21" in blocker_rows[0][2]
    assert next_rows[0][0] == "LOW"
