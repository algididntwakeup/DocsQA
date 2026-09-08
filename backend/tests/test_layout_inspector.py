"""
Unit tests for DocumentLayoutInspector (layout, typography, and page-continuity diagnostics).
"""

from pathlib import Path

import fitz  # type: ignore[import-untyped]
import pytest

from schemas.extraction import (
    CoordinateContract,
    PageBlock,
    PageMetric,
    PDFPage,
)
from services.layout_inspector import DocumentLayoutInspector

TESTCASE_DIR = Path(__file__).parent.parent.parent / "docs" / "testcase"
MEPG_PDF = TESTCASE_DIR / "05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf"


@pytest.fixture
def inspector() -> DocumentLayoutInspector:
    return DocumentLayoutInspector()


# ── 1. Cross-Page Sentence Breaks Tests ──────────────────────────────────────


def test_cross_page_sentence_break_conjunction(inspector: DocumentLayoutInspector) -> None:
    """Test detection when page N ends with a conjunction like 'and' and continues to page N+1."""
    blocks = [
        PageBlock(
            page_index=0,
            text="Asset Life Extension Study for Grissik Plant",
            bbox=CoordinateContract(
                page_index=0, x0=50, y0=30, x1=300, y1=50, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=0,
            text="equipment level are shown in Table 6-3 and",
            bbox=CoordinateContract(
                page_index=0, x0=50, y0=700, x1=500, y1=720, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=0,
            text="Page 20 of 34",
            bbox=CoordinateContract(
                page_index=0, x0=250, y0=760, x1=350, y1=780, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=1,
            text="Asset Life Extension Study for Grissik Plant",
            bbox=CoordinateContract(
                page_index=1, x0=50, y0=30, x1=300, y1=50, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=1,
            text="Table 6-4, at component level Table 6-3 shows that 25 out of 27 components.",
            bbox=CoordinateContract(
                page_index=1, x0=50, y0=80, x1=550, y1=100, page_width=600, page_height=800
            ),
        ),
    ]

    anomalies = inspector.detect_cross_page_sentence_breaks(blocks)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "CROSS_PAGE_BREAK"
    assert anomaly.page_index == 0
    assert anomaly.details["next_page_index"] == 1
    assert "and" in anomaly.details["reason"]
    assert "Table 6-3 and" in anomaly.details["last_text"]


def test_cross_page_sentence_break_comma(inspector: DocumentLayoutInspector) -> None:
    """Test detection when page N ends with a dangling comma."""
    blocks = [
        PageBlock(
            page_index=2,
            text="The evaluation indicates that the remaining life is acceptable,",
            bbox=CoordinateContract(
                page_index=2, x0=50, y0=700, x1=500, y1=720, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=3,
            text="provided that the periodic inspections continue as scheduled.",
            bbox=CoordinateContract(
                page_index=3, x0=50, y0=80, x1=500, y1=100, page_width=600, page_height=800
            ),
        ),
    ]

    anomalies = inspector.detect_cross_page_sentence_breaks(blocks)
    assert len(anomalies) == 1
    assert anomalies[0].page_index == 2
    assert "comma" in anomalies[0].details["reason"]


def test_cross_page_proper_terminal_punctuation_no_anomaly(
    inspector: DocumentLayoutInspector,
) -> None:
    """Test that pages ending with proper terminal punctuation (.!?:) do not trigger anomalies."""
    blocks = [
        PageBlock(
            page_index=0,
            text="All components met the ASME Section VIII requirements.",
            bbox=CoordinateContract(
                page_index=0, x0=50, y0=700, x1=500, y1=720, page_width=600, page_height=800
            ),
        ),
        PageBlock(
            page_index=1,
            text="Section 7 outlines the recommended mitigation strategy.",
            bbox=CoordinateContract(
                page_index=1, x0=50, y0=80, x1=500, y1=100, page_width=600, page_height=800
            ),
        ),
    ]

    anomalies = inspector.detect_cross_page_sentence_breaks(blocks)
    assert len(anomalies) == 0


def test_cross_page_single_page_returns_empty(inspector: DocumentLayoutInspector) -> None:
    """Single-page document should not trigger cross-page breaks."""
    blocks = [
        PageBlock(page_index=0, text="This is a sentence that ends abruptly and"),
    ]
    assert inspector.detect_cross_page_sentence_breaks(blocks) == []


# ── 2. Style Misclassification Tests ─────────────────────────────────────────


def test_style_misclassification_narrative_bold(inspector: DocumentLayoutInspector) -> None:
    """Detect narrative sentences ('Based on...') misclassified with bold styling."""
    blocks = [
        PageBlock(
            page_index=4,
            text="Based on Figure 6-1, the high-risk category without inspection is critical.",
            is_bold=True,
            is_heading=False,
            font_name="Arial-BoldMT",
        )
    ]

    anomalies = inspector.detect_style_misclassification(blocks)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "STYLE_MISCLASSIFICATION"
    assert anomaly.page_index == 4
    assert "bold font attribute" in anomaly.details["reasons"]


def test_style_misclassification_narrative_outline_heading(
    inspector: DocumentLayoutInspector,
) -> None:
    """Detect narrative sentences ('Referring to...') misclassified as heading/outline."""
    blocks = [
        PageBlock(
            page_index=5,
            text="Referring to the engineering datasheet, the wall thickness is 12.5 mm.",
            is_bold=False,
            is_heading=True,
            is_outline=True,
        )
    ]

    anomalies = inspector.detect_style_misclassification(blocks)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "STYLE_MISCLASSIFICATION"
    assert "heading classification" in anomaly.details["reasons"]
    assert "outline header" in anomaly.details["reasons"]


def test_style_misclassification_valid_cases_no_anomaly(
    inspector: DocumentLayoutInspector,
) -> None:
    """Legitimate section headings and unstyled narrative body text should not trigger anomalies."""
    blocks = [
        # Legitimate heading (not narrative phrase)
        PageBlock(
            page_index=2,
            text="6.0 STATIC EQUIPMENT ASSESSMENT",
            is_bold=True,
            is_heading=True,
        ),
        # Normal body text (starts with narrative phrase, but normal regular font)
        PageBlock(
            page_index=2,
            text="Based on the field inspection results, no significant degradation was observed.",
            is_bold=False,
            is_heading=False,
            font_name="ArialMT",
        ),
    ]

    anomalies = inspector.detect_style_misclassification(blocks)
    assert len(anomalies) == 0


# ── 3. Unintended Whitespace Tests ───────────────────────────────────────────


def test_unintended_whitespace_middle_page_detected(inspector: DocumentLayoutInspector) -> None:
    """Detect a largely blank page (< 25% utilization) in the middle of a document."""
    metrics = [
        PageMetric(page_index=0, text_utilization_ratio=0.75),  # cover/front page
        PageMetric(page_index=1, text_utilization_ratio=0.60),  # normal content
        PageMetric(page_index=2, text_utilization_ratio=0.12),  # void / blank page before section
        PageMetric(page_index=3, text_utilization_ratio=0.70),  # next section
    ]

    anomalies = inspector.detect_unintended_whitespace(metrics)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "UNINTENDED_WHITESPACE"
    assert anomaly.page_index == 2
    assert anomaly.details["text_utilization_ratio"] == 0.12
    assert anomaly.severity == "HIGH"


def test_unintended_whitespace_percentage_format_handled(
    inspector: DocumentLayoutInspector,
) -> None:
    """Handles text_utilization_ratio expressed as percentage (e.g., 15.0% instead of 0.15)."""
    metrics = [
        PageMetric(page_index=0, text_utilization_ratio=80.0),
        PageMetric(page_index=1, text_utilization_ratio=15.0),  # 15% < 25%
        PageMetric(page_index=2, text_utilization_ratio=85.0),
    ]

    anomalies = inspector.detect_unintended_whitespace(metrics)
    assert len(anomalies) == 1
    assert anomalies[0].page_index == 1
    assert anomalies[0].details["text_utilization_ratio"] == 0.15


def test_unintended_whitespace_first_and_last_pages_ignored(
    inspector: DocumentLayoutInspector,
) -> None:
    """
    First (cover) and last (back cover) pages are intentionally sparse and must not be flagged.
    """
    metrics = [
        PageMetric(page_index=0, text_utilization_ratio=0.10),  # Cover page
        PageMetric(page_index=1, text_utilization_ratio=0.65),
        PageMetric(page_index=2, text_utilization_ratio=0.08),  # Back cover
    ]

    anomalies = inspector.detect_unintended_whitespace(metrics)
    assert len(anomalies) == 0


def test_unintended_whitespace_short_document_no_middle_pages(
    inspector: DocumentLayoutInspector,
) -> None:
    """Documents with 2 or fewer pages have no middle pages and should return empty."""
    metrics = [
        PageMetric(page_index=0, text_utilization_ratio=0.05),
        PageMetric(page_index=1, text_utilization_ratio=0.05),
    ]
    assert inspector.detect_unintended_whitespace(metrics) == []


# ── 4. Uncontrolled Pages Audit Tests ────────────────────────────────────────


def test_audit_uncontrolled_pages_missing_elements(inspector: DocumentLayoutInspector) -> None:
    """Detect pages missing running header, footer, page number, or document number."""
    pages = [
        # Fully controlled portrait page
        PDFPage(
            page_index=0,
            width=595.0,
            height=842.0,
            orientation="portrait",
            has_header=True,
            has_footer=True,
            has_page_number=True,
            has_doc_number=True,
        ),
        # Landscape page missing doc number and footer
        PDFPage(
            page_index=1,
            width=842.0,
            height=595.0,
            orientation="landscape",
            has_header=True,
            has_footer=False,
            has_page_number=True,
            has_doc_number=False,
        ),
    ]

    anomalies = inspector.audit_uncontrolled_pages(pages)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "UNCONTROLLED_PAGE"
    assert anomaly.page_index == 1
    assert anomaly.details["orientation"] == "landscape"
    assert "running_footer" in anomaly.details["missing_elements"]
    assert "document_number" in anomaly.details["missing_elements"]


def test_audit_uncontrolled_pages_all_controlled_passes(
    inspector: DocumentLayoutInspector,
) -> None:
    """All controlled pages pass without anomalies."""
    pages = [
        PDFPage(
            page_index=0,
            width=600.0,
            height=800.0,
            orientation="portrait",
            header_text="Project Alpha Assessment Report",
            footer_text="Confidential - Internal Use Only",
            page_number="Page 1 of 10",
            doc_number="DOC-ENG-2026-001",
        )
    ]

    anomalies = inspector.audit_uncontrolled_pages(pages)
    assert len(anomalies) == 0


# ── 5. Front Matter Navigation Drift Tests ───────────────────────────────────


def test_validate_front_matter_navigation_drift_detected(
    inspector: DocumentLayoutInspector,
) -> None:
    """Detect drift between ToC/LoT/LoF listed page and actual physical position."""
    toc_entries = [
        {"title": "Table 6-3 RUL static component summary", "referenced_page": 20},
        {"title": "Table 6-4 RUL static equipment summary", "referenced_page": 22},
        {"title": "Section 4 Methodology", "referenced_page": 10},
    ]
    actual_positions = {
        "Table 6-3 RUL static component summary": 22,  # Drifted by +2 pages
        "Table 6-4 RUL static equipment summary": 22,  # Matched
        "Section 4 Methodology": {"page": 12},  # Drifted by +2 pages
    }

    anomalies = inspector.validate_front_matter_navigation(toc_entries, actual_positions)
    assert len(anomalies) == 2

    # First drift: Table 6-3
    assert anomalies[0].anomaly_type == "FRONT_MATTER_DRIFT"
    assert anomalies[0].details["referenced_page"] == 20
    assert anomalies[0].details["actual_page"] == 22
    assert anomalies[0].details["drift"] == 2

    # Second drift: Section 4
    assert anomalies[1].details["referenced_page"] == 10
    assert anomalies[1].details["actual_page"] == 12
    assert anomalies[1].details["drift"] == 2


def test_validate_front_matter_navigation_match_passes(
    inspector: DocumentLayoutInspector,
) -> None:
    """Matching ToC entries and actual positions produce no anomalies."""
    toc_entries = [
        {"title": "Executive Summary", "page": 1},
        {"title": "Scope of Work", "page": 3},
    ]
    actual_positions = {
        "Executive Summary": 1,
        "Scope of Work": 3,
    }

    anomalies = inspector.validate_front_matter_navigation(toc_entries, actual_positions)
    assert len(anomalies) == 0


# ── 6. PyMuPDF (fitz) Synthetic Integration Tests ────────────────────────────


def test_fitz_integration_synthetic_pdf(inspector: DocumentLayoutInspector) -> None:
    """
    Construct an in-memory PDF using PyMuPDF (fitz), extract blocks and metrics,
    and verify diagnostics end-to-end.
    """
    doc = fitz.open()

    # Page 0: Normal page with bold narrative text (style misclassification)
    p0 = doc.new_page(width=600, height=800)
    p0.insert_text(fitz.Point(50, 40), "ID-N-CG-MM1-DSR-PL-00-3001", fontname="helv", fontsize=9)
    p0.insert_text(
        fitz.Point(50, 100),
        "Based on the analysis, static equipment life is acceptable.",
        fontname="helv",
        fontsize=14,  # bold-like heading size
    )
    p0.insert_text(fitz.Point(50, 760), "Page 1 of 3", fontname="helv", fontsize=9)

    # Page 1: Void / largely blank middle page (< 25% utilization)
    p1 = doc.new_page(width=600, height=800)
    p1.insert_text(fitz.Point(50, 400), "Intentional section divider note.", fontsize=10)

    # Page 2: End page
    p2 = doc.new_page(width=600, height=800)
    p2.insert_text(fitz.Point(50, 100), "Conclusion and references.", fontsize=10)

    # 1. Test block extraction
    blocks = inspector.extract_page_blocks_from_fitz(doc)
    assert len(blocks) > 0
    assert all(b.bbox is not None and b.bbox.page_width == 600 for b in blocks)

    # 2. Test metrics and unintended whitespace
    metrics = inspector.calculate_page_metrics_from_fitz(doc)
    assert len(metrics) == 3
    whitespace = inspector.detect_unintended_whitespace(metrics)
    assert len(whitespace) == 1
    assert whitespace[0].page_index == 1
    assert whitespace[0].anomaly_type == "UNINTENDED_WHITESPACE"

    # 3. Test PDF page extraction and control auditing
    pdf_pages = inspector.extract_pdf_pages_from_fitz(doc)
    assert len(pdf_pages) == 3
    uncontrolled = inspector.audit_uncontrolled_pages(pdf_pages)
    # Page 1 has no page number or doc number, should be flagged
    p1_anomalies = [a for a in uncontrolled if a.page_index == 1]
    assert len(p1_anomalies) == 1

    doc.close()


# ── 7. Real Testcase Document Integration Tests ──────────────────────────────


def test_mepg_real_pdf_cross_page_break_table_6_3(inspector: DocumentLayoutInspector) -> None:
    """
    Validates that the real-world 'Table 6-3 and' cross-page break
    in MEPG PDF (p. 20-23) is detected by DocumentLayoutInspector.
    """
    if not MEPG_PDF.exists():
        pytest.skip(f"Test file not found: {MEPG_PDF}")

    doc = fitz.open(str(MEPG_PDF))
    try:
        # Extract blocks around the known break (index 20-24)
        target_blocks: list[PageBlock] = []
        for pno in range(20, 24):
            target_blocks.extend(inspector.extract_page_blocks_from_fitz(doc[pno]))

        cross_breaks = inspector.detect_cross_page_sentence_breaks(target_blocks)
        assert len(cross_breaks) > 0

        # Verify that the Table 6-3 break is specifically identified
        mepg_break = any("Table 6-3 and" in cb.details.get("last_text", "") for cb in cross_breaks)
        assert mepg_break, "Expected 'Table 6-3 and' cross-page break was not detected."
    finally:
        doc.close()
