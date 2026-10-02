"""Deterministic contradiction detection for categorical numeric bands.

The evaluator is document agnostic. It normalizes definition tables, then
checks classification/range assertions in executive summaries and conclusions
against those definitions. It does not use fixtures or a generative model.
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
_LABEL = r"(?P<label>Criticality|Priority|Category|Tier|Classification)"
_ID = r"(?P<id>[A-Za-z0-9_-]+)"
_BAND_RE = re.compile(
    rf"(?i)\b{_LABEL}\s+{_ID}\s*(?:[(:=—-]\s*)?(?P<interval>[^)\n,;]{{1,100}})"
)
_COMPONENT_RE = re.compile(
    r"(?i)\b(?P<id>(?:[A-Z0-9]{1,8}-)+[A-Z0-9]{1,12}(?:-[A-Z0-9]{1,12})*)"
    r"(?:\s+(?P<name>shell|tube|tubes|head|nozzle|vessel|pump|compressor|line|motor))?\b"
)


@dataclass(frozen=True)
class NumericInterval:
    """A numeric interval with explicit open/closed endpoints and provenance."""

    raw_text: str
    var_name: str | None
    low: float | None
    high: float | None
    low_inclusive: bool = True
    high_inclusive: bool = True
    source_page: int | str | None = None
    source_table: str | None = None

    def overlaps_or_equals(self, other: NumericInterval) -> bool:
        if self.high is not None and other.low is not None and (
            self.high < other.low
            or (isclose(self.high, other.low, abs_tol=0.01) and not (self.high_inclusive and other.low_inclusive))
        ):
            return False
        return not (
            other.high is not None and self.low is not None and (
                other.high < self.low
                or (isclose(other.high, self.low, abs_tol=0.01) and not (other.high_inclusive and self.low_inclusive))
            )
        )

    def matches_exact(self, other: NumericInterval) -> bool:
        return (
            ((self.low is None and other.low is None) or (self.low is not None and other.low is not None and isclose(self.low, other.low, abs_tol=0.01)))
            and ((self.high is None and other.high is None) or (self.high is not None and other.high is not None and isclose(self.high, other.high, abs_tol=0.01)))
            and self.low_inclusive == other.low_inclusive
            and self.high_inclusive == other.high_inclusive
        )


def _num(value: str | float) -> float:
    return float(value.replace(",", ".") if isinstance(value, str) else value)


def _clean_interval_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().rstrip(".:"))


def parse_numeric_interval(text: str, var_name: str | None = None) -> NumericInterval | None:
    """Parse comparator, range, and natural-language numeric interval forms."""
    raw = text.strip()
    clean = _clean_interval_text(raw).replace("≤", "<=").replace("≥", ">=")
    clean = re.sub(r"\s*\((?:to\s+)?\d{4}\)\s*$", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b([A-Za-z][\w-]*)\s+(\d{4})\b", r"\1\2", clean)
    variable = var_name
    comparator_patterns = (
        (rf"(?P<low>{_VALUE})\s*(?P<lop><|<=)\s*(?P<var>[A-Za-z][\w-]*)\s*(?P<hop><|<=)\s*(?P<high>{_VALUE})", lambda m: (m["low"], m["high"], m["lop"] == "<=", m["hop"] == "<=")),
        (rf"(?P<var>[A-Za-z][\w-]*)\s*(?P<op><=|>=|<|>)\s*(?P<value>{_VALUE})", lambda m: (None, m["value"], True, m["op"] == "<=")),
        (rf"(?P<value>{_VALUE})\s*(?P<op><=|<)\s*(?P<var>[A-Za-z][\w-]*)", lambda m: (m["value"], None, m["op"] == "<", True)),
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
            return NumericInterval(raw, variable, _num(low) if low is not None else None, _num(high) if high is not None else None, low_inc, high_inc)

    for pattern in (rf"(?P<low>{_VALUE})\s*(?:to|[-–—])\s*(?P<high>{_VALUE}){_UNIT}", rf"between\s+(?P<low>{_VALUE})\s+and\s+(?P<high>{_VALUE}){_UNIT}"):
        match = re.fullmatch(pattern, clean, re.IGNORECASE)
        if match:
            return NumericInterval(raw, variable, _num(match["low"]), _num(match["high"]), True, True)
    for pattern, side in ((rf"greater than(?: or equal to)?\s+(?P<value>{_VALUE}){_UNIT}", "low"), (rf"less than(?: or equal to)?\s+(?P<value>{_VALUE}){_UNIT}", "high")):
        match = re.fullmatch(pattern, clean, re.IGNORECASE)
        if match:
            value = _num(match["value"])
            inclusive = "or equal" in clean.lower()
            return NumericInterval(raw, variable, value if side == "low" else None, value if side == "high" else None, inclusive if side == "low" else True, inclusive if side == "high" else True)
    return None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _table_rows(table: Any) -> tuple[str, list[list[str]], int | None]:
    cells = _get(table, "cells", []) or []
    rows: dict[int, list[tuple[int, str]]] = {}
    for cell in cells:
        row = _get(cell, "row_index", 0)
        col = _get(cell, "col_index", 0)
        text = _get(cell, "text", "")
        rows.setdefault(int(row), []).append((int(col), str(text or "").strip()))
    values = [[text for _, text in sorted(items)] for _, items in sorted(rows.items())]
    header = " ".join(values[0]) if values else ""
    bbox = _get(table, "bbox")
    page_index = _get(bbox, "page_index") if bbox is not None else None
    return header, values, int(page_index) + 1 if page_index is not None else None


def _category_key(text: str, entity: str) -> str | None:
    clean = re.sub(r"\s+", " ", text.strip())
    match = re.search(rf"(?i)\b(?:{re.escape(entity)}\s*)?(?:class|category|level)?\s*([0-9]+[A-Za-z]?)\b", clean)
    if match:
        return match.group(1)
    # Tables often label a row simply "Criticality 2" while the header is "Criticality".
    match = re.search(r"(?i)\b(?:criticality|priority|category|tier|class)\s+([0-9]+[A-Za-z]?)\b", clean)
    return match.group(1) if match else (clean if re.fullmatch(r"[0-9]+[A-Za-z]?", clean) else None)


def harvest_definition_tables(extracted_tables: Iterable[Any]) -> dict[str, dict[str, NumericInterval]]:
    """Extract category-to-range mappings from table headers and row content."""
    result: dict[str, dict[str, NumericInterval]] = {}
    label_words = ("criticality", "priority", "category", "risk band", "classification", "tier")
    range_words = ("remaining life", "rul", "range", "criteria", "interval", "years", "year", "threshold")
    for table in extracted_tables:
        header, rows, page = _table_rows(table)
        if len(rows) < 2:
            continue
        all_text = " ".join(" ".join(row) for row in rows)
        lowered = f"{header} {all_text}".lower()
        entity = next((word for word in label_words if word in lowered), None)
        if entity is None or not any(word in lowered for word in range_words):
            continue
        for row in rows:
            if len(row) < 2:
                continue
            category_cells = [
                (index, _category_key(value, entity))
                for index, value in enumerate(row)
                if value.strip()
                and (
                    index == 0
                    or re.search(
                        r"(?i)\b(?:criticality|priority|category|tier|classification|class)\s+[0-9]+[A-Za-z]?\b",
                        value,
                    )
                )
            ]
            category_cells = [(index, category_id) for index, category_id in category_cells if category_id]
            for category_index, category_id in category_cells:
                interval = None
                candidates = [
                    index for index, value in enumerate(row)
                    if index != category_index and value.strip()
                ]
                # Table extraction often puts labels in column 2 and definitions
                # in column 4; do not assume either occupies the first column.
                for start in candidates:
                    for width in range(min(4, len(row) - start), 0, -1):
                        indices = range(start, start + width)
                        if category_index in indices:
                            continue
                        candidate = " ".join(row[index] for index in indices if row[index])
                        interval = parse_numeric_interval(candidate, entity)
                        if interval:
                            break
                    if interval:
                        break
                if interval is not None:
                    interval = NumericInterval(interval.raw_text, interval.var_name, interval.low, interval.high, interval.low_inclusive, interval.high_inclusive, page, header or None)
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
    what_would_fix_it: str = "Correct the category interval and regenerate the affected summary/conclusion."
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
            result.append(DocumentSection(str(item.get("name", key)), str(item.get("text", "")), item.get("page")))
        else:
            result.append(DocumentSection(str(key), str(item)))
    return result


def is_closure_or_summary(name: str, text: str = "") -> bool:
    return bool(re.search(r"(?i)\b(executive\s+summary|conclusions?|closure|summary)\b", f"{name} {text}"))


def _clause(text: str, start: int, end: int) -> str:
    left = max(text.rfind(mark, 0, start) for mark in (".", "!", "?", "\n")) + 1
    right_candidates = [pos for mark in (".", "!", "?", "\n") if (pos := text.find(mark, end)) >= 0]
    right = min(right_candidates) if right_candidates else len(text)
    return re.sub(r"\s+", " ", text[left:right].strip())[:500]


def detect_category_band_contradictions(doc_sections: Any, ground_truth: dict[str, dict[str, NumericInterval]]) -> list[ConsistencyIssue]:
    """Return duplicate-band and summary/conclusion-to-table contradiction findings."""
    issues: list[ConsistencyIssue] = []
    seen: set[tuple[str, str, str, str]] = set()
    for section in _sections(doc_sections):
        if not is_closure_or_summary(section.name):
            continue
        matches = list(_BAND_RE.finditer(section.text))
        parsed: list[tuple[re.Match[str], NumericInterval]] = []
        for match in matches:
            interval = parse_numeric_interval(match.group("interval"), match.group("label"))
            if interval is not None:
                parsed.append((match, interval))
        for index, (left_match, left) in enumerate(parsed):
            for right_match, right in parsed[index + 1 :]:
                if left_match.group("label").lower() == right_match.group("label").lower() and left_match.group("id") != right_match.group("id") and left.matches_exact(right):
                    definitions = ground_truth.get(left_match.group("label").lower(), {})
                    left_definition = definitions.get(left_match.group("id"))
                    right_definition = definitions.get(right_match.group("id"))
                    if (
                        left_definition is not None
                        and right_definition is not None
                        and (
                            not left.matches_exact(left_definition)
                            or not right.matches_exact(right_definition)
                        )
                    ):
                        # The table-aware cross-check below gives a more precise
                        # component-specific blocker for a repeated narrative band.
                        continue
                    clause = _clause(section.text, left_match.start(), right_match.end())
                    key = ("DUPLICATE_CATEGORY_BAND", section.name, left_match.group("id"), right_match.group("id"))
                    if key not in seen:
                        seen.add(key)
                        issues.append(ConsistencyIssue("BLOCKER", "DUPLICATE_CATEGORY_BAND", f"{section.name} (page {section.page or 'unlabeled'})", clause, f"{left_match.group('label')} {left_match.group('id')} and {right_match.group('id')} both use {left.raw_text}", "Different classification IDs share one interval, making component prioritization ambiguous.", "Reconcile the category definitions and correct the duplicate band in the summary and source table.", {"category_ids": [left_match.group("id"), right_match.group("id")], "interval": left.raw_text, "page": section.page}))

        for match, narrative in parsed:
            entity, category_id = match.group("label").lower(), match.group("id")
            expected = ground_truth.get(entity, {}).get(category_id)
            if expected is None:
                continue
            if narrative.matches_exact(expected):
                continue
            clause = re.sub(
                r"\s+\d{1,2}$", "", _clause(section.text, match.start(), match.end())
            )
            component = _COMPONENT_RE.search(clause)
            component_name = " ".join(part for part in (component.group("id"), component.group("name")) if part) if component else None
            subject = f" for {component_name}" if component_name else ""
            where = f"{section.name}{subject} (page {section.page or 'unlabeled'})"
            body_has = f"Definition table states {entity.title()} {category_id} = {expected.raw_text}"
            if expected.source_page:
                body_has += f" (PDF page {expected.source_page})"
            key = ("CATEGORY_BAND_CONTRADICTION", section.name, category_id, clause.lower())
            if key in seen:
                continue
            seen.add(key)
            issues.append(ConsistencyIssue(
                "BLOCKER", "CATEGORY_BAND_CONTRADICTION", where, clause, body_has,
                f"The stated range conflicts with the governing {entity} definition, which can assign the component to the wrong risk class and change its required inspection or mitigation priority.",
                f"Verify the component's measured remaining life, apply the table's {entity.title()} {category_id} band ({expected.raw_text}), then correct the conclusion or the governing definition and update dependent summaries.",
                {"entity": entity, "category_id": category_id, "narrative": narrative.raw_text, "ground_truth": expected.raw_text, "component": component_name, "page": section.page, "definition_page": expected.source_page},
            ))
    return issues
