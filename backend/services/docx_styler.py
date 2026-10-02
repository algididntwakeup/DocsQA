"""Deterministic python-docx styling primitives for review reports."""

from __future__ import annotations

import base64
import binascii
import re
from io import BytesIO
from pathlib import Path
from typing import cast

from docx.document import Document as DocxDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Emu, Inches, Length, Pt, RGBColor
from docx.table import _Cell, _Row
from docx.text.paragraph import Paragraph

from schemas.report import HeaderTemplateConfig


def set_cell_shading(cell: _Cell, color_hex: str) -> None:
    """Apply a solid fill to a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex.lstrip("#")}"/>'))


def set_cell_margins(
    cell: _Cell, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150
) -> None:
    """Set cell padding in twentieths of a point (dxa)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(
        parse_xml(
            f"<w:tcMar {nsdecls('w')}>"
            f'<w:top w:w="{top}" w:type="dxa"/>'
            f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
            f'<w:left w:w="{left}" w:type="dxa"/>'
            f'<w:right w:w="{right}" w:type="dxa"/>'
            f"</w:tcMar>"
        )
    )


def _set_left_border(cell: _Cell, color_hex: str, size: int = 24) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(
        parse_xml(
            f"<w:tcBorders {nsdecls('w')}>"
            f'<w:left w:val="single" w:sz="{size}" w:space="0" '
            f'w:color="{color_hex.lstrip("#")}"/>'
            f"</w:tcBorders>"
        )
    )


def create_callout_box(
    doc: DocxDocument,
    title: str,
    text_paragraphs: list[str],
    border_color: str = "#DC2626",
    bg_color: str = "#FEF2F2",
) -> _Cell:
    """Create a one-cell, full-width callout with a three-point left accent."""
    table = doc.add_table(rows=1, cols=1)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.9)
    set_cell_shading(cell, bg_color)
    set_cell_margins(cell)
    _set_left_border(cell, border_color, size=36)
    row_pr = table.rows[0]._tr.get_or_add_trPr()
    row_pr.append(parse_xml(f"<w:cantSplit {nsdecls('w')}/>"))

    first = cell.paragraphs[0]
    first.paragraph_format.space_after = Pt(3)
    run = first.add_run(title)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(31, 41, 55)
    for text in text_paragraphs:
        paragraph = cell.add_paragraph(text)
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.line_spacing = 1.15
        for run in paragraph.runs:
            run.font.name = "Arial"
            run.font.size = Pt(10)
    return cast(_Cell, cell)


def format_table_header(
    row: _Row,
    col_widths: list[float],
    bg_color: str = "#0F172A",
    text_color: str = "#FFFFFF",
) -> None:
    """Format a repeating table header row with uppercase white text."""
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(parse_xml(f"<w:tblHeader {nsdecls('w')}/>"))
    tr_pr.append(parse_xml(f"<w:cantSplit {nsdecls('w')}/>"))
    color = RGBColor.from_string(text_color.lstrip("#"))
    for index, cell in enumerate(row.cells):
        if index < len(col_widths):
            cell.width = Inches(col_widths[index])
        set_cell_shading(cell, bg_color)
        set_cell_margins(cell)
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.space_after = Pt(0)
            for run in paragraph.runs:
                run.bold = True
                run.font.name = "Arial"
                run.font.size = Pt(9)
                run.font.color.rgb = color
                run.text = run.text.upper()


def apply_document_defaults(doc: DocxDocument) -> None:
    """Apply the report's stable page, font, and paragraph defaults."""
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(4)


def _logo_stream(source: str | None) -> BytesIO | None:
    """Resolve a data URI or existing local image path without accepting remote URLs."""
    if not source:
        return None
    if source.startswith("data:image/"):
        try:
            encoded = source.split(",", 1)[1]
            return BytesIO(base64.b64decode(encoded, validate=True))
        except (IndexError, ValueError, binascii.Error):
            return None
    if re.match(r"^https?://", source, flags=re.IGNORECASE):
        return None
    path = Path(source)
    try:
        if path.is_file() and path.suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".tif",
            ".tiff",
        }:
            return BytesIO(path.read_bytes())
    except (OSError, ValueError):
        return None
    return None


