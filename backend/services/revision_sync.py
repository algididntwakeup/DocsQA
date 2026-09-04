"""Deterministic filename, cover, and revision-table synchronization (F12)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Literal
from unicodedata import normalize

from schemas.extraction import CoordinateContract, ExtractionArtifact, Table
from schemas.revision import RevisionAnalysis, RevisionSource, RevisionSourceName

_TOKEN = r"[A-Z0-9]{1,8}"
_FILENAME_PATTERN = re.compile(
    rf"(?:^|[\s_.-])(?:"
    rf"REVISION[\s_.-]*(?P<long>{_TOKEN})"
    rf"|REV(?:[\s_.-]+(?P<separated>{_TOKEN})|"
    rf"(?P<attached>[A-Z]|[0-9]{{1,4}})(?=$|[\s_.-])))",
    re.IGNORECASE,
)
_COVER_PATTERN = re.compile(
    rf"\b(?:DOCUMENT\s+)?REV(?:ISION)?\.?\s*(?:NO\.?|NUMBER)?\s*[:#-]?\s*({_TOKEN})\b",
    re.IGNORECASE,
)
_HEADER_PATTERN = re.compile(r"^(?:REV\.?|REVISION|REVISION\s+NO\.?)$", re.IGNORECASE)
_VALID_TOKEN = re.compile(rf"^{_TOKEN}$", re.IGNORECASE)


def normalize_revision_token(value: str | None) -> str | None:
    """Normalize a bounded revision token without inventing missing semantics."""

    if value is None:
        return None
    token = normalize("NFKC", value).strip().upper()
    token = re.sub(r"^REV(?:ISION)?\s*(?:NO\.?|NUMBER)?\s*[:#.-]?\s*", "", token)
    token = re.sub(r"[^A-Z0-9]", "", token)
    if not token or len(token) > 8:
        return None
    if token.isdigit():
        return str(int(token))
    return token


def extract_filename_revision(filename: str) -> RevisionSource:
    """Extract a revision only when the filename uses an explicit Rev marker."""

    match = _FILENAME_PATTERN.search(Path(filename).stem)
    raw = next((value for value in match.groupdict().values() if value), None) if match else None
    return RevisionSource(
        source="FILENAME",
        raw_value=raw,
        normalized_value=normalize_revision_token(raw),
    )


def _cover_items(artifact: ExtractionArtifact) -> list[tuple[str, CoordinateContract]]:
    items = [(span.text, span.bbox) for span in artifact.spans if span.bbox.page_index == 0]
    items.extend(
        (heading.text, heading.bbox)
        for heading in artifact.headings
        if heading.bbox.page_index == 0
    )
    return sorted(items, key=lambda item: (item[1].y0, item[1].x0))


def extract_cover_revision(artifact: ExtractionArtifact) -> RevisionSource:
    """Find an explicitly labelled revision on the first canonical page."""

    items = _cover_items(artifact)
    for index, (_text, location) in enumerate(items):
        context = " ".join(item[0] for item in items[index : index + 3])
        match = _COVER_PATTERN.search(context)
        if match:
            raw = match.group(1)
            return RevisionSource(
                source="COVER",
                raw_value=raw,
                normalized_value=normalize_revision_token(raw),
                location=location,
            )
    return RevisionSource(source="COVER")


def _revision_from_table(table: Table) -> tuple[str, CoordinateContract | None] | None:
    cells = sorted(table.cells, key=lambda cell: (cell.row_index, cell.col_index))
    headers = [cell for cell in cells if _HEADER_PATTERN.fullmatch(cell.text.strip())]
    for header in headers:
        candidates = [
            cell
            for cell in cells
            if cell.col_index == header.col_index
            and cell.row_index > header.row_index
            and _VALID_TOKEN.fullmatch(cell.text.strip())
        ]
        if candidates:
            latest = max(candidates, key=lambda cell: cell.row_index)
            return latest.text.strip(), latest.bbox
    return None


def extract_revision_sheet_revision(artifact: ExtractionArtifact) -> RevisionSource:
    """Use the last valid entry below an explicit revision-table header."""

    for table in artifact.tables:
        result = _revision_from_table(table)
        if result:
            raw, location = result
            return RevisionSource(
                source="REVISION_SHEET",
                raw_value=raw,
                normalized_value=normalize_revision_token(raw),
                location=location,
            )
    return RevisionSource(source="REVISION_SHEET")


def _disagreeing_sources(sources: list[RevisionSource]) -> list[RevisionSourceName]:
    present = [source for source in sources if source.normalized_value is not None]
    counts = Counter(source.normalized_value for source in present)
    if len(counts) <= 1:
        return []
    top_value, top_count = counts.most_common(1)[0]
    if top_count == 1:
        return [source.source for source in present]
    return [source.source for source in present if source.normalized_value != top_value]


def analyze_revision(filename: str, artifact: ExtractionArtifact) -> RevisionAnalysis:
    """Compare all available revision sources and retain missing-source evidence."""

    sources = [
        extract_filename_revision(filename),
        extract_cover_revision(artifact),
        extract_revision_sheet_revision(artifact),
    ]
    missing = [source.source for source in sources if source.normalized_value is None]
    disagreeing = _disagreeing_sources(sources)
    outcome: Literal["MATCH", "MISMATCH", "INCOMPLETE"]
    outcome = "MISMATCH" if disagreeing else "INCOMPLETE" if missing else "MATCH"
    return RevisionAnalysis(
        outcome=outcome,
        sources=sources,
        sources_disagreeing=disagreeing,
        missing_sources=missing,
    )
