"""Unit tests for finding aggregation, normalization, and deduplication (M2.5)."""

from decimal import Decimal
from uuid import uuid4

from domain.enums import IssueCategory, Severity
from schemas.extraction import CoordinateContract
from schemas.issues import (
    ReferenceDriftEvidence,
    RevisionEvidence,
    StageFailureEvidence,
    StandardEvidence,
    TableMathEvidence,
)
from schemas.ref_drift import RefDriftAnalysis, RefDriftFinding
from schemas.revision import RevisionAnalysis, RevisionSource
from schemas.standard_traceability import StandardFinding, StandardTraceabilityAnalysis
from schemas.table_math import TableMathAnalysis, TableMathFinding
from services.aggregate import aggregate_document_findings, to_bounding_box


def _make_coord(page_index: int = 0, y0: float = 100.0) -> CoordinateContract:
    return CoordinateContract(
        page_index=page_index,
        x0=50.0,
        y0=y0,
        x1=250.0,
        y1=y0 + 20.0,
        page_width=612.0,
        page_height=792.0,
    )


def test_to_bounding_box_fallback() -> None:
    """None coordinate returns safe default bounding box on specified page."""
    box = to_bounding_box(None, default_page=2)
    assert box.page_index == 2
    assert box.page_width == 612.0
    assert box.page_height == 792.0


def test_to_bounding_box_conversion() -> None:
    """Valid coordinate contract converts cleanly to BoundingBox."""
    coord = _make_coord(1, 150.0)
    box = to_bounding_box(coord)
    assert box.page_index == 1
    assert box.x0 == 50.0
    assert box.y0 == 150.0


def test_normalize_revision_mismatch() -> None:
    """Revision mismatch creates a critical traceability issue with RevisionEvidence."""
    doc_id = uuid4()
    analysis = RevisionAnalysis(
        outcome="MISMATCH",
        sources=[
            RevisionSource(source="FILENAME", raw_value="A", normalized_value="A"),
            RevisionSource(
                source="COVER",
                raw_value="B",
                normalized_value="B",
                location=_make_coord(0, 100.0),
            ),
            RevisionSource(
                source="REVISION_SHEET",
                raw_value="A",
                normalized_value="A",
                location=_make_coord(1, 200.0),
            ),
        ],
        sources_disagreeing=["COVER"],
    )

    result = aggregate_document_findings(doc_id, revision=analysis)

    assert result.total_issues == 1
    issue = result.issues[0]
    assert issue.category == IssueCategory.TRACEABILITY
    assert issue.type == "REVISION_MISMATCH"
    assert issue.severity == Severity.CRITICAL
    assert issue.confidence == 1.0
    assert isinstance(issue.evidence, RevisionEvidence)
    assert issue.evidence.sources_disagreeing == ["COVER"]
    assert issue.evidence.cover_revision == "B"
    assert issue.evidence.filename_revision == "A"
    assert len(issue.evidence.locations) == 2


def test_normalize_revision_match_produces_no_issues() -> None:
    """Matching revision sources produce zero issues."""
    doc_id = uuid4()
    analysis = RevisionAnalysis(
        outcome="MATCH",
        sources=[
            RevisionSource(source="FILENAME", raw_value="0", normalized_value="0"),
            RevisionSource(source="COVER", raw_value="0", normalized_value="0"),
            RevisionSource(source="REVISION_SHEET", raw_value="0", normalized_value="0"),
        ],
    )
    result = aggregate_document_findings(doc_id, revision=analysis)
    assert result.total_issues == 0


