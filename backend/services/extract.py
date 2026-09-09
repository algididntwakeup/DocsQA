"""
Text & Layout Extraction Service
=================================
Extracts raw text, layout metadata, table structures (bounding boxes, cell grid),
page anchors, and font metadata from PDF (PyMuPDF) and DOCX (python-docx).

Pipeline stage 0 — shared by both Linguistic and Traceability branches.
"""

import logging
import re
import subprocess
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from schemas.extraction import (
    CoordinateContract,
    ExtractionArtifact,
    Heading,
    PageMetadata,
    Table,
    TableCell,
    TextSpan,
)

logger = logging.getLogger(__name__)

# Safety thresholds for pathological PDFs (CAD drawings, blueprints, etc.)
_MAX_TABLES_PER_PAGE = 20
_MAX_CELLS_PER_TABLE = 500
_MAX_ROWS_PER_TABLE = 100
_MAX_COLS_PER_TABLE = 30
_PAGE_TIMEOUT_SECONDS = 20.0
_MAX_TEXT_BLOCKS_FOR_TABLES = 300
# Vector drawings (lines, rects, curves): CAD drawings and P&ID schematics have
# hundreds/thousands of vector paths. PyMuPDF's find_tables() inspects every path
# to find line intersections, which hangs or takes minutes per page.
_MAX_DRAWINGS_FOR_TABLES = 500
_PRINTED_PAGE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])([ivxlcdm]{1,12}|\d{1,4})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_EXPLICIT_PAGE_PATTERN = re.compile(
    r"\b(?:page|pg\.?|p\.?)\s*[:.]?\s*([ivxlcdm]{1,12}|\d{1,4})\b",
    re.IGNORECASE,
)


def _printed_page_label(blocks: list[dict], page_height: float) -> str | None:
    """Read the printed page label from footer text, not the PDF position."""
    candidates: list[tuple[float, str]] = []
    for block in blocks:
        for line in block.get("lines", []):
            line_text = " ".join(
                str(span.get("text", "")).strip() for span in line.get("spans", [])
            ).strip()
            bbox = line.get("bbox")
            if not line_text or not bbox or float(bbox[1]) < page_height * 0.78:
                continue
            explicit = _EXPLICIT_PAGE_PATTERN.search(line_text)
            if explicit:
                candidates.append((float(bbox[1]), explicit.group(1)))
                continue
            if re.fullmatch(r"[ivxlcdm]{1,12}|\d{1,4}", line_text, re.IGNORECASE):
                candidates.append((float(bbox[1]), line_text))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


