"""Deterministic revision-sync parser and comparison tests."""

from uuid import uuid4

import pytest

from schemas.extraction import CoordinateContract, ExtractionArtifact, Table, TableCell, TextSpan
from services.revision_sync import analyze_revision, normalize_revision_token


def _box(page: int = 0, y: float = 0) -> CoordinateContract:
    return CoordinateContract(
        page_index=page, x0=0, y0=y, x1=100, y1=y + 10, page_width=600, page_height=800
    )


def _artifact(cover: str | None, sheet: str | None) -> ExtractionArtifact:
    spans = [TextSpan(text=f"Document Revision: {cover}", bbox=_box())] if cover else []
    tables: list[Table] = []
    if sheet:
        tables.append(
            Table(
                cells=[
                    TableCell(text="REV", row_index=0, col_index=0, bbox=_box(1, 10)),
                    TableCell(text="DATE", row_index=0, col_index=1, bbox=_box(1, 10)),
                    TableCell(text="A", row_index=1, col_index=0, bbox=_box(1, 20)),
                    TableCell(text=sheet, row_index=2, col_index=0, bbox=_box(1, 30)),
                ]
            )
        )
    return ExtractionArtifact(document_id=uuid4(), spans=spans, tables=tables)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("rev. b", "B"), ("REVISION 003", "3"), (" A-1 ", "A1"), ("", None)],
)
def test_normalize_revision_token(raw: str, expected: str | None) -> None:
    assert normalize_revision_token(raw) == expected


def test_three_sources_match() -> None:
    result = analyze_revision("Inspection_Report_Rev-B.pdf", _artifact("B", "B"))
    assert result.outcome == "MATCH"
    assert result.sources_disagreeing == []
    assert result.missing_sources == []


@pytest.mark.parametrize(
    ("filename", "cover", "sheet", "disagreeing"),
    [
        ("Report_Rev-A.pdf", "B", "B", ["FILENAME"]),
        ("Report_Rev-B.pdf", "A", "B", ["COVER"]),
        ("Report_Rev-B.pdf", "B", "A", ["REVISION_SHEET"]),
        ("Report_Rev-A.pdf", "B", "C", ["FILENAME", "COVER", "REVISION_SHEET"]),
    ],
)
def test_revision_mismatch_sources(
    filename: str, cover: str, sheet: str, disagreeing: list[str]
) -> None:
    result = analyze_revision(filename, _artifact(cover, sheet))
    assert result.outcome == "MISMATCH"
    assert result.sources_disagreeing == disagreeing


def test_missing_sources_are_incomplete() -> None:
    result = analyze_revision("Report.pdf", _artifact("A", None))
    assert result.outcome == "INCOMPLETE"
    assert result.missing_sources == ["FILENAME", "REVISION_SHEET"]


@pytest.mark.parametrize(
    "filename", ["technical_review_board.pdf", "preview_A.pdf", "Report_River.pdf"]
)
def test_filename_false_positives_are_rejected(filename: str) -> None:
    result = analyze_revision(filename, _artifact(None, None))
    assert result.sources[0].normalized_value is None
