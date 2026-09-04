"""Tests for deterministic standard citation and bibliography matching."""

from uuid import uuid4

from schemas.extraction import CoordinateContract, ExtractionArtifact, Heading, TextSpan
from services.standard_traceability import (
    analyze_standard_traceability,
    normalize_standard_code,
)


def _box(page: int, y: float) -> CoordinateContract:
    return CoordinateContract(
        page_index=page,
        x0=10,
        y0=y,
        x1=500,
        y1=y + 12,
        page_width=600,
        page_height=800,
    )


def _artifact(body: list[str], references: list[str] | None = None) -> ExtractionArtifact:
    spans = [TextSpan(text=text, bbox=_box(0, 20 + index * 20)) for index, text in enumerate(body)]
    headings: list[Heading] = []
    if references is not None:
        headings.append(Heading(text="References", level=1, bbox=_box(1, 10)))
        spans.extend(
            TextSpan(text=text, bbox=_box(1, 30 + index * 20))
            for index, text in enumerate(references)
        )
    return ExtractionArtifact(document_id=uuid4(), spans=spans, headings=headings)


def test_matching_standard_and_year_has_no_findings() -> None:
    result = analyze_standard_traceability(
        _artifact(["Design complies with ASTM A240-2020."], ["ASTM A240:2020"])
    )
    assert result.reference_section_found is True
    assert result.findings == []
    assert result.body_citations[0].normalized_code == "ASTM A240"


def test_missing_bibliography_entry_is_reported() -> None:
    result = analyze_standard_traceability(
        _artifact(["Inspection follows ISO 9001:2015."], ["ASTM A240:2020"])
    )
    assert [finding.kind for finding in result.findings] == [
        "STANDARD_NOT_IN_BIBLIOGRAPHY"
    ]
    assert result.findings[0].cited_standard == "ISO 9001"


def test_edition_year_mismatch_retains_both_locations() -> None:
    result = analyze_standard_traceability(
        _artifact(["Apply API STD 650-2020."], ["API STD 650-2013"])
    )
    finding = result.findings[0]
    assert finding.kind == "EDITION_YEAR_MISMATCH"
    assert finding.body_edition_year == 2020
    assert finding.bibliography_edition_year == 2013
    assert finding.bibliography_location is not None


def test_unknown_bare_api_number_is_ambiguous_not_missing() -> None:
    result = analyze_standard_traceability(
        _artifact(["The API 200 response is recorded."], [])
    )
    assert [finding.kind for finding in result.findings] == ["AMBIGUOUS_STANDARD"]


def test_duplicate_body_mentions_produce_one_finding() -> None:
    result = analyze_standard_traceability(
        _artifact(["Use ISO 9001:2015.", "ISO 9001:2015 remains applicable."], [])
    )
    assert len(result.body_citations) == 2
    assert len(result.findings) == 1


def test_malformed_or_unregistered_codes_do_not_match() -> None:
    result = analyze_standard_traceability(
        _artifact(["Use ISO quality methods and ASTM-approved material.", "ASME team review."], [])
    )
    assert result.body_citations == []
    assert result.findings == []


def test_reference_heading_boundary_is_not_treated_as_body() -> None:
    result = analyze_standard_traceability(
        _artifact([], ["ASME Section VIII Division 1-2021"])
    )
    assert result.body_citations == []
    assert len(result.reference_entries) == 1


def test_normalize_common_labels() -> None:
    assert normalize_standard_code("ASME Sec. VIII Div. 1") == (
        "ASME SECTION VIII DIVISION 1"
    )
    assert normalize_standard_code("EN ISO 9001") == "ISO 9001"