class PDFExtractor:
    """Extracts text, headings, and tables from PDF files with canonical coordinates."""

    def extract(self, file_path: Path, document_id: UUID) -> ExtractionArtifact:
        artifact = ExtractionArtifact(document_id=document_id)

        try:
            import fitz  # type: ignore[import-untyped]
        except Exception as exc:  # noqa: BLE001 — fitz import failures are surface warnings
            artifact.warnings.append(f"Failed to import PyMuPDF: {exc}")
            return artifact

        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:  # noqa: BLE001 — malformed PDFs degrade to warnings
            artifact.warnings.append(f"Failed to open PDF: {exc}")
            return artifact

        for page_index in range(len(doc)):
            page_start = time.monotonic()
            page = doc[page_index]
            rect = page.rect
            # Extract text blocks
            blocks = page.get_text("dict")["blocks"]
            artifact.pages.append(
                PageMetadata(
                    page_index=page_index,
                    width=rect.width,
                    height=rect.height,
                    page_label=_printed_page_label(blocks, rect.height),
                )
            )
            for block in blocks:
                if block.get("type") != 0:  # not a text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        bbox = CoordinateContract(
                            page_index=page_index,
                            x0=span["bbox"][0],
                            y0=span["bbox"][1],
                            x1=span["bbox"][2],
                            y1=span["bbox"][3],
                            page_width=rect.width,
                            page_height=rect.height,
                        )

                        font_name = span.get("font", "")
                        font_size = span.get("size", 10)
                        is_bold = "Bold" in font_name or "Black" in font_name

                        if is_bold and font_size > 12:
                            artifact.headings.append(
                                Heading(
                                    text=text,
                                    level=1 if font_size > 16 else 2,
                                    bbox=bbox,
                                )
                            )
                        else:
                            artifact.spans.append(TextSpan(text=text, bbox=bbox))

            # Guard: skip table extraction entirely if page text phase already took too long
            if time.monotonic() - page_start > _PAGE_TIMEOUT_SECONDS:
                artifact.warnings.append(
                    f"Page {page_index}: text extraction exceeded"
                    f" {_PAGE_TIMEOUT_SECONDS}s timeout;"
                    " table extraction skipped for this page."
                )
                continue

            # Guard: skip table detection on CAD/drawing pages. find_tables() is a
            # super-linear, uninterruptible C call that hangs on dense vector pages
            # (measured 25s at ~300 blocks, indefinite at ~900). Data tables live on
            # sparse pages; a high block count is a reliable drawing heuristic.
            num_text_blocks = len(blocks)
            if num_text_blocks > _MAX_TEXT_BLOCKS_FOR_TABLES:
                artifact.warnings.append(
                    f"Page {page_index}: skipped table detection on dense page"
                    f" ({num_text_blocks} text blocks)."
                )
                continue

            # Guard: skip table detection on vector-dense drawing pages (CAD schematics, blueprints)
            try:
                drawings = page.get_drawings()
                num_drawings = len(drawings)
            except Exception:  # noqa: BLE001
                num_drawings = 0

            if num_drawings > _MAX_DRAWINGS_FOR_TABLES:
                artifact.warnings.append(
                    f"Page {page_index}: skipped table detection on vector-dense page"
                    f" ({num_drawings} vector paths)."
                )
                continue

            # Extract tables using PyMuPDF's find_tables.
            # IMPORTANT: page.find_tables() returns a TableFinder object.
            # - finder.tables  → list[Table]  (the table objects to iterate)
            # - Table.cells    → flat list[tuple(x0,y0,x1,y1)] (NOT a 2D grid!)
            # - Table.rows     → list[TableRow] — the correct 2D row iterator
            # - TableRow.cells → list[tuple|None] per column slot
            # Using Table.cells as if it were rows×cols causes TypeError because
            # each element is already a (x0,y0,x1,y1) tuple, not a row of cells.
            try:
                finder = page.find_tables()
            except Exception as exc:  # noqa: BLE001
                artifact.warnings.append(f"Page {page_index}: find_tables() raised {exc}")
                continue

            if finder is None:
                artifact.warnings.append(f"Page {page_index}: find_tables() returned None.")
                continue

            all_tables = getattr(finder, "tables", None) or []
            num_found = len(all_tables)
            tables_on_page = all_tables[:_MAX_TABLES_PER_PAGE]
            if num_found > _MAX_TABLES_PER_PAGE:
                artifact.warnings.append(
                    f"Page {page_index}: capped at {_MAX_TABLES_PER_PAGE} tables"
                    f" (found {num_found})."
                )

            for table in tables_on_page:
                if table is None:
                    continue
                # Guard: check page-level timeout before each table
                if time.monotonic() - page_start > _PAGE_TIMEOUT_SECONDS:
                    artifact.warnings.append(
                        f"Page {page_index}: per-page timeout reached during table"
                        " extraction; remaining tables skipped."
                    )
                    break

                table_model = Table(cells=[])
                t_bbox = table.bbox
                table_model.bbox = CoordinateContract(
                    page_index=page_index,
                    x0=t_bbox[0],
                    y0=t_bbox[1],
                    x1=t_bbox[2],
                    y1=t_bbox[3],
                    page_width=rect.width,
                    page_height=rect.height,
                )

                # Use table.rows for 2D iteration (TableRow.cells is list[tuple|None]).
                try:
                    rows = table.rows
                except Exception as exc:  # noqa: BLE001
                    artifact.warnings.append(
                        f"Page {page_index}: table.rows raised {exc}; skipping table."
                    )
                    continue

                num_rows = len(rows)
                num_cols = max((len(r.cells) for r in rows), default=0)
                total_cells = num_rows * num_cols

                # Guard: skip pathological tables (CAD cross-hatching, etc.)
                if (
                    total_cells > _MAX_CELLS_PER_TABLE
                    or num_rows > _MAX_ROWS_PER_TABLE
                    or num_cols > _MAX_COLS_PER_TABLE
                ):
                    artifact.warnings.append(
                        f"Page {page_index}: skipped pathological table with"
                        f" {num_rows} rows x {num_cols} cols ({total_cells} cells)."
                    )
                    continue

                for row_idx, table_row in enumerate(rows):
                    for col_idx, cell_rect in enumerate(table_row.cells):
                        # cell_rect is None for merged/spanned cells
                        if cell_rect is None:
                            continue

                        # Defensively unpack to validate it is a 4-float bbox
                        try:
                            x0 = float(cell_rect[0])
                            y0 = float(cell_rect[1])
                            x1 = float(cell_rect[2])
                            y1 = float(cell_rect[3])
                        except (TypeError, IndexError, ValueError):
                            continue

                        # Skip degenerate / inverted bounding boxes
                        if x1 <= x0 or y1 <= y0:
                            continue

                        try:
                            cell_text = page.get_text("text", clip=cell_rect).strip()
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "Error extracting table cell %s,%s: %s",
                                row_idx,
                                col_idx,
                                exc,
                            )
                            continue

                        if cell_text:
                            cell_bbox = CoordinateContract(
                                page_index=page_index,
                                x0=x0,
                                y0=y0,
                                x1=x1,
                                y1=y1,
                                page_width=rect.width,
                                page_height=rect.height,
                            )

                            table_model.cells.append(
                                TableCell(
                                    text=cell_text,
                                    row_index=row_idx,
                                    col_index=col_idx,
                                    bbox=cell_bbox,
                                )
                            )

                if table_model.cells:
                    artifact.tables.append(table_model)

        doc.close()
        return artifact


