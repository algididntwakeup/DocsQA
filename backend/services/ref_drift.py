"""Deterministic reference drift detection service (F11)."""

from __future__ import annotations

import re
from unicodedata import normalize

from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.ref_drift import (
    ActualTarget,
    RefDriftAnalysis,
    RefDriftFinding,
    TocEntry,
)

# ── Roman numeral helpers ──────────────────────────────────────────────────
_ROMAN_MAP: list[tuple[int, str]] = [
    (1000, "m"),
    (900, "cm"),
    (500, "d"),
    (400, "cd"),
    (100, "c"),
    (90, "xc"),
    (50, "l"),
    (40, "xl"),
    (10, "x"),
    (9, "ix"),
    (5, "v"),
    (4, "iv"),
    (1, "i"),
]

_ROMAN_VALS: dict[str, int] = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}

_ROMAN_REGEX = re.compile(
    r"^m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})$",
    re.IGNORECASE,
)


def roman_to_int(s: str) -> int | None:
    """Convert a roman numeral string to an integer, or None if invalid."""
    clean = s.strip().lower()
    if not clean or not _ROMAN_REGEX.match(clean):
        return None
    total = 0
    prev_val = 0
    for char in reversed(clean):
        val = _ROMAN_VALS.get(char, 0)
        if val < prev_val:
            total -= val
        else:
            total += val
        prev_val = val
    return total if total > 0 else None


def int_to_roman(n: int) -> str:
    """Convert an integer to a lowercase roman numeral."""
    if n <= 0:
        return str(n)
    result: list[str] = []
    num = n
    for val, sym in _ROMAN_MAP:
        while num >= val:
            result.append(sym)
            num -= val
    return "".join(result)


def parse_page_token(token: str) -> tuple[str, int | None]:
    """Parse a page token into (normalized_label, numeric_value)."""
    clean = token.strip()
    if clean.isdigit():
        return clean, int(clean)
    roman_val = roman_to_int(clean)
    if roman_val is not None:
        return clean.lower(), roman_val
    return clean, None


# ── Section and Entry Detection Patterns ───────────────────────────────────

_TOC_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:TABLE\s+OF\s+CONTENTS|CONTENTS|TOC)\b",
    re.IGNORECASE,
)
_LOF_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:LIST\s+OF\s+FIGURES|FIGURES|LOF)\b",
    re.IGNORECASE,
)
_LOT_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:LIST\s+OF\s+TABLES|TABLES|LOT)\b",
    re.IGNORECASE,
)

_ENTRY_LINE_PATTERN = re.compile(
    r"^(?P<title>.+?)(?:[\.\s\t_–—]{2,}|\s{2,}|\t+)(?P<page>[ivxlcdm]+|\d+)\s*$",
    re.IGNORECASE,
)


def normalize_title(text: str) -> str:
    """Normalize a section heading or caption title for robust comparison."""
    norm = normalize("NFKC", text).strip().lower()
    # Remove leader dots or trailing punctuation
    norm = re.sub(r"[\.\s_–—]+$", "", norm)
    # Collapse multiple whitespace
    norm = re.sub(r"\s+", " ", norm)
    return norm


def _get_page_label(page_index: int, artifact: ExtractionArtifact) -> str:
    """Retrieve human-facing page label for a 0-based page index."""
    if page_index < len(artifact.pages):
        label = artifact.pages[page_index].page_label
        if label:
            return label.strip()
    return str(page_index + 1)


