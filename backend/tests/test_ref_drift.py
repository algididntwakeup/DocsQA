"""Tests for deterministic reference drift detection (F11)."""

from uuid import uuid4

import pytest

from schemas.extraction import (
    CoordinateContract,
    ExtractionArtifact,
    Heading,
    PageMetadata,
    TextSpan,
)
from services.ref_drift import (
    analyze_ref_drift,
    int_to_roman,
    normalize_title,
    parse_page_token,
    roman_to_int,
)


def _bbox(page: int = 0, y0: float = 100, y1: float = 120) -> CoordinateContract:
    return CoordinateContract(
        page_index=page,
        x0=50.0,
        y0=y0,
        x1=400.0,
        y1=y1,
        page_width=612.0,
        page_height=792.0,
    )


# ── Roman numeral and page token helpers ───────────────────────────────────


@pytest.mark.parametrize(
    ("roman", "expected"),
    [
        ("i", 1),
        ("ii", 2),
        ("iii", 3),
        ("iv", 4),
        ("v", 5),
        ("vi", 6),
        ("ix", 9),
        ("x", 10),
        ("xiv", 14),
        ("xv", 15),
        ("xix", 19),
        ("xx", 20),
        ("IV", 4),
        ("XII", 12),
    ],
)
def test_roman_to_int_valid(roman: str, expected: int) -> None:
    assert roman_to_int(roman) == expected


@pytest.mark.parametrize("invalid", ["", "abc", "iiii", "vv", "123", "ixx"])
def test_roman_to_int_invalid(invalid: str) -> None:
    assert roman_to_int(invalid) is None


def test_int_to_roman() -> None:
    assert int_to_roman(1) == "i"
    assert int_to_roman(4) == "iv"
    assert int_to_roman(14) == "xiv"
    assert int_to_roman(0) == "0"


def test_parse_page_token() -> None:
    assert parse_page_token("12") == ("12", 12)
    assert parse_page_token("iv") == ("iv", 4)
    assert parse_page_token("A-1") == ("A-1", None)


def test_normalize_title() -> None:
    assert normalize_title("1.0 Introduction ..........") == "1.0 introduction"
    assert normalize_title("Section 2.0 Materials — —") == "section 2.0 materials"
    assert normalize_title("Figure 1: Microstructure") == "figure 1: microstructure"


# ── Reference Drift Scenarios ───────────────────────────────────────────────


