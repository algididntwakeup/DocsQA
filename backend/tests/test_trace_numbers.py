"""Tests for deterministic table math validation (F10)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from schemas.extraction import CoordinateContract, ExtractionArtifact, Table, TableCell
from services.trace_numbers import (
    analyze_table_math,
    extract_header_unit,
    normalize_unit_token,
    parse_decimal_value,
)


def _bbox(page: int = 0, y0: float = 100, y1: float = 120) -> CoordinateContract:
    return CoordinateContract(
        page_index=page,
        x0=50.0,
        y0=y0,
        x1=300.0,
        y1=y1,
        page_width=612.0,
        page_height=792.0,
    )


# ── Unit normalization and header unit extraction ────────────────────────────


def test_normalize_unit_token() -> None:
    assert normalize_unit_token("lbs") == "lb"
    assert normalize_unit_token("lb") == "lb"
    assert normalize_unit_token("ft-lbs") == "ft-lb"
    assert normalize_unit_token("USD") == "$"
    assert normalize_unit_token("$") == "$"
    assert normalize_unit_token("EUR") == "€"
    assert normalize_unit_token("MPa") == "MPa"
    assert normalize_unit_token("kg") == "kg"
    assert normalize_unit_token(None) is None


def test_extract_header_unit() -> None:
    assert extract_header_unit("Thickness (mm)") == "mm"
    assert extract_header_unit("Yield Strength [MPa]") == "MPa"
    assert extract_header_unit("Weight, kg") == "kg"
    assert extract_header_unit("Elongation (%)") == "%"
    assert extract_header_unit("Item Description") is None


# ── Decimal parser tests ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected_val", "expected_unit"),
    [
        ("123", Decimal("123"), None),
        ("123.45", Decimal("123.45"), None),
        ("1,234.56", Decimal("1234.56"), None),
        ("1,234,567.89", Decimal("1234567.89"), None),
        ("1.234,56", Decimal("1234.56"), None),
        ("1.234.567,89", Decimal("1234567.89"), None),
        ("1 234.56", Decimal("1234.56"), None),
        ("1 234,56", Decimal("1234.56"), None),
        ("12,5", Decimal("12.5"), None),
        ("1,50", Decimal("1.50"), None),
        ("0,75", Decimal("0.75"), None),
        ("-45.50", Decimal("-45.50"), None),
        ("(45.50)", Decimal("-45.50"), None),
        ("(1,200.00)", Decimal("-1200.00"), None),
        ("$1,500.00", Decimal("1500.00"), "$"),
        ("€250.50", Decimal("250.50"), "€"),
        ("120.5 MPa", Decimal("120.5"), "MPa"),
        ("45 kg", Decimal("45"), "kg"),
        ("100 psi", Decimal("100"), "psi"),
        ("15.5%", Decimal("15.5"), "%"),
        ("(25.0 kg)", Decimal("-25.0"), "kg"),
        ("50 kN", Decimal("50"), "kN"),
        ("100 J", Decimal("100"), "J"),
    ],
)
def test_parse_decimal_value_valid(
    raw: str, expected_val: Decimal, expected_unit: str | None
) -> None:
    result = parse_decimal_value(raw)
    assert result is not None
    val, unit = result
    assert val == expected_val
    assert unit == expected_unit


@pytest.mark.parametrize("raw", ["", "-", "--", "N/A", "NA", "TBD", "None", "nil"])
def test_parse_decimal_value_neutral_empty(raw: str) -> None:
    assert parse_decimal_value(raw) is None


@pytest.mark.parametrize("raw", ["Heat-10294", "ASTM A36", "REV-01", "Accepted", "Pass"])
def test_parse_decimal_value_non_numeric(raw: str) -> None:
    assert parse_decimal_value(raw) is None


def test_property_decimal_precision_reconstruction() -> None:
    """Verify that arbitrary exact Decimals convert to formatted string and back without drift."""
    for i in range(1, 100):
        expected = Decimal(str(i)) * Decimal("12.345")
        formatted = f"{expected:f}"
        parsed = parse_decimal_value(formatted)
        assert parsed is not None
        assert parsed[0] == expected


# ── Flat Table Math Assertion & Scoping Tests ───────────────────────────────


def test_flat_table_correct_column_total() -> None:
    """A standard flat table with column sum matches stated total exactly."""
    cells = [
        # Row 0: Header
        TableCell(text="Item", row_index=0, col_index=0, bbox=_bbox(0, 10, 20)),
        TableCell(text="Weight (kg)", row_index=0, col_index=1, bbox=_bbox(0, 10, 20)),
        # Row 1: Item 1
        TableCell(text="Plate A", row_index=1, col_index=0, bbox=_bbox(0, 20, 30)),
        TableCell(text="10.50", row_index=1, col_index=1, bbox=_bbox(0, 20, 30)),
        # Row 2: Item 2
        TableCell(text="Plate B", row_index=2, col_index=0, bbox=_bbox(0, 30, 40)),
        TableCell(text="20.25", row_index=2, col_index=1, bbox=_bbox(0, 30, 40)),
        # Row 3: Item 3
        TableCell(text="Plate C", row_index=3, col_index=0, bbox=_bbox(0, 40, 50)),
        TableCell(text="30.25", row_index=3, col_index=1, bbox=_bbox(0, 40, 50)),
        # Row 4: Total
        TableCell(text="Total", row_index=4, col_index=0, bbox=_bbox(0, 50, 60)),
        TableCell(text="61.00", row_index=4, col_index=1, bbox=_bbox(0, 50, 60)),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells, bbox=_bbox(0, 10, 60))],
    )

    analysis = analyze_table_math(artifact)

    assert analysis.tables_analyzed == 1
    assert len(analysis.assertions) == 1
    assertion = analysis.assertions[0]
    assert assertion.kind == "COLUMN_TOTAL"
    assert assertion.stated_value == Decimal("61.00")
    assert assertion.computed_value == Decimal("61.00")
    assert assertion.delta == Decimal("0")
    assert assertion.status == "CORRECT"
    assert assertion.unit == "kg"
    assert len(assertion.operand_cells) == 3
    assert len(analysis.findings) == 0


def test_table_math_rounding_boundary_within_tolerance() -> None:
    """Delta within allowable tolerance is classified as ROUNDING_BOUNDARY without findings."""
    cells = [
        TableCell(text="Item", row_index=0, col_index=0),
        TableCell(text="Qty", row_index=0, col_index=1),
        TableCell(text="Part 1", row_index=1, col_index=0),
        TableCell(text="10.0", row_index=1, col_index=1),
        TableCell(text="Part 2", row_index=2, col_index=0),
        TableCell(text="20.0", row_index=2, col_index=1),
        TableCell(text="Total", row_index=3, col_index=0),
        # computed=30.0, delta=0.5 <= tol_unit(1.0)
        TableCell(text="30.5", row_index=3, col_index=1),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 1
    assertion = analysis.assertions[0]
    assert assertion.status == "ROUNDING_BOUNDARY"
    assert assertion.delta == Decimal("0.5")
    assert len(analysis.findings) == 0  # No false positive


def test_table_math_percentage_tolerance_boundary() -> None:
    """Large values use 0.5% tolerance threshold."""
    # Stated: 2000. 0.5% of 2000 is 10.0. Delta of 8.0 should pass as ROUNDING_BOUNDARY.
    cells = [
        TableCell(text="Section", row_index=0, col_index=0),
        TableCell(text="Load (kN)", row_index=0, col_index=1),
        TableCell(text="A", row_index=1, col_index=0),
        TableCell(text="1000", row_index=1, col_index=1),
        TableCell(text="B", row_index=2, col_index=0),
        TableCell(text="1000", row_index=2, col_index=1),
        TableCell(text="Total", row_index=3, col_index=0),
        TableCell(text="2008", row_index=3, col_index=1),  # delta 8 <= 10.04
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 1
    assert analysis.assertions[0].status == "ROUNDING_BOUNDARY"
    assert len(analysis.findings) == 0


def test_table_math_mismatch_exceeds_tolerance() -> None:
    """Delta exceeding tolerance is classified as MISMATCH and emits TABLE_MATH_MISMATCH."""
    cells = [
        TableCell(text="Item", row_index=0, col_index=0),
        TableCell(text="Amount", row_index=0, col_index=1),
        TableCell(text="A", row_index=1, col_index=0),
        TableCell(text="100.00", row_index=1, col_index=1, bbox=_bbox(0, 20, 30)),
        TableCell(text="B", row_index=2, col_index=0),
        TableCell(text="200.00", row_index=2, col_index=1, bbox=_bbox(0, 30, 40)),
        TableCell(text="Total", row_index=3, col_index=0),
        TableCell(text="350.00", row_index=3, col_index=1, bbox=_bbox(0, 40, 50)),  # computed=300
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 1
    assertion = analysis.assertions[0]
    assert assertion.status == "MISMATCH"
    assert assertion.delta == Decimal("50.00")

    assert len(analysis.findings) == 1
    finding = analysis.findings[0]
    assert finding.kind == "TABLE_MATH_MISMATCH"
    assert finding.stated_value == Decimal("350.00")
    assert finding.computed_value == Decimal("300.00")
    assert finding.delta == Decimal("50.00")
    assert finding.total_location is not None
    assert len(finding.operand_locations) == 2


def test_subtotal_and_grand_total_scoping() -> None:
    """Grand total reconciles against subtotals without double-counting base items."""
    cells = [
        TableCell(text="Item", row_index=0, col_index=0),
        TableCell(text="Cost ($)", row_index=0, col_index=1),
        # Block 1
        TableCell(text="Item 1", row_index=1, col_index=0),
        TableCell(text="10", row_index=1, col_index=1),
        TableCell(text="Item 2", row_index=2, col_index=0),
        TableCell(text="20", row_index=2, col_index=1),
        TableCell(text="Subtotal", row_index=3, col_index=0),
        TableCell(text="30", row_index=3, col_index=1),
        # Block 2
        TableCell(text="Item 3", row_index=4, col_index=0),
        TableCell(text="15", row_index=4, col_index=1),
        TableCell(text="Item 4", row_index=5, col_index=0),
        TableCell(text="25", row_index=5, col_index=1),
        TableCell(text="Subtotal", row_index=6, col_index=0),
        TableCell(text="40", row_index=6, col_index=1),
        # Grand Total
        TableCell(text="Grand Total", row_index=7, col_index=0),
        TableCell(text="70", row_index=7, col_index=1),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 3
    kinds = [a.kind for a in analysis.assertions]
    assert kinds == ["SUBTOTAL", "SUBTOTAL", "GRAND_TOTAL"]
    for a in analysis.assertions:
        assert a.status == "CORRECT"
    assert len(analysis.findings) == 0


def test_horizontal_row_totals() -> None:
    """Summary columns at the right edge are evaluated across row operands."""
    cells = [
        TableCell(text="Part", row_index=0, col_index=0),
        TableCell(text="Q1", row_index=0, col_index=1),
        TableCell(text="Q2", row_index=0, col_index=2),
        TableCell(text="Total", row_index=0, col_index=3),
        # Row 1
        TableCell(text="Flange A", row_index=1, col_index=0),
        TableCell(text="100", row_index=1, col_index=1),
        TableCell(text="200", row_index=1, col_index=2),
        TableCell(text="300", row_index=1, col_index=3),
        # Row 2 (Mismatch)
        TableCell(text="Flange B", row_index=2, col_index=0),
        TableCell(text="50", row_index=2, col_index=1),
        TableCell(text="50", row_index=2, col_index=2),
        TableCell(text="120", row_index=2, col_index=3),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    row_assertions = [a for a in analysis.assertions if a.kind == "ROW_TOTAL"]
    assert len(row_assertions) == 2
    assert row_assertions[0].status == "CORRECT"
    assert row_assertions[1].status == "MISMATCH"
    assert len(analysis.findings) == 1
    assert analysis.findings[0].kind == "TABLE_MATH_MISMATCH"


def test_unit_mismatch_detection() -> None:
    """Operands with incompatible units or conflicting total units are flagged."""
    cells = [
        TableCell(text="Item", row_index=0, col_index=0),
        TableCell(text="Weight", row_index=0, col_index=1),
        TableCell(text="A", row_index=1, col_index=0),
        TableCell(text="10 kg", row_index=1, col_index=1),
        TableCell(text="B", row_index=2, col_index=0),
        TableCell(text="20 lb", row_index=2, col_index=1),  # conflicting unit
        TableCell(text="Total", row_index=3, col_index=0),
        TableCell(text="30 kg", row_index=3, col_index=1),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 1
    assert analysis.assertions[0].status == "UNIT_MISMATCH"
    assert len(analysis.findings) == 1
    assert analysis.findings[0].kind == "UNIT_MISMATCH"


def test_malformed_row_detection() -> None:
    """Corrupted non-numeric text in a numeric series surfaces as MALFORMED_TABLE_ROW."""
    cells = [
        TableCell(text="Sample", row_index=0, col_index=0),
        TableCell(text="Value", row_index=0, col_index=1),
        TableCell(text="1", row_index=1, col_index=0),
        TableCell(text="10.5", row_index=1, col_index=1),
        TableCell(text="2", row_index=2, col_index=0),
        TableCell(text="CORRUPT_ERR_###", row_index=2, col_index=1, bbox=_bbox(0, 25, 35)),
        TableCell(text="Total", row_index=3, col_index=0),
        TableCell(text="20.5", row_index=3, col_index=1, bbox=_bbox(0, 35, 45)),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    malformed_findings = [f for f in analysis.findings if f.kind == "MALFORMED_TABLE_ROW"]
    assert len(malformed_findings) == 1


def test_neutral_cells_do_not_block_valid_totals() -> None:
    """Empty cells or '-' dashes are treated as neutral without corrupting the sum."""
    cells = [
        TableCell(text="Item", row_index=0, col_index=0),
        TableCell(text="Value", row_index=0, col_index=1),
        TableCell(text="A", row_index=1, col_index=0),
        TableCell(text="10", row_index=1, col_index=1),
        TableCell(text="B", row_index=2, col_index=0),
        TableCell(text="-", row_index=2, col_index=1),  # neutral dash
        TableCell(text="C", row_index=3, col_index=0),
        TableCell(text="20", row_index=3, col_index=1),
        TableCell(text="Total", row_index=4, col_index=0),
        TableCell(text="30", row_index=4, col_index=1),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert len(analysis.assertions) == 1
    assert analysis.assertions[0].status == "CORRECT"
    assert len(analysis.findings) == 0


def test_false_positive_resistance_on_non_total_tables() -> None:
    """Specification tables, chemical analyses, and revision tables emit zero findings."""
    cells = [
        TableCell(text="Element", row_index=0, col_index=0),
        TableCell(text="C", row_index=0, col_index=1),
        TableCell(text="Mn", row_index=0, col_index=2),
        TableCell(text="P", row_index=0, col_index=3),
        TableCell(text="S", row_index=0, col_index=4),
        TableCell(text="Heat 102", row_index=1, col_index=0),
        TableCell(text="0.18", row_index=1, col_index=1),
        TableCell(text="1.20", row_index=1, col_index=2),
        TableCell(text="0.015", row_index=1, col_index=3),
        TableCell(text="0.008", row_index=1, col_index=4),
    ]
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        tables=[Table(cells=cells)],
    )

    analysis = analyze_table_math(artifact)

    assert analysis.tables_analyzed == 1
    assert len(analysis.assertions) == 0
    assert len(analysis.findings) == 0