def _collect_toc_entries(
    artifact: ExtractionArtifact,
) -> list[TocEntry]:
    """Identify ToC, LoF, and LoT sections and extract structured entries."""
    entries: list[TocEntry] = []

    # Identify pages containing ToC / LoF / LoT headings
    list_sections: list[tuple[int, str, CoordinateContract]] = []
    for heading in artifact.headings:
        text = heading.text.strip()
        if _TOC_HEADING_PATTERN.search(text):
            list_sections.append((heading.bbox.page_index, "TOC", heading.bbox))
        elif _LOF_HEADING_PATTERN.search(text):
            list_sections.append((heading.bbox.page_index, "LOF", heading.bbox))
        elif _LOT_HEADING_PATTERN.search(text):
            list_sections.append((heading.bbox.page_index, "LOT", heading.bbox))

    # Also check spans if not flagged as headings
    if not list_sections:
        for span in artifact.spans:
            text = span.text.strip()
            if _TOC_HEADING_PATTERN.search(text):
                list_sections.append((span.bbox.page_index, "TOC", span.bbox))
            elif _LOF_HEADING_PATTERN.search(text):
                list_sections.append((span.bbox.page_index, "LOF", span.bbox))
            elif _LOT_HEADING_PATTERN.search(text):
                list_sections.append((span.bbox.page_index, "LOT", span.bbox))

    if not list_sections:
        return entries

    # Scan spans in each list section
    for start_page, list_type, _hdr_box in list_sections:
        for span in artifact.spans:
            if span.bbox.page_index != start_page:
                continue
            line = span.text.strip()
            # Ignore the section heading itself
            if (
                _TOC_HEADING_PATTERN.search(line)
                or _LOF_HEADING_PATTERN.search(line)
                or _LOT_HEADING_PATTERN.search(line)
            ):
                continue

            match = _ENTRY_LINE_PATTERN.match(line)
            if not match:
                continue

            title_part = match.group("title").strip()
            page_part = match.group("page").strip()
            page_label, page_num = parse_page_token(page_part)

            entries.append(
                TocEntry(
                    source_list=list_type,  # type: ignore[arg-type]
                    raw_text=line,
                    normalized_title=normalize_title(title_part),
                    referenced_page_label=page_label,
                    referenced_page_number=page_num,
                    location=span.bbox,
                )
            )

    return entries


def _collect_actual_targets(
    artifact: ExtractionArtifact,
    toc_pages: set[int],
) -> list[ActualTarget]:
    """Collect candidate actual headings and captions outside ToC pages."""
    targets: list[ActualTarget] = []

    # Collect from headings
    for heading in artifact.headings:
        if heading.bbox.page_index in toc_pages:
            continue
        text = heading.text.strip()
        if not text:
            continue
        page_idx = heading.bbox.page_index
        page_label = _get_page_label(page_idx, artifact)
        targets.append(
            ActualTarget(
                title=text,
                normalized_title=normalize_title(text),
                actual_page_index=page_idx,
                actual_page_label=page_label,
                location=heading.bbox,
            )
        )

    # Collect figures and tables from spans
    fig_tbl_regex = re.compile(
        r"^\s*(?:FIGURE|FIG\.?|TABLE)\s+\d+(?:[\.\-:\s].*)?$",
        re.IGNORECASE,
    )
    for span in artifact.spans:
        if span.bbox.page_index in toc_pages:
            continue
        text = span.text.strip()
        if fig_tbl_regex.match(text):
            page_idx = span.bbox.page_index
            page_label = _get_page_label(page_idx, artifact)
            targets.append(
                ActualTarget(
                    title=text,
                    normalized_title=normalize_title(text),
                    actual_page_index=page_idx,
                    actual_page_label=page_label,
                    location=span.bbox,
                )
            )

    return targets


