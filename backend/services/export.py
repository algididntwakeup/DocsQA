"""Export Service for Annotated PDF.

Generates:
Annotated PDF with visual bounding boxes and callout notes for included findings.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import docx
import pypdf
from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor
from docx.table import Table, _Cell, _Row
from pypdf.annotations import Rectangle, Text

from schemas.budinski import (
    AssessmentData,
    AssessmentMetadata,
    BaselineMeasures,
    BlockerFinding,
    BudinskiScorecard,
    LanguageFinding,
    MajorFinding,
    ScoreItem,
)
from domain.enums import ReportLanguage
from services.docx_styler import apply_document_defaults
from services.report_locale import get_report_strings
from services.report_synthesizer import ReportSynthesizer

if TYPE_CHECKING:
    from models.document import Document
    from models.issue import Issue
    from services.storage.local import LocalStorage


def _issue_category(issue: Any) -> str:
    return str(
        getattr(getattr(issue, "category", ""), "value", getattr(issue, "category", ""))
    ).upper()


def _issue_severity(issue: Any) -> str:
    return str(
        getattr(getattr(issue, "severity", ""), "value", getattr(issue, "severity", ""))
    ).upper()


def _load_scorecard(scorecard_data: dict[str, Any] | None) -> BudinskiScorecard:
    """Validate persisted scorecards while ignoring Pydantic computed fields."""
    if not scorecard_data:
        return BudinskiScorecard()
    computed_fields = {"average", "score", "summary_ratio", "baseline_score", "group_averages"}
    cleaned = {
        key: (
            {
                child_key: child_value
                for child_key, child_value in value.items()
                if child_key not in computed_fields
            }
            if isinstance(value, dict)
            else value
        )
        for key, value in scorecard_data.items()
        if key not in computed_fields
    }
    return BudinskiScorecard.model_validate(cleaned)
def assessment_from_document_findings(
    document: Any,
    issues: list[Any],
    scorecard_data: dict[str, Any] | None = None,
    include_minors: bool = False,
    language: ReportLanguage = ReportLanguage.ENGLISH,
) -> AssessmentData:
    """Adapt persisted pipeline artifacts into the executive report contract."""
    included = [
        issue
        for issue in issues
        if getattr(issue, "included_in_report", True)
        and str(getattr(issue, "type", "")).upper() != "STANDARD_NOT_IN_BIBLIOGRAPHY"
        and (include_minors or _issue_severity(issue) not in {"MINOR", "INFO", "LOW"})
    ]
    scorecard = _load_scorecard(scorecard_data)
    baseline = scorecard.baseline_measures or BaselineMeasures(
        purpose_distinct_from_objective=False,
        procedure_repeatable=True,
        conclusions_valid=False,
        recommendations_actionable=False,
        reasons={
            "purpose_distinct_from_objective": "No persisted baseline assessment was available.",
            "procedure_repeatable": (
                "Procedure evidence was not reconstructed in the export adapter."
            ),
            "conclusions_valid": "No persisted baseline assessment was available.",
            "recommendations_actionable": "No persisted baseline assessment was available.",
        },
    )
    synthesizer = ReportSynthesizer(language)
    blockers = []
    majors = []
    language = []
    blocker_levels = {"BLOCKER", "CRITICAL", "HIGH"}
    control_blocker_types = {
        "UNCONTROLLED_PAGE",
        "RUNNING_FOOTER",
        "MISSING_DOCUMENT_NUMBER",
        "DOCUMENT_NUMBER_MISSING",
    }
    blocker_candidates = [
        issue
        for issue in included
        if _issue_severity(issue) in blocker_levels
        or str(getattr(issue, "type", "")).upper() in control_blocker_types
    ]
    blocker_groups = synthesizer.synthesize_blocker_groups(blocker_candidates)
    for group in blocker_groups:
        blockers.append(
            BlockerFinding(
                number=len(blockers) + 1,
                title=f"{group.get('finding_codes', group['type'])} ({group['count']} instances)",
                where_location="Consolidated across the affected printed pages",
                what_it_says=group["message"],
                what_body_has=group["message"],
                why_it_matters=(
                    "The repeated findings indicate one unresolved control weakness across "
                    "the document."
                ),
                what_would_fix_it=group["suggestion"],
            )
        )
    major_candidates: list[Any] = []
    for issue in included:
        evidence = getattr(issue, "evidence", None) or {}
        message = str(getattr(issue, "message", ""))
        page = str(getattr(issue, "page_number", None) or evidence.get("page", "not located"))
        issue_type = str(getattr(issue, "type", "")).upper()
        if _issue_severity(issue) in blocker_levels or issue_type in control_blocker_types:
            continue
        elif _issue_category(issue) in {"LINGUISTIC", "SPELLING", "GRAMMAR", "DICTIONARY"}:
            language.append(
                LanguageFinding(
                    page=page,
                    as_written=str(evidence.get("original_text") or message),
                    suggested=str(evidence.get("suggestion") or "Review wording."),
                )
            )
        else:
            major_candidates.append(issue)

    for group in synthesizer.synthesize_blocker_groups(major_candidates):
        majors.append(
            MajorFinding(
                number=len(majors) + 1,
                finding=group["message"],
                what_would_fix_it=group["suggestion"],
            )
        )

    metadata = AssessmentMetadata(
        document_reviewed=(
            f"{getattr(document, 'original_filename', 'document')} | {getattr(document, 'id', '')}"
        ),
        type_of_review="Deterministic engineering document review",
        basis=(
            "Budinski Appendix 12, internal consistency, layout, traceability, and language "
            "findings."
        ),
        scoring="Budinski Appendix 12 scores 1-5; scores of 2 or below require rework.",
        note="Generated from persisted document findings and scorecard artifacts.",
        not_covered=(
            "Engineering adequacy, operational safety, and external standards certification."
        ),
    )
    return AssessmentData(
        title=f"Review of {getattr(document, 'original_filename', 'Document')}",
        subtitle="Executive engineering-document review report",
        header_title="DOCUMENT REVIEW ENGINEERING",
        running_header=str(getattr(document, "original_filename", "Document")),
        metadata=metadata,
        summary_judgement=[],
        bottom_line="",
        baseline_measures=baseline,
        blockers=blockers,
        major_findings=majors,
        language_findings=language,
        scorecard=scorecard,
        what_it_does_well=[],
        limits_of_review=[metadata.not_covered],
        review_score_string=scorecard.review_score_string
        or "REVIEWSCORE | generated deterministically from persisted findings",
    )


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
        "bounding_box",
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
            sev_val = getattr(issue.severity, "value", str(issue.severity))
            label = f"[{issue.type}] {sev_val}: {issue.message}{note_line}"

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


# ---------------------------------------------------------------------------
# DOCX Export: Budinski Review of Asset Life Extension Study (Review-ALE)
# ---------------------------------------------------------------------------

COLOR_NAVY = RGBColor(27, 54, 93)  # #1B365D Primary Engineering Navy
COLOR_SECONDARY = RGBColor(43, 76, 126)  # #2B4C7E Secondary Slate Blue
COLOR_TEXT = RGBColor(30, 41, 59)  # #1E293B Charcoal Body Text
COLOR_MUTED = RGBColor(100, 116, 139)  # #64748B Muted Slate
COLOR_PASS = RGBColor(21, 128, 61)  # #15803D Forest Green
COLOR_FAIL = RGBColor(185, 28, 28)  # #B91C1C Crimson Red

HEX_NAVY = "1B365D"
HEX_WHITE = "FFFFFF"
HEX_BANNER = "EBF3FA"
HEX_ZEBRA = "F8FAFC"
HEX_BORDER = "D0D7DE"
HEX_CALLOUT_BG = "F8FAFC"
HEX_BLOCKER_BG = "FEF2F2"
HEX_BLOCKER_BORDER = "B91C1C"
HEX_DEMO_REWRITE_BG = "F0FDF4"
HEX_DEMO_REWRITE_BORDER = "15803D"


def _set_cell_shading(cell: _Cell, color_hex: str) -> None:
    """Set background fill color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'))


