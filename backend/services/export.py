"""Export Service for Annotated PDF.

Generates:
Annotated PDF with visual bounding boxes and callout notes for included findings.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import pypdf
from pypdf.annotations import Rectangle, Text

if TYPE_CHECKING:
    from models.document import Document
    from models.issue import Issue
    from services.storage.local import LocalStorage


def _extract_locations(
    evidence: dict[str, Any] | None,
) -> list[tuple[int, float, float, float, float, float, float]]:
    """Extract location tuples (page_index, x0, y0, x1, y1, page_width, page_height)."""
    if not evidence or not isinstance(evidence, dict):
        return []

    results: list[tuple[int, float, float, float, float, float, float]] = []

    def _parse_box(box: Any) -> tuple[int, float, float, float, float, float, float] | None:
        if not isinstance(box, dict):
            return None
        page_index = int(box.get("page_index", 0))
        x0 = float(box.get("x0", 0.0))
        y0 = float(box.get("y0", 0.0))
        x1 = float(box.get("x1", 0.0))
        y1 = float(box.get("y1", 0.0))
        pw = float(box.get("page_width", 612.0)) or 612.0
        ph = float(box.get("page_height", 792.0)) or 792.0
        return (page_index, x0, y0, x1, y1, pw, ph)

    for key in (
        "total_location",
        "body_location",
        "entry_location",
        "location",
        "target_location",
        "bibliography_location",
        "original_location",
    ):
        if key in evidence and evidence[key]:
            parsed = _parse_box(evidence[key])
            if parsed:
                results.append(parsed)

    # Handle location list keys (e.g. operand_locations or locations)
    for list_key in ("operand_locations", "locations"):
        val = evidence.get(list_key)
        if isinstance(val, list):
            for item in val:
                parsed = _parse_box(item)
                if parsed:
                    results.append(parsed)

    return results


def export_annotated_pdf(
    document: Document,
    issues: list[Issue],
    storage: LocalStorage,
) -> bytes:
    """Generate an annotated PDF with highlighted bounding boxes and callout popups."""
    writer = pypdf.PdfWriter()

    # Attempt to read original PDF from storage
    uri = document.canonical_pdf_uri or document.storage_uri
    source_pdf_bytes: bytes | None = None
    if uri:
        key = uri
        if key.startswith(storage.scheme):
            key = key[len(storage.scheme) :]
        path = storage._path_for_key(key)
        if path.exists():
            try:
                source_pdf_bytes = path.read_bytes()
            except OSError:
                source_pdf_bytes = None

    if source_pdf_bytes:
        reader = pypdf.PdfReader(io.BytesIO(source_pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    else:
        # Fallback: create empty page(s) matching issues' maximum page count
        max_page = 0
        for issue in issues:
            for p_idx, _, _, _, _, _, _ in _extract_locations(issue.evidence):
                max_page = max(max_page, p_idx)
        for _ in range(max_page + 1):
            writer.add_blank_page(width=612, height=792)

    total_pages = len(writer.pages)
    if total_pages == 0:
        writer.add_blank_page(width=612, height=792)
        total_pages = 1

    # Annotate issues onto pages
    for issue in issues:
        locations = _extract_locations(issue.evidence)
        for page_idx, x0, y0, x1, y1, pw, ph in locations:
            if page_idx < 0 or page_idx >= total_pages:
                target_page_idx = min(max(0, page_idx), total_pages - 1)
            else:
                target_page_idx = page_idx

            page = writer.pages[target_page_idx]
            actual_w = float(page.mediabox.width)
            actual_h = float(page.mediabox.height)

            # Scale coordinate system
            w_scale = actual_w / pw if pw > 0 else 1.0
            h_scale = actual_h / ph if ph > 0 else 1.0

            sx0 = x0 * w_scale
            sy0 = y0 * h_scale
            sx1 = x1 * w_scale
            sy1 = y1 * h_scale

            # PDF origin is bottom-left, y increases upward
            pdf_x0 = max(0.0, min(sx0, sx1))
            pdf_x1 = min(actual_w, max(sx0, sx1))
            pdf_y0 = max(0.0, actual_h - max(sy0, sy1))
            pdf_y1 = min(actual_h, actual_h - min(sy0, sy1))

            if pdf_x1 <= pdf_x0 + 1.0:
                pdf_x1 = min(actual_w, pdf_x0 + 20.0)
            if pdf_y1 <= pdf_y0 + 1.0:
                pdf_y1 = min(actual_h, pdf_y0 + 20.0)

            # Label for popup note
            note_line = f"\nReviewer note: {issue.reviewer_note}" if issue.reviewer_note else ""
            label = f"[{issue.type}] {issue.severity.value}: {issue.message}{note_line}"

            # Highlight bounding box
            rect_annot = Rectangle(
                rect=(pdf_x0, pdf_y0, pdf_x1, pdf_y1),
            )
            writer.add_annotation(page_number=target_page_idx, annotation=rect_annot)

            # Text popup note positioned at top corner of bounding box
            text_annot = Text(
                text=label,
                rect=(pdf_x0, pdf_y1, min(actual_w, pdf_x0 + 24.0), min(actual_h, pdf_y1 + 24.0)),
            )
            writer.add_annotation(page_number=target_page_idx, annotation=text_annot)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
