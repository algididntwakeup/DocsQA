"""Deterministic python-docx styling primitives for review reports."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor
from docx.table import _Cell, _Row


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
    return cell


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
