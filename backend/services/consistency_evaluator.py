"""Deterministic contradiction detection for categorical numeric bands.

The evaluator intentionally knows nothing about a particular report, asset, or
section numbering scheme.  It consumes extracted text/sections and normalized
definition tables only.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from math import isclose
from typing import Any

_NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
_VALUE = rf"[-+]?(?:{_NUMBER})"
_UNIT = r"(?:\s*(?:years?|yrs?|months?|mm|cm|days?))?"
_ID = r"(?P<id>[A-Za-z0-9_-]+)"
_BAND_RE = re.compile(
    rf"(?i)\b(?P<label>Criticality|Priority|Category|Tier)\s+{_ID}\s*"
    rf"[(:—-]\s*(?P<interval>[^)\n,;]+)"
)


@dataclass(frozen=True)
class NumericInterval:
    """A numeric interval with explicit open/closed endpoints."""

    raw_text: str
    var_name: str | None
    low: float | None
    high: float | None
    low_inclusive: bool = True
    high_inclusive: bool = True

    def overlaps_or_equals(self, other: NumericInterval) -> bool:
        if (
            self.high is not None
            and other.low is not None
            and (
                self.high < other.low
                or (
                    isclose(self.high, other.low, abs_tol=0.01)
                    and not (self.high_inclusive and other.low_inclusive)
                )
            )
        ):
            return False
        return not (
            other.high is not None
            and self.low is not None
            and (
                other.high < self.low
                or (
                    isclose(other.high, self.low, abs_tol=0.01)
                    and not (other.high_inclusive and self.low_inclusive)
                )
            )
        )

    def matches_exact(self, other: NumericInterval) -> bool:
        return (
            (
                self.low is None
                and other.low is None
                or self.low is not None
                and other.low is not None
                and isclose(self.low, other.low, abs_tol=0.01)
            )
            and (
                self.high is None
                and other.high is None
                or self.high is not None
                and other.high is not None
                and isclose(self.high, other.high, abs_tol=0.01)
            )
            and self.low_inclusive == other.low_inclusive
            and self.high_inclusive == other.high_inclusive
        )


def _num(value: str | float) -> float:
    return float(value.replace(",", ".") if isinstance(value, str) else value)


def _clean_interval_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().rstrip(".:"))


def parse_numeric_interval(text: str, var_name: str | None = None) -> NumericInterval | None:
    """Parse comparator and natural-language numeric interval forms."""
    raw = text.strip()
    clean = _clean_interval_text(raw)
    variable = var_name
    comparator_patterns = (
        (
            rf"(?P<low>{_VALUE})\s*(?P<lop><|<=)\s*(?P<var>[A-Za-z][\w-]*)\s*(?P<hop><|<=)\s*(?P<high>{_VALUE})",
            lambda m: (m["low"], m["high"], m["lop"] == "<=", m["hop"] == "<="),
        ),
        (
            rf"(?P<var>[A-Za-z][\w-]*)\s*(?P<op><=|>=|<|>)\s*(?P<value>{_VALUE})",
            lambda m: (None, m["value"], False, m["op"] in ("<=", "<")),
        ),
        (
            rf"(?P<value>{_VALUE})\s*(?P<op><=|<)\s*(?P<var>[A-Za-z][\w-]*)",
            lambda m: (m["value"], None, m["op"] == "<", True),
        ),
    )
    for pattern, bounds in comparator_patterns:
        match = re.fullmatch(pattern + _UNIT, clean, re.IGNORECASE)
        if match:
            low, high, low_inc, high_inc = bounds(match)
            variable = variable or match.groupdict().get("var")
            op = match.groupdict().get("op")
            if op in ("<=", "<", ">=", ">") and match.groupdict().get("value"):
                value = _num(match["value"])
                if op in ("<=", "<"):
                    low, high, low_inc, high_inc = None, value, True, op == "<="
                else:
                    low, high, low_inc, high_inc = value, None, op == ">=", True
            return NumericInterval(
                raw,
                variable,
                _num(low) if low is not None else None,
                _num(high) if high is not None else None,
                low_inc,
                high_inc,
            )

    natural = (
        rf"(?P<low>{_VALUE})\s*(?:to|[-–—])\s*(?P<high>{_VALUE}){_UNIT}",
        rf"between\s+(?P<low>{_VALUE})\s+and\s+(?P<high>{_VALUE}){_UNIT}",
    )
    for pattern in natural:
        match = re.fullmatch(pattern, clean, re.IGNORECASE)
        if match:
            return NumericInterval(
                raw, variable, _num(match["low"]), _num(match["high"]), True, True
            )
    words = (
        (rf"greater than(?: or equal to)?\s+(?P<value>{_VALUE}){_UNIT}", "low"),
        (rf"less than(?: or equal to)?\s+(?P<value>{_VALUE}){_UNIT}", "high"),
    )
    for pattern, side in words:
        match = re.fullmatch(pattern, clean, re.IGNORECASE)
        if match:
            value = _num(match["value"])
            inclusive = "or equal" in clean.lower()
            return NumericInterval(
                raw,
                variable,
                value if side == "low" else None,
                value if side == "high" else None,
                inclusive if side == "low" else True,
                inclusive if side == "high" else True,
            )
    return None


def _table_rows(table: Any) -> tuple[str, list[list[str]]]:
    cells = table.get("cells", []) if isinstance(table, dict) else getattr(table, "cells", [])
    rows: dict[int, list[tuple[int, str]]] = {}
    for cell in cells:
        row = cell.get("row_index", 0) if isinstance(cell, dict) else cell.row_index
        col = cell.get("col_index", 0) if isinstance(cell, dict) else cell.col_index
        text = cell.get("text", "") if isinstance(cell, dict) else cell.text
        rows.setdefault(row, []).append((col, str(text)))
    values = [[text for _, text in sorted(items)] for _, items in sorted(rows.items())]
    header = " ".join(values[0]) if values else ""
    return header, values


def harvest_definition_tables(
    extracted_tables: Iterable[Any],
) -> dict[str, dict[str, NumericInterval]]:
    """Find definition tables from semantic headers and return dynamic mappings."""
    result: dict[str, dict[str, NumericInterval]] = {}
    keywords = ("criticality", "priority", "category", "risk band", "classification", "definition")
    columns = ("remaining life", "rul", "range", "criteria", "interval", "years")
    for table in extracted_tables:
        header, rows = _table_rows(table)
        lowered = header.lower()
        if not any(key in lowered for key in keywords) or not any(
            key in lowered for key in columns
        ):
            continue
        entity = next((key for key in keywords if key in lowered), "category")
        for row in rows[1:]:
            if len(row) < 2:
                continue
            category_id = row[0].strip()
            interval = next(
                (
                    parse_numeric_interval(value, entity)
                    for value in row[1:]
                    if parse_numeric_interval(value, entity)
                ),
                None,
            )
            if category_id and interval:
                result.setdefault(entity, {})[category_id] = interval
    return result


@dataclass(frozen=True)
class DocumentSection:
    name: str
    text: str
    page: int | str | None = None


@dataclass(frozen=True)
class ConsistencyIssue:
    severity: str
    rule: str
    where: str
    what_it_says: str
    what_body_has: str | None = None
    why_it_matters: str = "Category bands must be unique and consistent throughout the document."
    what_would_fix_it: str = (
        "Correct the category interval and regenerate the affected summary/conclusion."
    )
    evidence: dict[str, Any] = field(default_factory=dict)


def _sections(value: Any) -> list[DocumentSection]:
    if isinstance(value, dict):
        value = value.get("sections", value)
    if isinstance(value, str):
        return [DocumentSection("Document", value)]
    result = []
    for key, item in value.items() if isinstance(value, dict) else enumerate(value or []):
        if isinstance(item, DocumentSection):
            result.append(item)
        elif isinstance(item, dict):
            result.append(
                DocumentSection(
                    str(item.get("name", key)), str(item.get("text", "")), item.get("page")
                )
            )
        else:
            result.append(DocumentSection(str(key), str(item)))
    return result


def is_closure_or_summary(name: str, text: str = "") -> bool:
    return bool(
        re.search(r"(?i)\b(executive\s+summary|conclusions?|closure|summary)\b", f"{name} {text}")
    )


def detect_category_band_contradictions(
    doc_sections: Any, ground_truth: dict[str, dict[str, NumericInterval]]
) -> list[ConsistencyIssue]:
    """Return deterministic Layer A duplicate-band and Layer B mismatch findings."""
    issues: list[ConsistencyIssue] = []
    for section in _sections(doc_sections):
        if not is_closure_or_summary(section.name, section.text):
            continue
        matches = list(_BAND_RE.finditer(section.text))
        parsed = [
            (match, parse_numeric_interval(match.group("interval"), match.group("label")))
            for match in matches
        ]
        parsed = [(match, interval) for match, interval in parsed if interval]
        for index, (left_match, left) in enumerate(parsed):
            for right_match, right in parsed[index + 1 :]:
                if (
                    left_match.group("label").lower() == right_match.group("label").lower()
                    and left_match.group("id") != right_match.group("id")
                    and left.matches_exact(right)
                ):
                    issues.append(
                        ConsistencyIssue(
                            "BLOCKER",
                            "DUPLICATE_CATEGORY_BAND",
                            f"{section.name} (page {section.page or 'unlabeled'})",
                            section.text,
                            why_it_matters=(
                                "Different category IDs cannot share the same band because "
                                "the classification becomes ambiguous."
                            ),
                            evidence={
                                "category_ids": [left_match.group("id"), right_match.group("id")],
                                "interval": left.raw_text,
                            },
                        )
                    )
        for match, narrative in parsed:
            entity = match.group("label").lower()
            expected = ground_truth.get(entity, {}).get(match.group("id"))
            if expected and not narrative.matches_exact(expected):
                issues.append(
                    ConsistencyIssue(
                        "BLOCKER",
                        "CATEGORY_BAND_CONTRADICTION",
                        f"{section.name} (page {section.page or 'unlabeled'})",
                        match.group(0),
                        f"{entity} {match.group('id')} = {expected.raw_text}",
                        evidence={
                            "entity": entity,
                            "category_id": match.group("id"),
                            "narrative": narrative.raw_text,
                            "ground_truth": expected.raw_text,
                        },
                    )
                )
    return issues