def _set_cell_margins(
    cell: _Cell,
    top: int = 100,
    bottom: int = 100,
    left: int = 140,
    right: int = 140,
) -> None:
    """Set internal cell margins (padding) in dxa (1 pt = 20 dxa)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f"<w:tcMar {nsdecls('w')}>"
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f"</w:tcMar>"
    )
    tc_pr.append(tc_mar)


def _set_cell_borders(
    cell: _Cell,
    *,
    top: str = "none",
    bottom: str = "none",
    left: str = "none",
    right: str = "none",
    color: str = HEX_BORDER,
    sz: str = "4",
) -> None:
    """Set borders on an individual table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    borders_elm = parse_xml(
        f"<w:tcBorders {nsdecls('w')}>"
        f'<w:top w:val="{top}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{left}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{bottom}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{right}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f"</w:tcBorders>"
    )
    tc_pr.append(borders_elm)


def _set_table_borders(table: Table, color: str = HEX_BORDER, sz: str = "4") -> None:
    """Set clean subtle horizontal-rule borders on a table."""
    tbl_pr = table._tbl.tblPr
    borders = parse_xml(
        f"<w:tblBorders {nsdecls('w')}>"
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/></w:tblBorders>'
    )
    tbl_pr.append(borders)


def _apply_tbl_header(row: _Row) -> None:
    """Designate table row as repeating header across pages."""
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(parse_xml(f"<w:tblHeader {nsdecls('w')}/>"))


def _apply_cant_split(row: _Row) -> None:
    """Prevent table row from splitting across page breaks."""
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(parse_xml(f"<w:cantSplit {nsdecls('w')}/>"))


def _add_callout_box(
    doc: DocxDocument,
    bg_hex: str = HEX_CALLOUT_BG,
    border_color_hex: str = HEX_NAVY,
    border_sz: str = "36",
    width_inches: float = 6.9,
) -> _Cell:
    """Create a full-width callout box with thick left accent border and shaded background."""
    table = doc.add_table(rows=1, cols=1)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    cell.width = Inches(width_inches)
    _set_cell_shading(cell, bg_hex)
    _set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
    _set_cell_borders(cell, left="single", color=border_color_hex, sz=border_sz)
    _apply_cant_split(table.rows[0])
    return cast(_Cell, cell)


def _add_heading_1(doc: DocxDocument, text: str) -> None:
    """Add Level 1 Heading styled with navy primary color and keep-with-next."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(13)
    run.font.color.rgb = COLOR_NAVY


def _add_heading_2(doc: DocxDocument, text: str, color: RGBColor = COLOR_SECONDARY) -> None:
    """Add Level 2 Heading styled with secondary color and keep-with-next."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(11)
    run.font.color.rgb = color