def test_normalize_table_math_findings() -> None:
    """Table math findings map to exact severities and TableMathEvidence."""
    doc_id = uuid4()
    analysis = TableMathAnalysis(
        tables_analyzed=1,
        findings=[
            TableMathFinding(
                kind="TABLE_MATH_MISMATCH",
                table_index=0,
                stated_value=Decimal("100"),
                computed_value=Decimal("95"),
                delta=Decimal("5"),
                tolerance=Decimal("0.5"),
                total_location=_make_coord(0, 300.0),
                operand_locations=[_make_coord(0, 200.0), _make_coord(0, 250.0)],
                message="Column total mismatch",
            ),
            TableMathFinding(
                kind="TOTAL_NOT_FOUND",
                table_index=1,
                message="Expected total cell not found",
            ),
            TableMathFinding(
                kind="UNIT_MISMATCH",
                table_index=0,
                stated_value=Decimal("50"),
                computed_value=Decimal("50"),
                delta=Decimal("0"),
                tolerance=Decimal("0"),
                total_location=_make_coord(0, 400.0),
                message="Incompatible units summed",
            ),
            TableMathFinding(
                kind="MALFORMED_TABLE_ROW",
                table_index=2,
                message="Unparseable row values",
            ),
        ],
    )

    result = aggregate_document_findings(doc_id, table_math=analysis)

    assert result.total_issues == 4
    types = {issue.type: issue for issue in result.issues}

    mismatch = types["TABLE_MATH_MISMATCH"]
    assert mismatch.severity == Severity.CRITICAL
    assert mismatch.confidence == 1.0
    assert isinstance(mismatch.evidence, TableMathEvidence)
    assert mismatch.evidence.stated_value == Decimal("100")
    assert mismatch.evidence.computed_value == Decimal("95")
    assert len(mismatch.evidence.operand_locations) == 2

    not_found = types["TOTAL_NOT_FOUND"]
    assert not_found.severity == Severity.HIGH
    assert not_found.confidence == 0.9

    unit_mismatch = types["UNIT_MISMATCH"]
    assert unit_mismatch.severity == Severity.HIGH
    assert unit_mismatch.confidence == 1.0

    malformed = types["MALFORMED_TABLE_ROW"]
    assert malformed.severity == Severity.MEDIUM
    assert malformed.confidence == 0.8


def test_normalize_ref_drift_findings() -> None:
    """Reference drift findings map to ReferenceDriftEvidence with dual locations."""
    doc_id = uuid4()
    analysis = RefDriftAnalysis(
        toc_entries_found=3,
        findings=[
            RefDriftFinding(
                kind="REF_DRIFT",
                label="Section 2.0",
                source_list="TOC",
                referenced_page_label="10",
                actual_page_label="12",
                page_delta=2,
                entry_location=_make_coord(0, 150.0),
                target_location=_make_coord(11, 80.0),
                message="Section 2.0 drifted +2 pages",
            ),
            RefDriftFinding(
                kind="MISSING_TARGET",
                label="Section 3.0",
                source_list="TOC",
                referenced_page_label="15",
                entry_location=_make_coord(0, 180.0),
                message="Target heading not found in document body",
            ),
            RefDriftFinding(
                kind="DUPLICATE_CAPTION",
                label="Figure 1",
                source_list="LOF",
                referenced_page_label="4",
                entry_location=_make_coord(1, 100.0),
                message="Ambiguous duplicate caption",
            ),
        ],
    )

    result = aggregate_document_findings(doc_id, ref_drift=analysis)

    assert result.total_issues == 3
    types = {issue.type: issue for issue in result.issues}

    drift = types["REF_DRIFT"]
    assert drift.severity == Severity.HIGH
    assert drift.confidence == 1.0
    assert isinstance(drift.evidence, ReferenceDriftEvidence)
    assert drift.evidence.page_delta == 2
    assert drift.evidence.entry_location.page_index == 0
    assert drift.evidence.target_location.page_index == 11

    missing = types["MISSING_TARGET"]
    assert missing.severity == Severity.HIGH
    assert isinstance(missing.evidence, ReferenceDriftEvidence)
    assert missing.evidence.actual_page_label == "NOT_FOUND"
    assert missing.evidence.target_location.page_index == 0

    duplicate = types["DUPLICATE_CAPTION"]
    assert duplicate.severity == Severity.MEDIUM
    assert duplicate.confidence == 0.8