def _find_matching_target(
    entry: TocEntry,
    targets: list[ActualTarget],
) -> tuple[ActualTarget | None, bool]:
    """
    Find matching target for a ToC entry.

    Returns (target, is_duplicate).
    """
    matches: list[ActualTarget] = []

    entry_norm = entry.normalized_title

    # 1. Exact title match
    for target in targets:
        if target.normalized_title == entry_norm:
            matches.append(target)

    # 2. If no exact match, prefix or subtitle match
    if not matches:
        for target in targets:
            if target.normalized_title.startswith(entry_norm) or entry_norm.startswith(
                target.normalized_title
            ):
                matches.append(target)

    # 3. Section number match (e.g. "1.1 " or "Figure 1:")
    if not matches:
        prefix_match = re.match(
            r"^(?:(?:figure|fig\.?|table|section)\s+)?(\d+(?:\.\d+)*\b)",
            entry_norm,
        )
        if prefix_match:
            sec_num = prefix_match.group(1)
            for target in targets:
                target_prefix = re.match(
                    r"^(?:(?:figure|fig\.?|table|section)\s+)?(\d+(?:\.\d+)*\b)",
                    target.normalized_title,
                )
                if target_prefix and target_prefix.group(1) == sec_num:
                    matches.append(target)

    if not matches:
        return None, False

    # Check for duplicate captions on different pages
    unique_pages = {m.actual_page_index for m in matches}
    if len(matches) > 1 and len(unique_pages) > 1:
        return matches[0], True

    return matches[0], False


def analyze_ref_drift(
    artifact: ExtractionArtifact,
) -> RefDriftAnalysis:
    """
    Perform deterministic reference drift validation across ToC, LoF, and LoT.

    Validates:
    - Stated referenced page vs actual target location
    - Front-matter roman numeral and body page numbering
    - Reports page_delta and dual navigation locations
    - Flags REF_DRIFT, MISSING_TARGET, and DUPLICATE_CAPTION
    """
    toc_entries = _collect_toc_entries(artifact)
    if not toc_entries:
        return RefDriftAnalysis(
            schema_version="1.0",
            rule_version="ref-drift/1.0.0",
            toc_entries_found=0,
            entries=[],
            findings=[],
        )

    toc_pages = {entry.location.page_index for entry in toc_entries}
    actual_targets = _collect_actual_targets(artifact, toc_pages)

    findings: list[RefDriftFinding] = []

    for entry in toc_entries:
        target, is_duplicate = _find_matching_target(entry, actual_targets)

        if is_duplicate:
            findings.append(
                RefDriftFinding(
                    kind="DUPLICATE_CAPTION",
                    label=entry.raw_text,
                    source_list=entry.source_list,
                    referenced_page_label=entry.referenced_page_label,
                    actual_page_label=target.actual_page_label if target else None,
                    entry_location=entry.location,
                    target_location=target.location if target else None,
                    message=(
                        f"Entry '{entry.raw_text}' has multiple duplicate target "
                        f"headings/captions in the document."
                    ),
                )
            )
            continue

        if target is None:
            findings.append(
                RefDriftFinding(
                    kind="MISSING_TARGET",
                    label=entry.raw_text,
                    source_list=entry.source_list,
                    referenced_page_label=entry.referenced_page_label,
                    entry_location=entry.location,
                    message=(
                        f"Referenced entry '{entry.raw_text}' could not be located "
                        f"in the document body."
                    ),
                )
            )
            continue

        # Compare referenced vs actual page
        ref_num = entry.referenced_page_number
        actual_label, actual_num = parse_page_token(target.actual_page_label)

        if ref_num is not None and actual_num is not None:
            page_delta = actual_num - ref_num
        elif entry.referenced_page_label.lower() != actual_label.lower():
            page_delta = 1
        else:
            page_delta = 0

        if page_delta != 0:
            findings.append(
                RefDriftFinding(
                    kind="REF_DRIFT",
                    label=entry.raw_text,
                    source_list=entry.source_list,
                    referenced_page_label=entry.referenced_page_label,
                    actual_page_label=target.actual_page_label,
                    page_delta=page_delta,
                    entry_location=entry.location,
                    target_location=target.location,
                    message=(
                        f"Reference drift detected for '{entry.raw_text}': "
                        f"referenced page {entry.referenced_page_label}, "
                        f"actual page {target.actual_page_label} "
                        f"(drift {page_delta:+d} pages)."
                    ),
                )
            )

    return RefDriftAnalysis(
        schema_version="1.0",
        rule_version="ref-drift/1.0.0",
        toc_entries_found=len(toc_entries),
        entries=toc_entries,
        findings=findings,
    )
