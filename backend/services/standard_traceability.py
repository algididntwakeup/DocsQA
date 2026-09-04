"""Deterministic body-citation to bibliography traceability checks (F13)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern
from typing import Literal

from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.standard_traceability import (
    StandardCitation,
    StandardFinding,
    StandardTraceabilityAnalysis,
)

StandardFamily = Literal["ASME", "API", "ASTM", "ISO"]


@dataclass(frozen=True, slots=True)
class StandardPattern:
    """One bounded, reviewed pattern in the built-in standards registry."""

    family: StandardFamily
    expression: Pattern[str]


def _compile(expression: str) -> Pattern[str]:
    return re.compile(expression, re.IGNORECASE)


STANDARD_PATTERNS = (
    StandardPattern(
        "ASME",
        _compile(
            r"\b(?P<code>ASME\s+(?:(?:SEC(?:TION)?\.?)\s*)?[IVXLCDM]+"
            r"(?:\s+(?:DIV(?:ISION)?\.?)\s*\d+)?)"
            r"(?:\s*[-:,(]\s*(?P<year>(?:19|20)\d{2})\)?)?\b"
        ),
    ),
    StandardPattern(
        "API",
        _compile(
            r"\b(?P<code>API\s+(?:(?P<qualifier>STD|SPEC|RP)\s+)?"
            r"(?P<api_number>\d{1,4}[A-Z]?))"
            r"(?:\s*[-:,(]\s*(?P<year>(?:19|20)\d{2})\)?)?\b"
        ),
    ),
    StandardPattern(
        "ASTM",
        _compile(
            r"\b(?P<code>ASTM\s+[A-Z]\d{1,4}(?:/[A-Z]\d{1,4})?M?)"
            r"(?:\s*[-:,(]\s*(?P<year>(?:19|20)\d{2})\)?)?\b"
        ),
    ),
    StandardPattern(
        "ISO",
        _compile(
            r"\b(?P<code>(?:EN\s+)?ISO\s+\d{3,6}(?:-\d+)?)"
            r"(?:\s*[-:,(]\s*(?P<year>(?:19|20)\d{2})\)?)?\b"
        ),
    ),
)

_REFERENCE_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*\s+)?(?:NORMATIVE\s+)?(?:REFERENCES?|BIBLIOGRAPHY|CODES?\s+AND\s+STANDARDS?)$",
    re.IGNORECASE,
)
_KNOWN_BARE_API_CODES = {"510", "570", "579", "650", "653", "1104", "5L", "6A"}


def normalize_standard_code(value: str) -> str:
    """Normalize spacing and common labels while preserving standard identity."""

    normalized = re.sub(r"[.,]$", "", value.upper().strip())
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\bSEC(?:TION)?\.?\s*", "SECTION ", normalized)
    normalized = re.sub(r"\bDIV(?:ISION)?\.?\s*", "DIVISION ", normalized)
    return normalized.replace("EN ISO ", "ISO ", 1)


def _ordered_items(
    artifact: ExtractionArtifact,
) -> list[tuple[str, CoordinateContract, bool]]:
    items = [(span.text, span.bbox, False) for span in artifact.spans]
    items.extend((heading.text, heading.bbox, True) for heading in artifact.headings)
    return sorted(items, key=lambda item: (item[1].page_index, item[1].y0, item[1].x0))


def _is_ambiguous_api(match: re.Match[str]) -> bool:
    qualifier = match.groupdict().get("qualifier")
    number = (match.groupdict().get("api_number") or "").upper()
    return qualifier is None and number not in _KNOWN_BARE_API_CODES


def _extract_from_text(
    text: str,
    location: CoordinateContract,
    section: Literal["BODY", "REFERENCE"],
) -> list[StandardCitation]:
    citations: list[StandardCitation] = []
    for registered in STANDARD_PATTERNS:
        for match in registered.expression.finditer(text):
            raw = match.group(0).strip(" ,.;")
            year_text = match.groupdict().get("year")
            citations.append(
                StandardCitation(
                    family=registered.family,
                    raw_text=raw,
                    normalized_code=normalize_standard_code(match.group("code")),
                    edition_year=int(year_text) if year_text else None,
                    section=section,
                    location=location,
                    ambiguous=registered.family == "API" and _is_ambiguous_api(match),
                )
            )
    return citations


def extract_standard_citations(
    artifact: ExtractionArtifact,
) -> tuple[list[StandardCitation], list[StandardCitation], bool]:
    """Partition citations using the first explicit bibliography heading."""

    body: list[StandardCitation] = []
    references: list[StandardCitation] = []
    in_references = False
    reference_found = False
    for text, location, is_heading in _ordered_items(artifact):
        if _REFERENCE_HEADING.fullmatch(text.strip()) and (is_heading or len(text) <= 80):
            in_references = True
            reference_found = True
            continue
        section: Literal["BODY", "REFERENCE"] = "REFERENCE" if in_references else "BODY"
        target = references if in_references else body
        target.extend(_extract_from_text(text, location, section))
    return body, references, reference_found


def _deduplicate_findings(findings: list[StandardFinding]) -> list[StandardFinding]:
    seen: set[tuple[str, str, int | None]] = set()
    unique: list[StandardFinding] = []
    for finding in findings:
        key = (finding.kind, finding.cited_standard, finding.body_edition_year)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def analyze_standard_traceability(
    artifact: ExtractionArtifact,
) -> StandardTraceabilityAnalysis:
    """Cross-reference body standards against normalized bibliography entries."""

    body, references, reference_found = extract_standard_citations(artifact)
    by_code: dict[str, list[StandardCitation]] = {}
    for citation in references:
        by_code.setdefault(citation.normalized_code, []).append(citation)

    findings: list[StandardFinding] = []
    for citation in body:
        if citation.ambiguous:
            findings.append(
                StandardFinding(
                    kind="AMBIGUOUS_STANDARD",
                    cited_standard=citation.normalized_code,
                    body_edition_year=citation.edition_year,
                    body_location=citation.location,
                )
            )
            continue
        matches = by_code.get(citation.normalized_code, [])
        if not matches:
            findings.append(
                StandardFinding(
                    kind="STANDARD_NOT_IN_BIBLIOGRAPHY",
                    cited_standard=citation.normalized_code,
                    body_edition_year=citation.edition_year,
                    body_location=citation.location,
                )
            )
            continue
        reference = matches[0]
        reference_years = {item.edition_year for item in matches if item.edition_year}
        if (
            citation.edition_year
            and reference_years
            and citation.edition_year not in reference_years
        ):
            findings.append(
                StandardFinding(
                    kind="EDITION_YEAR_MISMATCH",
                    cited_standard=citation.normalized_code,
                    body_edition_year=citation.edition_year,
                    bibliography_entry=reference.raw_text,
                    bibliography_edition_year=reference.edition_year,
                    body_location=citation.location,
                    bibliography_location=reference.location,
                )
            )

    return StandardTraceabilityAnalysis(
        reference_section_found=reference_found,
        body_citations=body,
        reference_entries=references,
        findings=_deduplicate_findings(findings),
    )
