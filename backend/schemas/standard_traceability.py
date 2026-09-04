"""Versioned evidence for deterministic standards traceability analysis."""

from typing import Literal

from pydantic import Field

from schemas.base import ApiModel
from schemas.extraction import CoordinateContract


class StandardCitation(ApiModel):
    """A normalized standard citation located in body or reference content."""

    family: Literal["ASME", "API", "ASTM", "ISO"]
    raw_text: str
    normalized_code: str
    edition_year: int | None = None
    section: Literal["BODY", "REFERENCE"]
    location: CoordinateContract
    ambiguous: bool = False


class StandardFinding(ApiModel):
    """One actionable or ambiguous body-to-bibliography comparison result."""

    kind: Literal[
        "STANDARD_NOT_IN_BIBLIOGRAPHY",
        "EDITION_YEAR_MISMATCH",
        "AMBIGUOUS_STANDARD",
    ]
    cited_standard: str
    body_edition_year: int | None = None
    bibliography_entry: str | None = None
    bibliography_edition_year: int | None = None
    body_location: CoordinateContract
    bibliography_location: CoordinateContract | None = None


class StandardTraceabilityAnalysis(ApiModel):
    """Complete versioned output consumed by later issue aggregation."""

    schema_version: str = "1.0"
    rule_version: str = "standard-traceability/1.0.0"
    reference_section_found: bool
    body_citations: list[StandardCitation] = Field(default_factory=list)
    reference_entries: list[StandardCitation] = Field(default_factory=list)
    findings: list[StandardFinding] = Field(default_factory=list)