def _add_body_p(doc: DocxDocument, text: str, space_after: int = 6) -> None:
    """Add body paragraph with standard line spacing and spacing after."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(10)
    run.font.color.rgb = COLOR_TEXT


def _format_table_row(
    row: _Row,
    widths: list[float],
    bg_hex: str | None = None,
    is_header: bool = False,
) -> None:
    """Format row cells with explicit widths, padding, cantSplit, and optional shading."""
    _apply_cant_split(row)
    if is_header:
        _apply_tbl_header(row)

    for idx, cell in enumerate(row.cells):
        if idx < len(widths):
            cell.width = Inches(widths[idx])
        _set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
        if bg_hex:
            _set_cell_shading(cell, bg_hex)
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            for r in p.runs:
                r.font.name = "Arial"
                if is_header:
                    r.bold = True
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = RGBColor(255, 255, 255)
                else:
                    r.font.size = Pt(9)


def _setup_page_header_footer(doc: DocxDocument, assessment: AssessmentData) -> None:
    """Setup running header and footer with dynamic page numbers and document identity."""
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    # Page Header
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.space_after = Pt(4)
    r_hdr = hp.add_run(f"{assessment.running_header}  |  {assessment.header_title}")
    r_hdr.font.name = "Arial"
    r_hdr.font.size = Pt(8)
    r_hdr.font.color.rgb = COLOR_MUTED

    # Page Footer
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fp.paragraph_format.space_before = Pt(4)

    r_ftr_title = fp.add_run(f"{assessment.title}    ")
    r_ftr_title.font.name = "Arial"
    r_ftr_title.font.size = Pt(8)
    r_ftr_title.font.color.rgb = COLOR_MUTED

    r_pg = fp.add_run("Page ")
    r_pg.font.name = "Arial"
    r_pg.font.size = Pt(8)
    r_pg.font.color.rgb = COLOR_MUTED
    r_pg._r.append(parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="PAGE"/>'))

    r_of = fp.add_run(" of ")
    r_of.font.name = "Arial"
    r_of.font.size = Pt(8)
    r_of.font.color.rgb = COLOR_MUTED
    r_of._r.append(parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="NUMPAGES"/>'))


def generate_ale_review_docx(
    assessment_result: AssessmentData,
    document: Any = None,
    language: ReportLanguage = ReportLanguage.ENGLISH,
) -> bytes:
    """
    Generate a complete, professionally formatted DOCX review report from the supplied
    assessment and Budinski scorecard data.

    Covers 10 distinct sections:
    1. Document Reviewed Metadata Block
    2. Summary Judgement & Callout Box 'BOTTOM LINE'
    3. Table: 'The four baseline measures'
    4. Sub-section: 'Blockers' (callouts per blocker)
    5. Table: 'Should fix in the next revision'
    6. Table: 'Language and mechanics, by page'
    7. 'Demonstration rewrite' (As Written vs Demonstration comparison)
     8. 'Scorecard' (Appendix 12 items across Groups I-IV with averages and notes)
    9. 'What this document does well'
    10. 'Limits of this review' & REVIEWSCORE summary string
    """
    doc = docx.Document()
    apply_document_defaults(doc)
    strings = get_report_strings(language)
    synthesizer = ReportSynthesizer(language)
    if not assessment_result.summary_judgement:
        summary = synthesizer.generate_summary_judgement(assessment_result.major_findings, assessment_result.scorecard, assessment_result.metadata)
        assessment_result.summary_judgement = summary.split("\n\n")
    if not assessment_result.bottom_line:
        assessment_result.bottom_line = synthesizer.generate_bottom_line(assessment_result.blockers)
    if not assessment_result.what_it_does_well:
        assessment_result.what_it_does_well = synthesizer.synthesize_praise({}, [])
    _setup_page_header_footer(doc, assessment_result)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = COLOR_TEXT

    # -----------------------------------------------------------------------
    # Document Title & Subtitle
    # -----------------------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run(f"{strings.title_prefix}{assessment_result.title}")
    r_title.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = COLOR_NAVY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run(assessment_result.subtitle)
    r_sub.italic = True
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = COLOR_MUTED

    # -----------------------------------------------------------------------
    # Bagian 1: Document Reviewed Metadata Block
    # -----------------------------------------------------------------------
    meta = assessment_result.metadata
    workflow_status = getattr(getattr(document, "workflow_status", None), "value", strings.not_supplied)
    owner = getattr(document, "owner", None)
    verified = getattr(document, "verified_by", None)
    prepared_by = getattr(owner, "full_name", strings.not_supplied)
    checked_by = getattr(verified, "full_name", strings.pending_verification)
    is_english = language == ReportLanguage.ENGLISH
    meta_entries = [
        ("Doc No" if is_english else "Nomor Dokumen", meta.document_reviewed),
        ("Rev" if is_english else "Revisi", meta.document_reviewed.rsplit(" ", 1)[-1] if meta.document_reviewed else strings.not_supplied),
        ("Pages" if is_english else "Halaman", strings.not_supplied),
        ("File Date" if is_english else "Tanggal File", strings.not_supplied),
        ("Originator" if is_english else "Asal", strings.not_supplied),
        ("Document reviewed" if is_english else "Dokumen yang ditinjau", meta.document_reviewed),
        ("Type of review" if is_english else "Jenis tinjauan", meta.type_of_review),
        ("Basis" if is_english else "Dasar", meta.basis),
        ("Scoring" if is_english else "Penilaian", meta.scoring),
        ("Note" if is_english else "Catatan", meta.note),
        ("Not covered" if is_english else "Tidak tercakup", meta.not_covered),
        ("Prepared by" if is_english else "Disiapkan oleh", prepared_by),
        ("Checked / Verified by" if is_english else "Diperiksa / Diverifikasi oleh", checked_by if workflow_status == "VERIFIED_BY_LEAD" else strings.pending_verification),
        ("Status" if is_english else "Status", workflow_status),
    ]

    meta_table = doc.add_table(rows=0, cols=2)
    meta_table.autofit = False
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(meta_table, color=HEX_BORDER, sz="4")
    meta_widths = [1.5, 5.4]

    for label, val in meta_entries:
        row = meta_table.add_row()
        _format_table_row(row, meta_widths)
        _set_cell_shading(row.cells[0], "F4F6F8")
        _set_cell_shading(row.cells[1], HEX_WHITE)

        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(9)
        r0.font.color.rgb = COLOR_NAVY

        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.name = "Arial"
        r1.font.size = Pt(9)
        r1.font.color.rgb = COLOR_TEXT

    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(0)
    p_space.paragraph_format.space_after = Pt(6)

    # Bagian 2: Summary Judgement & Callout Box "BOTTOM LINE"
    _add_heading_1(doc, strings.summary_judgement)

    for paragraph_text in assessment_result.summary_judgement:
        _add_body_p(doc, paragraph_text, space_after=6)

    # Callout Box "BOTTOM LINE"
    bottom_line_cell = _add_callout_box(
        doc,
        bg_hex=HEX_CALLOUT_BG,
        border_color_hex=HEX_NAVY,
        border_sz="36",
    )
    bl_p = bottom_line_cell.paragraphs[0]
    bl_p.paragraph_format.space_before = Pt(0)
    bl_p.paragraph_format.space_after = Pt(0)
    bl_p.paragraph_format.line_spacing = 1.15
    bl_tag = bl_p.add_run(f"{strings.bottom_line}  ")
    bl_tag.bold = True
    bl_tag.font.name = "Arial"
    bl_tag.font.size = Pt(10)
    bl_tag.font.color.rgb = COLOR_NAVY

    bl_body = bl_p.add_run(assessment_result.bottom_line)
    bl_body.font.name = "Arial"
    bl_body.font.size = Pt(10)
    bl_body.font.color.rgb = COLOR_TEXT

    p_bl_space = doc.add_paragraph()
    p_bl_space.paragraph_format.space_before = Pt(0)
    p_bl_space.paragraph_format.space_after = Pt(8)

    # -----------------------------------------------------------------------
    # Bagian 3: Tabel "The four baseline measures"
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.baseline_measures)
    _add_body_p(doc, strings.baseline_intro, space_after=6)

    baseline = assessment_result.baseline_measures
    baseline_items = [
        (
            "States the purpose of the report explicitly, distinct from the objective of the work",
            baseline.purpose_distinct_from_objective,
            baseline.reasons.get("purpose_distinct_from_objective", ""),
        ),
        (
            "Procedure detailed enough for another competent party to repeat the work",
            baseline.procedure_repeatable,
            baseline.reasons.get("procedure_repeatable", ""),
        ),
        (
            "Conclusions are conclusions, not results and not discussion",
            baseline.conclusions_valid,
            baseline.reasons.get("conclusions_valid", ""),
        ),
        (
            "Recommendations name an owner and a date",
            baseline.recommendations_actionable,
            baseline.reasons.get("recommendations_actionable", ""),
        ),
    ]

    base_table = doc.add_table(rows=0, cols=3)
    base_table.autofit = False
    base_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(base_table, color=HEX_BORDER, sz="4")
    base_widths = [2.2, 0.9, 3.8]

    # Header row
    hdr_row = base_table.add_row()
    hdr_row.cells[0].paragraphs[0].add_run("Measure" if strings.baseline_measures.startswith("The") else "Ukuran")
    hdr_row.cells[1].paragraphs[0].add_run("Result" if strings.baseline_measures.startswith("The") else "Hasil")
    hdr_row.cells[2].paragraphs[0].add_run("Reason" if strings.baseline_measures.startswith("The") else "Alasan")
    _format_table_row(hdr_row, base_widths, bg_hex=HEX_NAVY, is_header=True)

    for idx, (measure_text, is_pass, reason_text) in enumerate(baseline_items):
        row = base_table.add_row()
        bg = HEX_ZEBRA if idx % 2 == 1 else HEX_WHITE

        p_m = row.cells[0].paragraphs[0]
        r_m = p_m.add_run(measure_text)
        r_m.font.name = "Arial"
        r_m.font.size = Pt(9)
        r_m.bold = True
        r_m.font.color.rgb = COLOR_TEXT

        p_r = row.cells[1].paragraphs[0]
        r_res = p_r.add_run("PASS" if is_pass else "FAIL")
        r_res.font.name = "Arial"
        r_res.font.size = Pt(9)
        r_res.bold = True
        r_res.font.color.rgb = COLOR_PASS if is_pass else COLOR_FAIL

        p_rs = row.cells[2].paragraphs[0]
        r_rs = p_rs.add_run(reason_text)
        r_rs.font.name = "Arial"
        r_rs.font.size = Pt(9)
        r_rs.font.color.rgb = COLOR_TEXT

        _format_table_row(row, base_widths, bg_hex=bg)

    p_score = doc.add_paragraph()
    p_score.paragraph_format.space_before = Pt(6)
    r_sc_lbl = p_score.add_run(f"{strings.baseline_score}: ")
    r_sc_lbl.bold = True
    r_sc_lbl.font.name = "Arial"
    r_sc_lbl.font.size = Pt(9.5)
    r_sc_lbl.font.color.rgb = COLOR_NAVY
    baseline_score = assessment_result.scorecard.baseline_score
    r_sc_val = p_score.add_run(f"{baseline_score:.0f}/4 ({baseline_score:.0f} {strings.passing})")
    r_sc_val.font.size = Pt(9.5)
    r_sc_val.bold = True
    r_sc_val.font.color.rgb = COLOR_PASS if baseline_score >= 3 else COLOR_FAIL

    # -----------------------------------------------------------------------
    # Bagian 4: Scorecard summary before blockers
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.scorecard)
    _add_body_p(doc, strings.scorecard_intro, space_after=6)
    scorecard = assessment_result.scorecard
    score_summary = (
        f"Overall average: {scorecard.overall_average:.2f} / 5.00. "
        f"Group averages: I {scorecard.group_averages['Group I']:.2f}, "
        f"II {scorecard.group_averages['Group II']:.2f}, "
        f"III {scorecard.group_averages['Group III']:.2f}, "
        f"IV {scorecard.group_averages['Group IV']:.2f}. "
        f"Items requiring rework: {len(scorecard.get_rework_items())}."
    )
    _add_callout_box(
        doc,
        bg_hex="EFF6FF",
        border_color_hex=HEX_NAVY,
        border_sz="24",
    ).paragraphs[0].add_run(score_summary)
    p_sc_space = doc.add_paragraph()
    p_sc_space.paragraph_format.space_after = Pt(8)

    # -----------------------------------------------------------------------
    # Bagian 5: Sub-section "Blockers"
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.blockers)
    _add_body_p(doc, strings.blockers_intro, space_after=6)

    if not assessment_result.blockers:
        _add_body_p(doc, strings.no_blockers, space_after=8)
    else:
        for blocker in assessment_result.blockers:
            _add_heading_2(doc, f"{strings.blocker} {blocker.number}: {blocker.title}", color=COLOR_FAIL)
            cell = _add_callout_box(doc, bg_hex=HEX_BLOCKER_BG, border_color_hex=HEX_BLOCKER_BORDER, border_sz="36")
            fields = [(strings.where, blocker.where_location), (strings.what_it_says, blocker.what_it_says), (strings.what_body_has, blocker.what_body_has), (strings.why_it_matters, blocker.why_it_matters), (strings.what_would_fix_it, blocker.what_would_fix_it)]
            for f_idx, (fname, fval) in enumerate(fields):
                p = cell.paragraphs[0] if f_idx == 0 else cell.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(3 if f_idx < len(fields) - 1 else 0)
                p.paragraph_format.line_spacing = 1.15
                r_fn = p.add_run(f"{fname}: ")
                r_fn.bold = True
                r_fn.font.name = "Arial"
                r_fn.font.size = Pt(9.5)
                r_fn.font.color.rgb = COLOR_FAIL if fname == strings.what_would_fix_it else COLOR_TEXT
                r_fv = p.add_run(fval)
                r_fv.font.name = "Arial"
                r_fv.font.size = Pt(9.5)
                r_fv.font.color.rgb = COLOR_TEXT
            p_b_space = doc.add_paragraph()
            p_b_space.paragraph_format.space_before = Pt(0)
            p_b_space.paragraph_format.space_after = Pt(6)

    # -----------------------------------------------------------------------
    # Bagian 6: Tabel "Should fix in the next revision"
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.next_revision)
    _add_body_p(doc, strings.next_revision_intro, space_after=6)

    if not assessment_result.major_findings:
        _add_body_p(doc, strings.no_major_findings, space_after=8)
    else:
        maj_table = doc.add_table(rows=0, cols=3)
        maj_table.autofit = False
        maj_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(maj_table, color=HEX_BORDER, sz="4")
        maj_widths = [0.5, 3.5, 2.9]
        m_hdr = maj_table.add_row()
        m_hdr.cells[0].paragraphs[0].add_run(strings.no)
        m_hdr.cells[1].paragraphs[0].add_run(strings.finding)
        m_hdr.cells[2].paragraphs[0].add_run(strings.what_would_fix_it)
        _format_table_row(m_hdr, maj_widths, bg_hex=HEX_NAVY, is_header=True)
        for idx, finding in enumerate(assessment_result.major_findings):
            row = maj_table.add_row()
            bg = HEX_ZEBRA if idx % 2 == 1 else HEX_WHITE
            p0 = row.cells[0].paragraphs[0]
            r0 = p0.add_run(str(finding.number))
            r0.bold = True
            r0.font.name = "Arial"
            r0.font.size = Pt(9)
            r0.font.color.rgb = COLOR_NAVY
            p1 = row.cells[1].paragraphs[0]
            r1 = p1.add_run(finding.finding)
            r1.font.name = "Arial"
            r1.font.size = Pt(9)
            r1.font.color.rgb = COLOR_TEXT
            p2 = row.cells[2].paragraphs[0]
            r2 = p2.add_run(finding.what_would_fix_it)
            r2.font.name = "Arial"
            r2.font.size = Pt(9)
            r2.font.color.rgb = COLOR_TEXT
            _format_table_row(row, maj_widths, bg_hex=bg)
        p_m_space = doc.add_paragraph()
        p_m_space.paragraph_format.space_before = Pt(0)
        p_m_space.paragraph_format.space_after = Pt(8)

    # -----------------------------------------------------------------------
    # Bagian 7: Tabel "Language and mechanics, by page"
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.language_mechanics)
    _add_body_p(doc, strings.language_intro, space_after=6)
    if not assessment_result.language_findings:
        _add_body_p(doc, strings.no_language_findings, space_after=8)
    else:
        lang_table = doc.add_table(rows=0, cols=3)
        lang_table.autofit = False
        lang_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(lang_table, color=HEX_BORDER, sz="4")
        lang_widths = [0.8, 3.1, 3.0]
        l_hdr = lang_table.add_row()
        l_hdr.cells[0].paragraphs[0].add_run(strings.page)
        l_hdr.cells[1].paragraphs[0].add_run(strings.as_written)
        l_hdr.cells[2].paragraphs[0].add_run(strings.suggested)
        _format_table_row(l_hdr, lang_widths, bg_hex=HEX_NAVY, is_header=True)
        for idx, item in enumerate(assessment_result.language_findings):
            row = lang_table.add_row()
            bg = HEX_ZEBRA if idx % 2 == 1 else HEX_WHITE
            row.cells[0].paragraphs[0].add_run(item.page)
            row.cells[1].paragraphs[0].add_run(item.as_written)
            row.cells[2].paragraphs[0].add_run(item.suggested)
            _format_table_row(row, lang_widths, bg_hex=bg)
        p_l_space = doc.add_paragraph()
        p_l_space.paragraph_format.space_before = Pt(0)
        p_l_space.paragraph_format.space_after = Pt(8)


    # -----------------------------------------------------------------------
    # Bagian 8: Demonstration rewrite
    # -----------------------------------------------------------------------
    if assessment_result.demonstration_rewrite:
        demo = assessment_result.demonstration_rewrite
        _add_heading_1(doc, "Demonstration rewrite")
        _add_heading_2(doc, demo.section_title)
        _add_body_p(doc, demo.intro_note, space_after=6)

        # Callout 1: As Written
        c_as = _add_callout_box(
            doc,
            bg_hex=HEX_CALLOUT_BG,
            border_color_hex="94A3B8",
            border_sz="24",
        )
        p_as_title = c_as.paragraphs[0]
        p_as_title.paragraph_format.space_after = Pt(3)
        r_as_t = p_as_title.add_run(demo.as_written_title)
        r_as_t.bold = True
        r_as_t.font.name = "Arial"
        r_as_t.font.size = Pt(9.5)
        r_as_t.font.color.rgb = COLOR_SECONDARY

        p_as_text = c_as.add_paragraph()
        p_as_text.paragraph_format.space_after = Pt(4)
        p_as_text.paragraph_format.line_spacing = 1.15
        r_as_tx = p_as_text.add_run(demo.as_written_text)
        r_as_tx.font.name = "Arial"
        r_as_tx.font.size = Pt(9)
        r_as_tx.font.color.rgb = COLOR_TEXT

        p_as_faults = c_as.add_paragraph()
        p_as_faults.paragraph_format.space_after = Pt(0)
        r_flt_lbl = p_as_faults.add_run("Faults against Budinski rules: ")
        r_flt_lbl.bold = True
        r_flt_lbl.font.name = "Arial"
        r_flt_lbl.font.size = Pt(9)
        r_flt_lbl.font.color.rgb = COLOR_FAIL
        r_flt_val = p_as_faults.add_run(demo.faults_summary)
        r_flt_val.font.name = "Arial"
        r_flt_val.font.size = Pt(9)
        r_flt_val.font.color.rgb = COLOR_TEXT

        doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # Callout 2: Demonstration Form
        c_dm = _add_callout_box(
            doc,
            bg_hex=HEX_DEMO_REWRITE_BG,
            border_color_hex=HEX_DEMO_REWRITE_BORDER,
            border_sz="36",
        )
        p_dm_title = c_dm.paragraphs[0]
        p_dm_title.paragraph_format.space_after = Pt(4)
        r_dm_t = p_dm_title.add_run(demo.demonstration_title)
        r_dm_t.bold = True
        r_dm_t.font.name = "Arial"
        r_dm_t.font.size = Pt(9.5)
        r_dm_t.font.color.rgb = COLOR_PASS

        for item_sentence in demo.demonstration_items:
            p_item = c_dm.add_paragraph()
            p_item.paragraph_format.space_before = Pt(0)
            p_item.paragraph_format.space_after = Pt(3)
            p_item.paragraph_format.line_spacing = 1.15
            r_item = p_item.add_run(item_sentence)
            r_item.font.name = "Arial"
            r_item.font.size = Pt(9)
            r_item.font.color.rgb = COLOR_TEXT

        p_concl = doc.add_paragraph()
        p_concl.paragraph_format.space_before = Pt(6)
        p_concl.paragraph_format.space_after = Pt(10)
        p_concl.paragraph_format.line_spacing = 1.15
        r_concl = p_concl.add_run(demo.conclusion_summary)
        r_concl.italic = True
        r_concl.font.name = "Arial"
        r_concl.font.size = Pt(9.5)
        r_concl.font.color.rgb = COLOR_TEXT

    # -----------------------------------------------------------------------
    # Bagian 9: Scorecard detail
    # -----------------------------------------------------------------------
    _add_heading_1(doc, "Scorecard detail")
    _add_body_p(
        doc,
        "Scored against the 41 items of the Appendix 12 review checklist from Budinski, "
        "Engineers' Guide to Technical Writing (2001). Scores: 1 = disagree, 5 = agree. "
        "Any item scoring 2 or below is treated as requiring rework.",
        space_after=6,
    )

    _add_heading_1(doc, strings.scorecard_detail)

    # Summary table across 4 groups
    sc_summary_table = doc.add_table(rows=0, cols=4)
    sc_summary_table.autofit = False
    sc_summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(sc_summary_table, color=HEX_BORDER, sz="4")
    sc_sum_widths = [1.8, 3.1, 0.7, 1.3]

    s_hdr = sc_summary_table.add_row()
    s_hdr.cells[0].paragraphs[0].add_run("Group")
    s_hdr.cells[1].paragraphs[0].add_run("Focus Area")
    s_hdr.cells[2].paragraphs[0].add_run("Items")
    s_hdr.cells[3].paragraphs[0].add_run("Group Average")
    _format_table_row(s_hdr, sc_sum_widths, bg_hex=HEX_NAVY, is_header=True)

    group_averages = scorecard.group_averages
    g1_avg = group_averages["Group I"]
    g2_avg = group_averages["Group II"]
    g3_avg = group_averages["Group III"]
    g4_avg = group_averages["Group IV"]
    all_scores = [item.score for item in scorecard.items]
    overall_avg = (
        round(sum(all_scores) / len(all_scores), 2) if all_scores else scorecard.overall_average
    )

    group_rows = [
        ("Group I: Technical Content", "Does the document have substance?", g1_avg),
        ("Group II: Style", "Is it written appropriately for the application?", g2_avg),
        ("Group III: Report Mechanics", "Introduction and Procedure", g3_avg),
        ("Group IV: Conclusions & Craft", "Results, Discussion, Conclusions, Craft", g4_avg),
    ]

    for idx, (grp_name, desc, avg) in enumerate(group_rows):
        cnt = sum(1 for item in scorecard.items if item.group in {grp_name.split(":", 1)[0]})
        if not cnt:
            cnt = {"Group I": 9, "Group II": 11, "Group III": 11, "Group IV": 10}.get(
                grp_name.split(":", 1)[0], 0
            )
        row = sc_summary_table.add_row()
        bg = HEX_ZEBRA if idx % 2 == 1 else HEX_WHITE

        r0 = row.cells[0].paragraphs[0].add_run(grp_name)
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(9)
        r0.font.color.rgb = COLOR_NAVY

        r1 = row.cells[1].paragraphs[0].add_run(desc)
        r1.font.name = "Arial"
        r1.font.size = Pt(9)
        r1.font.color.rgb = COLOR_TEXT

        r2 = row.cells[2].paragraphs[0].add_run(str(cnt))
        r2.font.name = "Arial"
        r2.font.size = Pt(9)
        r2.font.color.rgb = COLOR_TEXT

        r3 = row.cells[3].paragraphs[0].add_run(f"{avg:.2f} / 5.00")
        r3.bold = True
        r3.font.name = "Arial"
        r3.font.size = Pt(9)
        r3.font.color.rgb = COLOR_PASS if avg >= 3.0 else COLOR_FAIL

        _format_table_row(row, sc_sum_widths, bg_hex=bg)

    # Overall Summary Row
    ov_row = sc_summary_table.add_row()
    r_ov_lbl = ov_row.cells[0].paragraphs[0].add_run("Overall Average")
    r_ov_lbl.bold = True
    r_ov_lbl.font.name = "Arial"
    r_ov_lbl.font.size = Pt(9.5)
    r_ov_lbl.font.color.rgb = COLOR_NAVY

    item_count = len(scorecard.items) or 41
    r_ov_desc = (
        ov_row.cells[1].paragraphs[0].add_run(f"All {item_count} Checklist Items (Appendix 12)")
    )
    r_ov_desc.bold = True
    r_ov_desc.font.name = "Arial"
    r_ov_desc.font.size = Pt(9)
    r_ov_desc.font.color.rgb = COLOR_TEXT

    r_ov_cnt = ov_row.cells[2].paragraphs[0].add_run(str(item_count))
    r_ov_cnt.bold = True
    r_ov_cnt.font.name = "Arial"
    r_ov_cnt.font.size = Pt(9)

    r_ov_val = ov_row.cells[3].paragraphs[0].add_run(f"{overall_avg:.2f} / 5.00")
    r_ov_val.bold = True
    r_ov_val.font.name = "Arial"
    r_ov_val.font.size = Pt(9.5)
    r_ov_val.font.color.rgb = COLOR_NAVY

    _format_table_row(ov_row, sc_sum_widths, bg_hex=HEX_BANNER)

    p_sc_space = doc.add_paragraph()
    p_sc_space.paragraph_format.space_before = Pt(4)
    p_sc_space.paragraph_format.space_after = Pt(4)

    # Detailed 41-Item Table
    _add_body_p(
        doc,
        "Detailed 41-item evaluation across all four Appendix 12 checklist groups:",
        space_after=4,
    )

    detail_table = doc.add_table(rows=0, cols=4)
    detail_table.autofit = False
    detail_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(detail_table, color=HEX_BORDER, sz="4")
    det_widths = [0.6, 2.7, 0.7, 2.9]

    d_hdr = detail_table.add_row()
    d_hdr.cells[0].paragraphs[0].add_run("Item")
    d_hdr.cells[1].paragraphs[0].add_run("Checklist Parameter")
    d_hdr.cells[2].paragraphs[0].add_run("Score")
    d_hdr.cells[3].paragraphs[0].add_run("Reviewer Note")
    _format_table_row(d_hdr, det_widths, bg_hex=HEX_NAVY, is_header=True)

    def _get_item_tuple(
        prefix: str, idx: int, item: ScoreItem, default_name: str
    ) -> tuple[str, str, int, str]:
        code = f"{prefix}.{idx}"
        name = item.name or default_name
        return (code, name, item.score, item.note)

    if scorecard.items:
        dynamic_groups: dict[str, list[tuple[str, str, int, str]]] = {}
        for item in scorecard.items:
            dynamic_groups.setdefault(item.group, []).append(
                (item.item_id, item.item_id, item.score, item.note)
            )
        group_i_items = dynamic_groups.get("Group I", [])
        group_ii_items = dynamic_groups.get("Group II", [])
        group_iii_items = dynamic_groups.get("Group III", [])
        group_iv_items = dynamic_groups.get("Group IV", [])
    else:
        tc = scorecard.technical_content
        st = scorecard.style
        rm = scorecard.report_mechanics
        cc = scorecard.conclusions_and_craft
        if not any((tc, st, rm, cc)):
            group_i_items = []
            group_ii_items = []
            group_iii_items = []
            group_iv_items = []
        else:
            if not all((tc, st, rm, cc)):
                raise ValueError("Legacy scorecard groups are required when items is empty")
            group_i_items = [
                _get_item_tuple("I", 1, tc.message_clear, "The message to the reader is clear"),
                _get_item_tuple("I", 2, tc.logical_approach, "The engineering approach is logical"),
                _get_item_tuple("I", 3, tc.adequate_research, "Adequate research of previous work"),
                _get_item_tuple(
                    "I", 4, tc.adequate_comparison, "Adequate comparison with work of others"
                ),
                _get_item_tuple(
                    "I", 5, tc.conclusions_supported, "Conclusions supported by the work"
                ),
                _get_item_tuple("I", 6, tc.value_stated, "The value of the work is clearly stated"),
                _get_item_tuple("I", 7, tc.objective_met, "The work met the stated objective"),
                _get_item_tuple(
                    "I", 8, tc.original_free_of_plagiarism, "Original and free of plagiarism"
                ),
                _get_item_tuple("I", 9, tc.timely, "Timely"),
            ]
            group_ii_items = [
                _get_item_tuple("II", 1, st.objective_tone, "Objective, neutral tone"),
                _get_item_tuple("II", 2, st.sections_logical, "Sections are logical"),
                _get_item_tuple("II", 3, st.readership_level, "Writing level suits readership"),
                _get_item_tuple("II", 4, st.free_of_jargon, "Free of jargon and commercialism"),
                _get_item_tuple("II", 5, st.english_usage, "Use of English is satisfactory"),
                _get_item_tuple("II", 6, st.concise, "Understandable and concise"),
                _get_item_tuple("II", 7, st.interesting, "Interesting"),
                _get_item_tuple("II", 8, st.free_of_personal_opinion, "Free of personal opinion"),
                _get_item_tuple("II", 9, st.no_over_explain, "Does not over-explain"),
                _get_item_tuple(
                    "II", 10, st.standard_writing_practice, "Conforms to writing practice"
                ),
                _get_item_tuple("II", 11, st.layout_and_whitespace, "Page layout and whitespace"),
            ]
            group_iii_items = [
                _get_item_tuple(
                    "III", 1, rm.sufficient_background, "Sufficient background information"
                ),
                _get_item_tuple("III", 2, rm.purpose_of_work_clear, "Purpose of the work is clear"),
                _get_item_tuple(
                    "III", 3, rm.objective_of_work_clear, "Objective of the work is clear"
                ),
                _get_item_tuple(
                    "III", 4, rm.purpose_of_report_clear, "Purpose of the report is clear"
                ),
                _get_item_tuple(
                    "III", 5, rm.objective_of_report_clear, "Objective of the report is clear"
                ),
                _get_item_tuple("III", 6, rm.format_stated, "Format of the report is stated"),
                _get_item_tuple(
                    "III", 7, rm.work_referenced, "Work of others adequately referenced"
                ),
                _get_item_tuple(
                    "III", 8, rm.experimental_steps_outlined, "Experimental steps outlined"
                ),
                _get_item_tuple(
                    "III", 9, rm.adequate_detail_to_repeat, "Adequate detail to repeat"
                ),
                _get_item_tuple(
                    "III", 10, rm.free_of_trade_names, "Free of unnecessary trade names"
                ),
                _get_item_tuple(
                    "III", 11, rm.test_standards_cited, "Test standards properly cited"
                ),
            ]
            group_iv_items = [
                _get_item_tuple("IV", 1, cc.results_clearly_stated, "Results clearly stated"),
                _get_item_tuple(
                    "IV", 2, cc.results_free_of_discussion, "Results free of discussion"
                ),
                _get_item_tuple("IV", 3, cc.graphs_and_tables_proper, "Graphs and tables proper"),
                _get_item_tuple("IV", 4, cc.sufficient_results, "Sufficient results presented"),
                _get_item_tuple(
                    "IV", 5, cc.discussion_relates_to_others, "Discussion relates to others"
                ),
                _get_item_tuple(
                    "IV", 6, cc.discussion_length_appropriate, "Discussion length appropriate"
                ),
                _get_item_tuple(
                    "IV", 7, cc.conclusions_follow_from_results, "Conclusions follow results"
                ),
                _get_item_tuple("IV", 8, cc.conclusions_clear, "Conclusions clear and unambiguous"),
                _get_item_tuple(
                    "IV", 9, cc.references_properly_attributed, "References attributed"
                ),
                _get_item_tuple(
                    "IV", 10, cc.sentence_paragraph_length, "Sentence and paragraph length"
                ),
            ]

    all_groups_data = [
        (
            "GROUP I: TECHNICAL CONTENT",
            "Does the document have substance?",
            g1_avg,
            group_i_items,
        ),
        (
            "GROUP II: STYLE",
            "Is it written appropriately for the application?",
            g2_avg,
            group_ii_items,
        ),
        (
            "GROUP III: REPORT MECHANICS",
            "Introduction and Procedure",
            g3_avg,
            group_iii_items,
        ),
        (
            "GROUP IV: CONCLUSIONS & CRAFT",
            "Results, Discussion, Conclusions, Craft",
            g4_avg,
            group_iv_items,
        ),
    ]

    for g_title, g_desc, g_avg, items in all_groups_data:
        # Group Spanning Banner Row
        banner_row = detail_table.add_row()
        banner_cell = banner_row.cells[0]
        banner_cell.merge(banner_row.cells[3])
        _set_cell_shading(banner_cell, HEX_BANNER)
        _set_cell_margins(banner_cell, top=100, bottom=100, left=140, right=140)
        _apply_cant_split(banner_row)

        p_b = banner_cell.paragraphs[0]
        p_b.paragraph_format.space_before = Pt(0)
        p_b.paragraph_format.space_after = Pt(0)
        r_b = p_b.add_run(f"{g_title} — {g_desc}  (Average: {g_avg:.2f} / 5.00)")
        r_b.bold = True
        r_b.font.name = "Arial"
        r_b.font.size = Pt(9.5)
        r_b.font.color.rgb = COLOR_NAVY

        for idx, (code, name, score, note) in enumerate(items):
            row = detail_table.add_row()
            bg = HEX_ZEBRA if idx % 2 == 1 else HEX_WHITE

            p0 = row.cells[0].paragraphs[0]
            r0 = p0.add_run(code)
            r0.bold = True
            r0.font.name = "Arial"
            r0.font.size = Pt(9)
            r0.font.color.rgb = COLOR_NAVY

            p1 = row.cells[1].paragraphs[0]
            r1 = p1.add_run(name)
            r1.font.name = "Arial"
            r1.font.size = Pt(9)
            r1.font.color.rgb = COLOR_TEXT

            p2 = row.cells[2].paragraphs[0]
            is_rework = score <= 2
            score_str = f"{score} (Rework)" if is_rework else str(score)
            r2 = p2.add_run(score_str)
            r2.bold = True
            r2.font.name = "Arial"
            r2.font.size = Pt(9)
            r2.font.color.rgb = COLOR_FAIL if is_rework else COLOR_TEXT

            p3 = row.cells[3].paragraphs[0]
            r3 = p3.add_run(note)
            r3.font.name = "Arial"
            r3.font.size = Pt(9)
            r3.font.color.rgb = COLOR_TEXT

            _format_table_row(row, det_widths, bg_hex=bg)

    p_det_space = doc.add_paragraph()
    p_det_space.paragraph_format.space_before = Pt(0)
    p_det_space.paragraph_format.space_after = Pt(8)

    # -----------------------------------------------------------------------
    # Bagian 10: What this document does well
    # -----------------------------------------------------------------------
    _add_heading_1(doc, "What this document does well")
    _add_body_p(
        doc,
        "Positive engineering writing practices and structural strengths observed:",
        space_after=6,
    )

    for index, item_text in enumerate(assessment_result.what_it_does_well, 1):
        p_good = doc.add_paragraph()
        p_good.paragraph_format.space_before = Pt(0)
        p_good.paragraph_format.space_after = Pt(5)
        p_good.paragraph_format.line_spacing = 1.15
        r_num = p_good.add_run(f"{index}.  ")
        r_num.bold = True
        r_num.font.name = "Arial"
        r_num.font.size = Pt(9.5)
        r_num.font.color.rgb = COLOR_NAVY
        r_txt = p_good.add_run(item_text)
        r_txt.font.name = "Arial"
        r_txt.font.size = Pt(9.5)
        r_txt.font.color.rgb = COLOR_TEXT

    p_good_space = doc.add_paragraph()
    p_good_space.paragraph_format.space_before = Pt(0)
    p_good_space.paragraph_format.space_after = Pt(8)

    # -----------------------------------------------------------------------
    # Bagian 11: Limits of this review & REVIEWSCORE summary string
    # -----------------------------------------------------------------------
    _add_heading_1(doc, strings.limits_of_review)

    for item_text in assessment_result.limits_of_review:
        _add_body_p(doc, item_text, space_after=6)

    # REVIEWSCORE Callout Box
    score_str = assessment_result.review_score_string or scorecard.review_score_string
    if score_str:
        c_rs = _add_callout_box(
            doc,
            bg_hex="F1F5F9",
            border_color_hex=HEX_NAVY,
            border_sz="12",
        )
        p_rs = c_rs.paragraphs[0]
        p_rs.paragraph_format.space_before = Pt(0)
        p_rs.paragraph_format.space_after = Pt(0)
        r_rs = p_rs.add_run(score_str)
        r_rs.bold = True
        r_rs.font.name = "Consolas"
        r_rs.font.size = Pt(9)
        r_rs.font.color.rgb = COLOR_NAVY

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def create_review_report_template(output_path: Path | str | None = None) -> bytes:
    """
    Generate a baseline blank review report template DOCX file with pre-configured
    margins, headers, footers, and styles.
    """
    doc = docx.Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = COLOR_TEXT

    # Page Header
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_hdr = hp.add_run(
        "Review of Technical Document — writing review only  |  DOCUMENT REVIEW · ENGINEERING"
    )
    r_hdr.font.name = "Arial"
    r_hdr.font.size = Pt(8)
    r_hdr.font.color.rgb = COLOR_MUTED

    # Page Footer
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_ftr = fp.add_run("Review Report    Page ")
    r_ftr.font.name = "Arial"
    r_ftr.font.size = Pt(8)
    r_ftr.font.color.rgb = COLOR_MUTED
    r_ftr._r.append(parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="PAGE"/>'))

    r_of = fp.add_run(" of ")
    r_of.font.name = "Arial"
    r_of.font.size = Pt(8)
    r_of.font.color.rgb = COLOR_MUTED
    r_of._r.append(parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="NUMPAGES"/>'))

    p_init = doc.add_paragraph()
    r_init = p_init.add_run("DOCUMENT REVIEW TEMPLATE (BUDINSKI APPENDIX 12)")
    r_init.bold = True
    r_init.font.name = "Arial"
    r_init.font.size = Pt(16)
    r_init.font.color.rgb = COLOR_NAVY

    output = io.BytesIO()
    doc.save(output)
    doc_bytes = output.getvalue()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(doc_bytes)

    return doc_bytes