def test_toc_happy_path_exact_match() -> None:
    """ToC entries match actual heading page locations exactly."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
        PageMetadata(page_index=2, width=612, height=792, page_label="3"),
    ]
    headings = [
        # ToC heading on page 0
        Heading(text="Table of Contents", level=1, bbox=_bbox(0, 50, 70)),
        # Actual headings on pages 1 and 2
        Heading(text="1.0 Scope", level=1, bbox=_bbox(1, 100, 120)),
        Heading(text="2.0 Material Specification", level=1, bbox=_bbox(2, 100, 120)),
    ]
    spans = [
        # ToC entry lines on page 0
        TextSpan(text="1.0 Scope ................................. 2", bbox=_bbox(0, 100, 115)),
        TextSpan(text="2.0 Material Specification ................ 3", bbox=_bbox(0, 120, 135)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert analysis.toc_entries_found == 2
    assert len(analysis.findings) == 0


def test_toc_positive_drift_detected() -> None:
    """When a heading is shifted later by an inserted page, positive drift is flagged."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
        PageMetadata(page_index=2, width=612, height=792, page_label="3"),
        PageMetadata(page_index=3, width=612, height=792, page_label="4"),
        PageMetadata(page_index=4, width=612, height=792, page_label="5"),
    ]
    headings = [
        Heading(text="Table of Contents", level=1, bbox=_bbox(0, 50, 70)),
        # Scope is on page 2 (index 1), matches
        Heading(text="1.0 Scope", level=1, bbox=_bbox(1, 100, 120)),
        # Materials is on page 5 (index 4), but ToC says page 3! Drift = +2
        Heading(text="2.0 Materials", level=1, bbox=_bbox(4, 100, 120)),
    ]
    spans = [
        TextSpan(text="1.0 Scope ................. 2", bbox=_bbox(0, 100, 115)),
        TextSpan(text="2.0 Materials ............. 3", bbox=_bbox(0, 120, 135)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert analysis.toc_entries_found == 2
    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.kind == "REF_DRIFT"
    assert finding.referenced_page_label == "3"
    assert finding.actual_page_label == "5"
    assert finding.page_delta == 2
    assert finding.entry_location.page_index == 0
    assert finding.target_location is not None
    assert finding.target_location.page_index == 4


def test_toc_negative_drift_detected() -> None:
    """When a section starts earlier than stated, negative drift is flagged."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
        PageMetadata(page_index=2, width=612, height=792, page_label="3"),
    ]
    headings = [
        Heading(text="Contents", level=1, bbox=_bbox(0, 50, 70)),
        # Stated page 4, but appears on page 3 (index 2). Drift = -1
        Heading(text="3.0 Welding Procedure", level=1, bbox=_bbox(2, 100, 120)),
    ]
    spans = [
        TextSpan(text="3.0 Welding Procedure ......... 4", bbox=_bbox(0, 100, 115)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.kind == "REF_DRIFT"
    assert finding.referenced_page_label == "4"
    assert finding.actual_page_label == "3"
    assert finding.page_delta == -1


def test_roman_numeral_front_matter_drift() -> None:
    """Roman numeral page labels in preliminary matter are resolved and diffed."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="i"),
        PageMetadata(page_index=1, width=612, height=792, page_label="ii"),
        PageMetadata(page_index=2, width=612, height=792, page_label="iii"),
        PageMetadata(page_index=3, width=612, height=792, page_label="iv"),
        PageMetadata(page_index=4, width=612, height=792, page_label="v"),
    ]
    headings = [
        Heading(text="Table of Contents", level=1, bbox=_bbox(0, 50, 70)),
        # Stated as page iii, actually on page v (index 4). Drift = +2
        Heading(text="Executive Summary", level=1, bbox=_bbox(4, 100, 120)),
    ]
    spans = [
        TextSpan(text="Executive Summary ............ iii", bbox=_bbox(0, 100, 115)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.kind == "REF_DRIFT"
    assert finding.referenced_page_label == "iii"
    assert finding.actual_page_label == "v"
    assert finding.page_delta == 2


def test_list_of_figures_and_tables_drift() -> None:
    """List of Figures and List of Tables entries are tracked and diffed."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
        PageMetadata(page_index=2, width=612, height=792, page_label="3"),
    ]
    headings = [
        Heading(text="List of Figures", level=1, bbox=_bbox(0, 50, 70)),
    ]
    spans = [
        # LoF entry stating page 2
        TextSpan(text="Figure 1 - Tensile Curve ....... 2", bbox=_bbox(0, 100, 115)),
        # Actual figure caption on page 3 (index 2) -> Drift +1
        TextSpan(text="Figure 1 - Tensile Curve", bbox=_bbox(2, 200, 220)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert analysis.toc_entries_found == 1
    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.source_list == "LOF"
    assert finding.kind == "REF_DRIFT"
    assert finding.page_delta == 1


def test_missing_target_detection() -> None:
    """ToC entry whose target heading does not exist surfaces as MISSING_TARGET."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
    ]
    headings = [
        Heading(text="Table of Contents", level=1, bbox=_bbox(0, 50, 70)),
    ]
    spans = [
        # Cites a section that was deleted from document body
        TextSpan(text="4.0 Non-Destructive Testing ...... 12", bbox=_bbox(0, 100, 115)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.kind == "MISSING_TARGET"
    assert finding.target_location is None


def test_duplicate_caption_detection() -> None:
    """Multiple identical captions on different pages surface as DUPLICATE_CAPTION."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
        PageMetadata(page_index=1, width=612, height=792, page_label="2"),
        PageMetadata(page_index=2, width=612, height=792, page_label="3"),
    ]
    headings = [
        Heading(text="List of Figures", level=1, bbox=_bbox(0, 50, 70)),
    ]
    spans = [
        TextSpan(text="Figure 2: Microstructure ....... 2", bbox=_bbox(0, 100, 115)),
        # Two identical captions on different pages
        TextSpan(text="Figure 2: Microstructure", bbox=_bbox(1, 100, 120)),
        TextSpan(text="Figure 2: Microstructure", bbox=_bbox(2, 100, 120)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert len(analysis.findings) == 1
    assert analysis.findings[0].kind == "DUPLICATE_CAPTION"


def test_false_positive_resistance_no_toc() -> None:
    """Document without any ToC/LoF/LoT produces zero findings."""
    pages = [
        PageMetadata(page_index=0, width=612, height=792, page_label="1"),
    ]
    headings = [
        Heading(text="Inspection Certificate", level=1, bbox=_bbox(0, 50, 70)),
        Heading(text="Chemical Analysis", level=2, bbox=_bbox(0, 100, 120)),
    ]
    spans = [
        TextSpan(text="Standard tensile inspection report.", bbox=_bbox(0, 130, 145)),
    ]

    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=pages,
        headings=headings,
        spans=spans,
    )

    analysis = analyze_ref_drift(artifact)

    assert analysis.toc_entries_found == 0
    assert len(analysis.findings) == 0