def _add_header_logo(paragraph: Paragraph, source: str | None, max_width: Length) -> None:
    """Add a proportionally scaled logo to a header paragraph when it is valid."""
    stream = _logo_stream(source)
    if stream is None:
        return
    try:
        run = paragraph.add_run()
        picture = run.add_picture(stream, height=Inches(0.6))
        if picture.width > max_width:
            ratio = max_width / picture.width
            picture.width = max_width
            picture.height = Emu(int(picture.height * ratio))
    except Exception:
        return
    paragraph.add_run("  ")


def apply_document_header(doc: DocxDocument, config: HeaderTemplateConfig) -> None:
    """Render a repeating, three-column dual-brand header into every section."""
    if not config.enabled:
        return
    for section in doc.sections:
        if (section.top_margin or Inches(1.0)) < Inches(1.1):
            section.top_margin = Inches(1.1)
        section.header_distance = Inches(0.25)
        header = section.header
        header.is_linked_to_previous = False
        # Keep the required header paragraph, then place the layout table after it.
        required = header.paragraphs[0]
        required.text = ""
        required.paragraph_format.space_after = Pt(0)
        page_width = section.page_width or Inches(8.5)
        left_margin = section.left_margin or Inches(0.8)
        right_margin = section.right_margin or Inches(0.8)
        table_width = page_width - left_margin - right_margin
        table = header.add_table(rows=1, cols=3, width=Emu(int(table_width)))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        widths = [
            Emu(int(table_width * ratio))
            for ratio in (0.25, 0.50, 0.25)
        ]
        for index, cell in enumerate(table.rows[0].cells):
            cell.width = widths[index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=0, bottom=0, left=50, right=50)
        tbl_pr = table._tbl.tblPr
        tbl_pr.append(
            parse_xml(
                f'<w:tblBorders {nsdecls("w")}>'
                '<w:top w:val="nil"/><w:left w:val="nil"/>'
                '<w:bottom w:val="nil"/><w:right w:val="nil"/>'
                '<w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
                "</w:tblBorders>"
            )
        )

        company_logo = config.company_logo or str(
            Path(__file__).resolve().parent.parent / "assets" / "reksolindo-logo.png"
        )
        left_logo: str | None = company_logo
        right_logo: str | None = config.client_logo
        if config.placement == "split_inverted":
            left_logo, right_logo = right_logo, left_logo
        elif config.placement == "both_right":
            left_logo, right_logo = None, None
        elif config.placement == "both_left":
            right_logo = None
        max_logo_width = (
            Inches(0.72)
            if config.placement in {"both_left", "both_right"}
            else Inches(1.25)
        )

        left_p, center_p, right_p = [cell.paragraphs[0] for cell in table.rows[0].cells]
        left_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        center_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for paragraph in (left_p, center_p, right_p):
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)

        if config.placement == "both_left":
            _add_header_logo(left_p, company_logo, max_logo_width)
            _add_header_logo(left_p, config.client_logo, max_logo_width)
        elif config.placement == "both_right":
            _add_header_logo(right_p, company_logo, max_logo_width)
            _add_header_logo(right_p, config.client_logo, max_logo_width)
        else:
            _add_header_logo(left_p, left_logo, max_logo_width)
            _add_header_logo(right_p, right_logo, max_logo_width)

        title_run = center_p.add_run(config.title)
        title_run.bold = True
        title_run.font.name = "Plus Jakarta Sans"
        title_run.font.size = Pt(10)
        title_run.font.color.rgb = RGBColor(31, 41, 55)
        title_run._element.rPr.rFonts.set(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
            "Plus Jakarta Sans",
        )
        if config.show_divider:
            for paragraph in (left_p, center_p, right_p):
                paragraph._p.get_or_add_pPr().append(
                    parse_xml(
                        f'<w:pBdr {nsdecls("w")}>'
                        '<w:bottom w:val="single" w:sz="4" w:space="4" w:color="CBD5E1"/>'
                        "</w:pBdr>"
                    )
                )
