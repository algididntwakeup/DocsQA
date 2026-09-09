"""Unit tests for Near-Duplicate Content Detection Service (M4.3)."""

from unittest.mock import patch
from uuid import uuid4

from schemas.extraction import CoordinateContract, ExtractionArtifact, PageMetadata, TextSpan
from services.duplicate import MAX_FUZZY_COMPARISONS, analyze_duplicates


def _make_span(text: str, page_index: int, y0: float = 200.0, y1: float = 240.0) -> TextSpan:
    return TextSpan(
        text=text,
        bbox=CoordinateContract(
            page_index=page_index,
            x0=50.0,
            y0=y0,
            x1=550.0,
            y1=y1,
            page_width=612.0,
            page_height=792.0,
        ),
    )


def test_detects_near_duplicate_content_with_dual_locations() -> None:
    """Detects >= 85% duplicate paragraphs across pages and sets dual bounding boxes."""
    p1_text = (
        "All pressure-retaining components shall be subject to 100% radiographic examination "
        "in accordance with ASME Section VIII Division 1 Appendix 4 "
        "prior to final hydrostatic testing."
    )
    p2_text = (
        "All pressure-retaining components shall be subjected to 100% radiographic examination "
        "in accordance with ASME Section VIII Division 1 App 4 before final hydrostatic testing."
    )

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[
            PageMetadata(page_index=0, width=612.0, height=792.0),
            PageMetadata(page_index=1, width=612.0, height=792.0),
        ],
        spans=[
            _make_span(p1_text, page_index=0),
            _make_span(p2_text, page_index=1),
        ],
    )

    analysis = analyze_duplicates(artifact, threshold=85)
    assert len(analysis.findings) == 1

    finding = analysis.findings[0]
    assert finding.type == "DUPLICATE_CONTENT"
    assert finding.confidence >= 0.85
    assert finding.location.page_index == 1
    assert finding.original_location is not None
    assert finding.original_location.page_index == 0
    assert "Page 1" in finding.message


def test_dissimilar_paragraphs_yield_zero_findings() -> None:
    """Paragraphs with different topics do not trigger duplicate warnings."""
    p1_text = "The tensile test was performed on a 500kN calibrated servohydraulic test frame."
    p2_text = (
        "Chemical analysis was determined by optical emission spectrometry with argon purging."
    )

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=0, width=612.0, height=792.0)],
        spans=[
            _make_span(p1_text, page_index=0, y0=100.0, y1=140.0),
            _make_span(p2_text, page_index=0, y0=300.0, y1=340.0),
        ],
    )

    analysis = analyze_duplicates(artifact)
    assert len(analysis.findings) == 0


def test_ignores_headers_footers_and_short_snippets() -> None:
    """Excludes short strings (<30 chars) and header/footer regions."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[
            PageMetadata(page_index=0, width=612.0, height=792.0),
            PageMetadata(page_index=1, width=612.0, height=792.0),
        ],
        spans=[
            # Header zone (y0=20, y1=40 on 792 height page is < 8%)
            _make_span(
                "CONFIDENTIAL & PROPRIETARY CLIENT SPECIFICATION", page_index=0, y0=20.0, y1=40.0
            ),
            _make_span(
                "CONFIDENTIAL & PROPRIETARY CLIENT SPECIFICATION", page_index=1, y0=20.0, y1=40.0
            ),
            # Short text (<30 chars)
            _make_span("Section 2.1 Overview", page_index=0, y0=100.0, y1=120.0),
            _make_span("Section 2.1 Overview", page_index=1, y0=100.0, y1=120.0),
        ],
    )

    analysis = analyze_duplicates(artifact)
    assert len(analysis.findings) == 0


def test_large_document_uses_bounded_candidate_matching() -> None:
    """Large documents do not fall back to an unbounded quadratic fuzzy scan."""
    spans = [
        _make_span(
            f"Unrelated engineering paragraph {index} describes material qualification "
            f"and inspection sequence {index} with unique evidence.",
            page_index=index // 20,
            y0=100 + (index % 20) * 25,
            y1=120 + (index % 20) * 25,
        )
        for index in range(1200)
    ]

    with patch("services.duplicate.fuzz.token_sort_ratio", wraps=lambda left, right: 0) as matcher:
        analysis = analyze_duplicates(
            ExtractionArtifact(
                document_id=uuid4(),
                pages=[
                    PageMetadata(page_index=index, width=612.0, height=792.0)
                    for index in range(60)
                ],
                spans=spans,
            )
        )

    assert matcher.call_count <= MAX_FUZZY_COMPARISONS
    assert len(analysis.findings) >= 0


def test_unrelated_token_sets_skip_fuzzy_matching() -> None:
    """Paragraphs with no substantive token overlap never call fuzzy matching."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=0, width=612.0, height=792.0)],
        spans=[
            _make_span(
                "alpha alloy pressure vessel inspection sequence and acceptance criteria",
                page_index=0,
            ),
            _make_span(
                "banana chemical laboratory microscopy result calibration procedure",
                page_index=0,
                y0=300,
                y1=340,
            ),
        ],
    )

    with patch("services.duplicate.fuzz.token_sort_ratio") as matcher:
        analyze_duplicates(artifact)

    matcher.assert_not_called()