class DOCXExtractor:
    """
    Extracts structure from DOCX. Generates a canonical PDF via LibreOffice (soffice)
    to obtain reliable bounding boxes.
    """

    def extract(self, file_path: Path, document_id: UUID) -> ExtractionArtifact:
        # First, attempt to convert to PDF for canonical coordinates
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    str(file_path),
                    "--outdir",
                    temp_dir,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                converted_pdf = Path(temp_dir) / file_path.with_suffix(".pdf").name
                if converted_pdf.exists():
                    artifact = PDFExtractor().extract(converted_pdf, document_id)
                    artifact.warnings.append(
                        "Converted from DOCX using headless LibreOffice for coordinate mapping."
                    )
                    return artifact
            logger.warning("soffice conversion failed: %s", result.stderr)

        # Fallback if LibreOffice is missing or fails
        artifact = ExtractionArtifact(document_id=document_id)
        artifact.warnings.append(
            "DOCX processing without Canonical PDF coordinates. "
            "soffice conversion failed or not found."
        )

        try:
            import docx
        except Exception as exc:  # noqa: BLE001
            artifact.warnings.append(f"Failed to import python-docx: {exc}")
            return artifact

        try:
            document = docx.Document(str(file_path))
        except Exception as exc:  # noqa: BLE001
            artifact.warnings.append(f"Failed to open DOCX: {exc}")
            return artifact

        dummy_bbox = CoordinateContract(
            page_index=0, x0=0, y0=0, x1=0, y1=0, page_width=0, page_height=0
        )

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            style = paragraph.style
            style_name = style.name if style is not None else ""
            if style_name.startswith("Heading"):
                level = 1
                with suppress(ValueError):
                    level = int(style_name.split(" ")[-1])
                artifact.headings.append(Heading(text=text, level=level, bbox=dummy_bbox))
            else:
                artifact.spans.append(TextSpan(text=text, bbox=dummy_bbox))

        return artifact


def extract_document(file_path: Path, document_id: UUID, mime_type: str) -> ExtractionArtifact:
    """Factory function to choose the correct extractor based on mime type."""
    if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        return PDFExtractor().extract(file_path, document_id)
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or file_path.suffix.lower() == ".docx"
    ):
        return DOCXExtractor().extract(file_path, document_id)
    artifact = ExtractionArtifact(document_id=document_id)
    artifact.warnings.append(f"Unsupported file type: {mime_type}")
    return artifact