def test_normalize_standard_findings() -> None:
    """Standards findings map to StandardEvidence and appropriate severities."""
    doc_id = uuid4()
    analysis = StandardTraceabilityAnalysis(
        reference_section_found=True,
        findings=[
            StandardFinding(
                kind="STANDARD_NOT_IN_BIBLIOGRAPHY",
                cited_standard="ASME B31.3",
                body_location=_make_coord(2, 200.0),
            ),
            StandardFinding(
                kind="EDITION_YEAR_MISMATCH",
                cited_standard="API 650",
                body_edition_year=2018,
                bibliography_entry="API 650-2020",
                bibliography_edition_year=2020,
                body_location=_make_coord(3, 100.0),
                bibliography_location=_make_coord(15, 300.0),
            ),
            StandardFinding(
                kind="AMBIGUOUS_STANDARD",
                cited_standard="API 500",
                body_location=_make_coord(4, 400.0),
            ),
        ],
    )

    result = aggregate_document_findings(doc_id, standard_traceability=analysis)

    assert result.total_issues == 3
    types = {issue.type: issue for issue in result.issues}

    missing_bib = types["STANDARD_NOT_IN_BIBLIOGRAPHY"]
    assert missing_bib.severity == Severity.HIGH
    assert missing_bib.confidence == 1.0
    assert isinstance(missing_bib.evidence, StandardEvidence)
    assert missing_bib.evidence.cited_standard == "ASME B31.3"
    assert missing_bib.evidence.bibliography_location is None

    year_mismatch = types["EDITION_YEAR_MISMATCH"]
    assert year_mismatch.severity == Severity.HIGH
    assert isinstance(year_mismatch.evidence, StandardEvidence)
    assert year_mismatch.evidence.body_edition_year == 2018
    assert year_mismatch.evidence.bibliography_edition_year == 2020
    assert year_mismatch.evidence.bibliography_location is not None

    ambiguous = types["AMBIGUOUS_STANDARD"]
    assert ambiguous.severity == Severity.LOW
    assert ambiguous.confidence == 0.5


def test_stage_failure_creates_synthetic_system_issue() -> None:
    """Failed stage emits a SYSTEM / STAGE_FAILURE issue with StageFailureEvidence."""
    doc_id = uuid4()
    result = aggregate_document_findings(
        doc_id,
        failed_stages=[("table_math", "TIMEOUT_ERROR", True)],
    )

    assert result.total_issues == 1
    issue = result.issues[0]
    assert issue.category == IssueCategory.SYSTEM
    assert issue.type == "STAGE_FAILURE"
    assert issue.severity == Severity.HIGH
    assert issue.confidence == 1.0
    assert isinstance(issue.evidence, StageFailureEvidence)
    assert issue.evidence.stage == "table_math"
    assert issue.evidence.error_code == "TIMEOUT_ERROR"
    assert issue.evidence.retryable is True


def test_aggregation_deduplication() -> None:
    """Identical duplicate findings across redundant scans are collapsed."""
    doc_id = uuid4()
    analysis = StandardTraceabilityAnalysis(
        reference_section_found=True,
        findings=[
            StandardFinding(
                kind="STANDARD_NOT_IN_BIBLIOGRAPHY",
                cited_standard="ASME B31.3",
                body_location=_make_coord(2, 200.0),
            ),
            StandardFinding(
                kind="STANDARD_NOT_IN_BIBLIOGRAPHY",
                cited_standard="ASME B31.3",
                body_location=_make_coord(2, 200.0),
            ),
        ],
    )

    result = aggregate_document_findings(doc_id, standard_traceability=analysis)
    assert result.total_issues == 1


def test_aggregation_result_metrics() -> None:
    """Summary counts by category and severity are aggregated accurately."""
    doc_id = uuid4()
    result = aggregate_document_findings(
        doc_id,
        failed_stages=[("revision_sync", "PARSE_ERROR", False)],
        ref_drift=RefDriftAnalysis(
            toc_entries_found=1,
            findings=[
                RefDriftFinding(
                    kind="REF_DRIFT",
                    label="Heading",
                    source_list="TOC",
                    referenced_page_label="1",
                    actual_page_label="2",
                    page_delta=1,
                    entry_location=_make_coord(0, 100.0),
                    message="Heading drifted +1 page",
                )
            ],
        ),
    )

    assert result.total_issues == 2
    assert result.issues_by_category[IssueCategory.SYSTEM.value] == 1
    assert result.issues_by_category[IssueCategory.TRACEABILITY.value] == 1
    assert result.issues_by_severity[Severity.HIGH.value] == 2
