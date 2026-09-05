"""Versioned evidence emitted by deterministic table math validation (F10)."""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from schemas.base import ApiModel
from schemas.extraction import CoordinateContract


class TableMathCell(ApiModel):
    """Normalized cell representation for numeric analysis."""

    row_index: int = Field(ge=0)
    col_index: int = Field(ge=0)
    raw_text: str
    numeric_value: Decimal | None = None
    unit: str | None = None
    location: CoordinateContract | None = None


class TableMathAssertion(ApiModel):
    """One audited mathematical relationship between operands and a stated total."""

    kind: Literal["ROW_TOTAL", "COLUMN_TOTAL", "SUBTOTAL", "GRAND_TOTAL"]
    table_index: int = Field(ge=0)
    label: str | None = None
    stated_value: Decimal
    computed_value: Decimal
    delta: Decimal
    tolerance: Decimal
    unit: str | None = None
    status: Literal[
        "CORRECT",
        "ROUNDING_BOUNDARY",
        "MISMATCH",
        "UNIT_MISMATCH",
        "MALFORMED_ROW",
    ]
    total_cell: TableMathCell
    operand_cells: list[TableMathCell] = Field(default_factory=list)


class TableMathFinding(ApiModel):
    """An actionable finding to be surfaced or aggregated into issues."""

    kind: Literal[
        "TABLE_MATH_MISMATCH",
        "TOTAL_NOT_FOUND",
        "UNIT_MISMATCH",
        "MALFORMED_TABLE_ROW",
    ]
    table_index: int = Field(ge=0)
    label: str | None = None
    stated_value: Decimal | None = None
    computed_value: Decimal | None = None
    delta: Decimal | None = None
    tolerance: Decimal | None = None
    unit: str | None = None
    total_location: CoordinateContract | None = None
    operand_locations: list[CoordinateContract] = Field(default_factory=list)
    message: str


class TableMathAnalysis(ApiModel):
    """Complete versioned artifact persisted for the table math stage."""

    schema_version: str = "1.0"
    rule_version: str = "table-math/1.0.0"
    tables_analyzed: int = 0
    assertions: list[TableMathAssertion] = Field(default_factory=list)
    findings: list[TableMathFinding] = Field(default_factory=list)
