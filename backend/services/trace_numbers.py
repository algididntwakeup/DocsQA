"""Deterministic table math and traceability validation service (F10)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Literal
from unicodedata import normalize

from core.config import Settings
from core.config import settings as app_settings
from schemas.extraction import CoordinateContract, ExtractionArtifact, Table, TableCell
from schemas.table_math import (
    TableMathAnalysis,
    TableMathAssertion,
    TableMathCell,
    TableMathFinding,
)

# ── Keywords for total row/column detection ────────────────────────────────
_TOTAL_ROW_KEYWORDS = re.compile(
    r"^\s*(?:GRAND\s+)?(?:TOTAL|TOTALS|SUB-?TOTAL|SUM|SUMMARY|OVERALL\s+TOTAL)\b",
    re.IGNORECASE,
)
_SUBTOTAL_KEYWORDS = re.compile(r"^\s*SUB-?TOTAL\b", re.IGNORECASE)
_GRAND_TOTAL_KEYWORDS = re.compile(r"^\s*GRAND\s+TOTAL\b", re.IGNORECASE)
_TOTAL_COL_KEYWORDS = re.compile(
    r"^\s*(?:GRAND\s+)?(?:TOTAL|TOTALS|SUM|SUMMARY)\b",
    re.IGNORECASE,
)

# ── Unit extraction patterns ───────────────────────────────────────────────
_CURRENCY_PREFIXES = re.compile(
    r"^(?P<prefix>[\$€£¥]|Rp\.?|IDR|USD|EUR)\s*",
    re.IGNORECASE,
)
_UNIT_SUFFIXES = re.compile(
    r"\s*(?P<suffix>%|°[CF]|K\b|MPa\b|kPa\b|GPa\b|psi\b|ksi\b|bar\b|mbar\b|"
    r"kN\b|N\b|lbf\b|kgf\b|mm\b|cm\b|m\b|in\b|ft\b|kg\b|g\b|mg\b|t\b|tonne\b|"
    r"ton\b|lbs?\b|oz\b|kJ\b|J\b|ft-lbs?\b|sec\b|s\b|min\b|hrs?\b|h\b|"
    r"pcs\b|ea\b|qty\b|nos\b|items?\b)$",
    re.IGNORECASE,
)
_HEADER_UNIT_PATTERN = re.compile(
    r"(?:[\(\[]\s*([A-Za-z%°][A-Za-z0-9%°\/\-\.\$€£]*)\s*[\)\]]|,\s*([A-Za-z%°][A-Za-z0-9%°\/\-\.\$€£]*)$)",
    re.IGNORECASE,
)

# Non-numeric neutral strings
_NEUTRAL_EMPTY_STRINGS = frozenset(
    {"", "-", "--", "---", "–", "—", "n/a", "na", "null", "none", "tbd", "nil"}
)


def normalize_unit_token(unit: str | None) -> str | None:
    """Normalize common unit representations to a canonical token."""
    if not unit:
        return None
    token = unit.strip()
    lower = token.lower()
    if lower in ("lbs", "lb"):
        return "lb"
    if lower in ("ft-lb", "ft-lbs"):
        return "ft-lb"
    if lower in ("hr", "hrs", "h"):
        return "hr"
    if lower in ("sec", "s"):
        return "s"
    if lower in ("min", "mins"):
        return "min"
    if lower in ("pcs", "items", "ea", "nos", "qty"):
        return lower
    if lower in ("usd", "$"):
        return "$"
    if lower in ("eur", "€"):
        return "€"
    if lower in ("gbp", "£"):
        return "£"
    return token


def extract_header_unit(header_text: str) -> str | None:
    """Extract an explicit unit token from a column header label if present."""
    match = _HEADER_UNIT_PATTERN.search(header_text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    return normalize_unit_token(raw)


def parse_decimal_value(
    raw: str, default_locale: str = "auto"
) -> tuple[Decimal, str | None] | None:
    """
    Parse a numeric string into a Decimal and unit token without float math.

    Handles:
    - Locale separators (1,234.56 vs 1.234,56 vs 1 234.56)
    - Accounting negative parentheses: (123.45) -> -123.45
    - Units (e.g. 120 MPa, 45 kg, $500, 15%)
    """
    if not raw:
        return None
    cleaned = normalize("NFKC", raw).strip()
    if not cleaned or cleaned.lower() in _NEUTRAL_EMPTY_STRINGS:
        return None

    is_negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:].strip()
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()

    unit: str | None = None

    # Check prefix unit/currency
    prefix_match = _CURRENCY_PREFIXES.search(cleaned)
    if prefix_match:
        unit = normalize_unit_token(prefix_match.group("prefix"))
        cleaned = cleaned[prefix_match.end() :].strip()

    # Check suffix unit
    suffix_match = _UNIT_SUFFIXES.search(cleaned)
    if suffix_match:
        if unit is None:
            unit = normalize_unit_token(suffix_match.group("suffix"))
        cleaned = cleaned[: suffix_match.start()].strip()

    if not cleaned:
        return None

    # Remove internal space thousands separators (e.g. "1 234.56" -> "1234.56")
    cleaned_no_spaces = re.sub(r"(?<=\d)\s+(?=\d)", "", cleaned)

    # Check if there are illegal characters left (not digits, dot, or comma)
    if not re.match(r"^\d[\d,.]*$", cleaned_no_spaces):
        return None

    # Disambiguate separators
    has_comma = "," in cleaned_no_spaces
    has_dot = "." in cleaned_no_spaces

    if has_comma and has_dot:
        last_comma = cleaned_no_spaces.rfind(",")
        last_dot = cleaned_no_spaces.rfind(".")
        if last_comma < last_dot:
            # 1,234,567.89 -> comma is thousands, dot is decimal
            num_str = cleaned_no_spaces.replace(",", "")
        else:
            # 1.234.567,89 -> dot is thousands, comma is decimal
            num_str = cleaned_no_spaces.replace(".", "").replace(",", ".")
    elif has_comma:
        # Only comma
        comma_count = cleaned_no_spaces.count(",")
        if comma_count > 1:
            # 1,000,000 -> thousands separator
            num_str = cleaned_no_spaces.replace(",", "")
        else:
            parts = cleaned_no_spaces.split(",")
            if len(parts[1]) == 3 and default_locale not in ("de", "eu", "id"):
                # English engineering default: 1,000 is thousands separator
                num_str = cleaned_no_spaces.replace(",", "")
            else:
                # Decimal comma (e.g. 12,5 or 1,50)
                num_str = f"{parts[0]}.{parts[1]}"
    elif has_dot:
        # Only dot
        dot_count = cleaned_no_spaces.count(".")
        num_str = cleaned_no_spaces.replace(".", "") if dot_count > 1 else cleaned_no_spaces
    else:
        num_str = cleaned_no_spaces

    try:
        val = Decimal(num_str)
        if is_negative:
            val = -val
        return val, unit
    except (InvalidOperation, ValueError):
        return None


def _build_grid(table: Table) -> list[list[TableCell | None]]:
    """Convert flat table cells into a 2D row/col indexed grid."""
    if not table.cells:
        return []
    max_r = max(c.row_index + c.row_span for c in table.cells)
    max_c = max(c.col_index + c.col_span for c in table.cells)
    grid: list[list[TableCell | None]] = [[None for _ in range(max_c)] for _ in range(max_r)]
    for cell in table.cells:
        for r_offset in range(cell.row_span):
            for c_offset in range(cell.col_span):
                r = cell.row_index + r_offset
                c = cell.col_index + c_offset
                if r < max_r and c < max_c:
                    grid[r][c] = cell
    return grid
EvaluationStatus = Literal["CORRECT", "ROUNDING_BOUNDARY", "MISMATCH"]
AssertionStatus = Literal[
    "CORRECT",
    "ROUNDING_BOUNDARY",
    "MISMATCH",
    "UNIT_MISMATCH",
    "MALFORMED_ROW",
]


def _evaluate_total(
    computed_val: Decimal,
    stated_val: Decimal,
    settings: Settings,
) -> tuple[Decimal, Decimal, EvaluationStatus]:
    """Evaluate delta and tolerance according to approved policy."""
    delta = abs(computed_val - stated_val)
    tol_percent = Decimal(str(settings.TABLE_MATH_TOLERANCE_PERCENT)) / Decimal("100")
    tol_unit = Decimal(str(settings.TABLE_MATH_TOLERANCE_UNIT))
    allowed_tolerance = max(abs(stated_val) * tol_percent, tol_unit)

    status: EvaluationStatus
    if delta == Decimal("0"):
        status = "CORRECT"
    elif delta <= allowed_tolerance:
        status = "ROUNDING_BOUNDARY"
    else:
        status = "MISMATCH"
    return delta, allowed_tolerance, status


def _analyze_column_totals(
    table_idx: int,
    grid: list[list[TableCell | None]],
    settings: Settings,
) -> tuple[list[TableMathAssertion], list[TableMathFinding]]:
    """Analyze vertical column totals, subtotals, and grand totals."""
    assertions: list[TableMathAssertion] = []
    findings: list[TableMathFinding] = []

    num_rows = len(grid)
    if num_rows < 2:
        return assertions, findings
    num_cols = len(grid[0])

    # Extract header units for each column
    header_units: dict[int, str | None] = {}
    for c in range(num_cols):
        top_cell = grid[0][c]
        header_units[c] = extract_header_unit(top_cell.text) if top_cell else None

    # Find candidate summary rows (subtotal or total)
    summary_rows: list[tuple[int, TableCell, str]] = []
    for r in range(1, num_rows):
        for c in range(num_cols):
            cell = grid[r][c]
            if cell is None:
                continue
            text = cell.text.strip()
            if _GRAND_TOTAL_KEYWORDS.search(text):
                summary_rows.append((r, cell, "GRAND_TOTAL"))
                break
            if _SUBTOTAL_KEYWORDS.search(text):
                summary_rows.append((r, cell, "SUBTOTAL"))
                break
            if _TOTAL_ROW_KEYWORDS.search(text):
                summary_rows.append((r, cell, "ROW_TOTAL"))
                break

    if not summary_rows:
        return assertions, findings

    # Evaluate each summary row
    prev_boundary_row = 1  # data starts at row 1 after header
    subtotal_assertions_by_col: dict[int, list[TableMathAssertion]] = {
        c: [] for c in range(num_cols)
    }

    for sum_r, label_cell, sum_kind in summary_rows:
        label_col = label_cell.col_index

        for c in range(num_cols):
            if c == label_col:
                continue

            target_cell = grid[sum_r][c]
            if target_cell is None:
                continue

            raw_target = target_cell.text.strip()
            if not raw_target:
                continue

            parsed_target = parse_decimal_value(raw_target)
            if parsed_target is None:
                # Total row exists, but cell is unparseable or malformed
                if raw_target.lower() not in _NEUTRAL_EMPTY_STRINGS:
                    findings.append(
                        TableMathFinding(
                            kind="MALFORMED_TABLE_ROW",
                            table_index=table_idx,
                            label=label_cell.text.strip(),
                            total_location=target_cell.bbox,
                            message=(
                                f"Table {table_idx + 1} column {c + 1} total cell has "
                                f"malformed value '{raw_target}'."
                            ),
                        )
                    )
                continue

            stated_val, target_unit = parsed_target
            eff_target_unit = target_unit or header_units.get(c)

            # Determine operand rows based on scoping
            operand_cells: list[TableMathCell] = []
            has_malformed = False

            if sum_kind == "GRAND_TOTAL" and subtotal_assertions_by_col[c]:
                # Grand total sums the subtotals
                for sub_ast in subtotal_assertions_by_col[c]:
                    operand_cells.append(sub_ast.total_cell)
            else:
                # Subtotal or flat total: sum rows from prev_boundary_row to sum_r - 1
                start_r = prev_boundary_row if sum_kind == "SUBTOTAL" else 1
                for r in range(start_r, sum_r):
                    # Skip intermediate summary rows if doing flat total
                    if any(r == sr[0] for sr in summary_rows):
                        continue
                    cell_in_col = grid[r][c]
                    if cell_in_col is None:
                        continue
                    cell_text = cell_in_col.text.strip()
                    if not cell_text or cell_text.lower() in _NEUTRAL_EMPTY_STRINGS:
                        continue
                    parsed_op = parse_decimal_value(cell_text)
                    if parsed_op is None:
                        # Non-numeric text in numeric column
                        has_malformed = True
                        findings.append(
                            TableMathFinding(
                                kind="MALFORMED_TABLE_ROW",
                                table_index=table_idx,
                                label=label_cell.text.strip(),
                                total_location=target_cell.bbox,
                                operand_locations=(
                                    [cell_in_col.bbox] if cell_in_col.bbox else []
                                ),
                                message=(
                                    f"Table {table_idx + 1} row {r + 1} column {c + 1} has "
                                    f"unparseable numeric content '{cell_text}'."
                                ),
                            )
                        )
                        break

                    op_val, op_unit = parsed_op
                    eff_op_unit = op_unit or header_units.get(c)
                    operand_cells.append(
                        TableMathCell(
                            row_index=r,
                            col_index=c,
                            raw_text=cell_text,
                            numeric_value=op_val,
                            unit=eff_op_unit,
                            location=cell_in_col.bbox,
                        )
                    )

            if has_malformed:
                continue

            if not operand_cells:
                # No numeric operands found in this column
                continue

            # Check unit consistency
            unit_mismatch = False
            first_unit = operand_cells[0].unit
            for op in operand_cells[1:]:
                if op.unit != first_unit:
                    unit_mismatch = True
                    break
            if (
                not unit_mismatch
                and eff_target_unit
                and first_unit
                and eff_target_unit != first_unit
            ):
                unit_mismatch = True

            total_math_cell = TableMathCell(
                row_index=sum_r,
                col_index=c,
                raw_text=raw_target,
                numeric_value=stated_val,
                unit=eff_target_unit,
                location=target_cell.bbox,
            )

            computed_val = sum(
                (op.numeric_value or Decimal("0") for op in operand_cells),
                start=Decimal("0"),
            )
            delta, tolerance, eval_status = _evaluate_total(
                computed_val, stated_val, settings
            )
            final_status: AssertionStatus = (
                "UNIT_MISMATCH" if unit_mismatch else eval_status
            )

            assertion = TableMathAssertion(
                kind=(
                    "SUBTOTAL"
                    if sum_kind == "SUBTOTAL"
                    else "GRAND_TOTAL"
                    if sum_kind == "GRAND_TOTAL"
                    else "COLUMN_TOTAL"
                ),
                table_index=table_idx,
                label=label_cell.text.strip(),
                stated_value=stated_val,
                computed_value=computed_val,
                delta=delta,
                tolerance=tolerance,
                unit=eff_target_unit or first_unit,
                status=final_status,
                total_cell=total_math_cell,
                operand_cells=operand_cells,
            )
            assertions.append(assertion)

            if sum_kind == "SUBTOTAL":
                subtotal_assertions_by_col[c].append(assertion)

            # Generate findings if non-correct
            op_locs: list[CoordinateContract] = [
                op.location for op in operand_cells if op.location is not None
            ]

            if final_status == "MISMATCH":
                findings.append(
                    TableMathFinding(
                        kind="TABLE_MATH_MISMATCH",
                        table_index=table_idx,
                        label=label_cell.text.strip(),
                        stated_value=stated_val,
                        computed_value=computed_val,
                        delta=delta,
                        tolerance=tolerance,
                        unit=assertion.unit,
                        total_location=target_cell.bbox,
                        operand_locations=op_locs,
                        message=(
                            f"Table {table_idx + 1} column {c + 1} sum mismatch: "
                            f"stated {stated_val}, computed {computed_val} "
                            f"(delta {delta} exceeds tolerance {tolerance})."
                        ),
                    )
                )
            elif final_status == "UNIT_MISMATCH":
                findings.append(
                    TableMathFinding(
                        kind="UNIT_MISMATCH",
                        table_index=table_idx,
                        label=label_cell.text.strip(),
                        stated_value=stated_val,
                        computed_value=computed_val,
                        delta=delta,
                        tolerance=tolerance,
                        unit=assertion.unit,
                        total_location=target_cell.bbox,
                        operand_locations=op_locs,
                        message=(
                            f"Table {table_idx + 1} column {c + 1} unit mismatch: "
                            f"conflicting units among operands or total."
                        ),
                    )
                )

        if sum_kind == "SUBTOTAL":
            prev_boundary_row = sum_r + 1

    return assertions, findings


def _analyze_row_totals(
    table_idx: int,
    grid: list[list[TableCell | None]],
    settings: Settings,
) -> tuple[list[TableMathAssertion], list[TableMathFinding]]:
    """Analyze horizontal row totals (summary column at right)."""
    assertions: list[TableMathAssertion] = []
    findings: list[TableMathFinding] = []

    num_rows = len(grid)
    if num_rows < 2:
        return assertions, findings
    num_cols = len(grid[0])
    if num_cols < 3:
        return assertions, findings

    # Look for candidate total column in header row 0
    total_col_idx: int | None = None
    for c in range(num_cols - 1, -1, -1):
        cell = grid[0][c]
        if cell and _TOTAL_COL_KEYWORDS.search(cell.text):
            total_col_idx = c
            break

    if total_col_idx is None:
        return assertions, findings

    header_cell = grid[0][total_col_idx]
    col_label = header_cell.text.strip() if header_cell else "Total"
    target_unit = extract_header_unit(col_label)

    # For each data row (excluding row 0 and any summary rows)
    for r in range(1, num_rows):
        is_summary_row = False
        for c in range(num_cols):
            candidate = grid[r][c]
            if candidate is not None and _TOTAL_ROW_KEYWORDS.search(candidate.text):
                is_summary_row = True
                break
        if is_summary_row:
            continue

        target_cell = grid[r][total_col_idx]
        if target_cell is None:
            continue
        raw_target = target_cell.text.strip()
        if not raw_target or raw_target.lower() in _NEUTRAL_EMPTY_STRINGS:
            continue

        parsed_target = parse_decimal_value(raw_target)
        if parsed_target is None:
            continue

        stated_val, cell_unit = parsed_target
        eff_unit = cell_unit or target_unit

        # Collect operands in row r to the left of total_col_idx
        operand_cells: list[TableMathCell] = []
        has_malformed = False

        for c in range(total_col_idx):
            cell_in_row = grid[r][c]
            if cell_in_row is None:
                continue
            text = cell_in_row.text.strip()
            if not text or text.lower() in _NEUTRAL_EMPTY_STRINGS:
                continue
            parsed_op = parse_decimal_value(text)
            if parsed_op is None:
                # If first column is descriptive text label (e.g. "Item A"), skip
                if c == 0:
                    continue
                has_malformed = True
                break

            op_val, op_unit = parsed_op
            operand_cells.append(
                TableMathCell(
                    row_index=r,
                    col_index=c,
                    raw_text=text,
                    numeric_value=op_val,
                    unit=op_unit or eff_unit,
                    location=cell_in_row.bbox,
                )
            )

        if has_malformed or len(operand_cells) < 2:
            continue

        # Check unit consistency
        unit_mismatch = False
        first_unit = operand_cells[0].unit
        for op in operand_cells[1:]:
            if op.unit != first_unit:
                unit_mismatch = True
                break
        if (
            not unit_mismatch
            and eff_unit
            and first_unit
            and eff_unit != first_unit
        ):
            unit_mismatch = True

        total_math_cell = TableMathCell(
            row_index=r,
            col_index=total_col_idx,
            raw_text=raw_target,
            numeric_value=stated_val,
            unit=eff_unit,
            location=target_cell.bbox,
        )

        computed_val = sum(
            (op.numeric_value or Decimal("0") for op in operand_cells),
            start=Decimal("0"),
        )
        delta, tolerance, eval_status = _evaluate_total(
            computed_val, stated_val, settings
        )
        final_status: AssertionStatus = (
            "UNIT_MISMATCH" if unit_mismatch else eval_status
        )

        assertion = TableMathAssertion(
            kind="ROW_TOTAL",
            table_index=table_idx,
            label=col_label,
            stated_value=stated_val,
            computed_value=computed_val,
            delta=delta,
            tolerance=tolerance,
            unit=eff_unit or first_unit,
            status=final_status,
            total_cell=total_math_cell,
            operand_cells=operand_cells,
        )
        assertions.append(assertion)

        op_locs: list[CoordinateContract] = [
            op.location for op in operand_cells if op.location is not None
        ]

        if final_status == "MISMATCH":
            findings.append(
                TableMathFinding(
                    kind="TABLE_MATH_MISMATCH",
                    table_index=table_idx,
                    label=col_label,
                    stated_value=stated_val,
                    computed_value=computed_val,
                    delta=delta,
                    tolerance=tolerance,
                    unit=assertion.unit,
                    total_location=target_cell.bbox,
                    operand_locations=op_locs,
                    message=(
                        f"Table {table_idx + 1} row {r + 1} sum mismatch: "
                        f"stated {stated_val}, computed {computed_val} "
                        f"(delta {delta} exceeds tolerance {tolerance})."
                    ),
                )
            )
        elif final_status == "UNIT_MISMATCH":
            findings.append(
                TableMathFinding(
                    kind="UNIT_MISMATCH",
                    table_index=table_idx,
                    label=col_label,
                    stated_value=stated_val,
                    computed_value=computed_val,
                    delta=delta,
                    tolerance=tolerance,
                    unit=assertion.unit,
                    total_location=target_cell.bbox,
                    operand_locations=op_locs,
                    message=(
                        f"Table {table_idx + 1} row {r + 1} unit mismatch: "
                        f"conflicting units among operands or total."
                    ),
                )
            )

    return assertions, findings


def analyze_table_math(
    artifact: ExtractionArtifact,
    settings: Settings | None = None,
) -> TableMathAnalysis:
    """
    Perform deterministic validation of table totals across all extracted tables.

    Validates:
    - Flat table column totals
    - Horizontal row totals
    - Subtotals and grand totals
    - Configurable rounding tolerance policy
    - Unit consistency and malformed row detection
    """
    config = settings or app_settings
    all_assertions: list[TableMathAssertion] = []
    all_findings: list[TableMathFinding] = []

    for table_idx, table in enumerate(artifact.tables):
        grid = _build_grid(table)
        if not grid:
            continue

        col_assertions, col_findings = _analyze_column_totals(
            table_idx, grid, config
        )
        row_assertions, row_findings = _analyze_row_totals(
            table_idx, grid, config
        )

        all_assertions.extend(col_assertions)
        all_assertions.extend(row_assertions)
        all_findings.extend(col_findings)
        all_findings.extend(row_findings)

    return TableMathAnalysis(
        schema_version="1.0",
        rule_version="table-math/1.0.0",
        tables_analyzed=len(artifact.tables),
        assertions=all_assertions,
        findings=all_findings,
    )
