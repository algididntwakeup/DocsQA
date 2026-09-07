"""Deterministic DOCX review report builder.

The report describes document-internal evidence only; it never certifies
engineering adequacy, code compliance, or operational safety.
"""
from __future__ import annotations

import io
from collections import Counter
from typing import TYPE_CHECKING

from docx import Document as WordDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from domain.enums import Severity

if TYPE_CHECKING:
    from models.document import Document
    from models.issue import Issue


def _page(issue: Issue) -> str:
    return str(issue.page_number) if issue.page_number else "not located"


def _recommendation(issue: Issue) -> str:
    evidence = issue.evidence or {}
    suggestion = evidence.get("suggestion")
    if suggestion:
        return f"Review and apply the suggested correction: {suggestion}"
    return "Verify this statement against the cited source and correct the document if needed."


def build_review_report(document: Document, issues: list[Issue]) -> bytes:
    """Build a concise evidence-led review report for included findings."""
    included = [item for item in issues if item.included_in_report]
    counts = Counter(item.severity.value for item in included)
    blockers = [item for item in included if item.severity in {Severity.CRITICAL, Severity.HIGH}]
    language = [item for item in included if item.category.value == "LINGUISTIC"]
    other = [item for item in included if item not in blockers and item not in language]

    report = WordDocument()
    section = report.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    styles = report.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)

    title = report.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("DOCUMENT REVIEW ENGINEERING")
    subtitle = report.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(f"Review of {document.original_filename}").bold = True
    report.add_paragraph("Basis: deterministic internal-consistency review profile.")

    report.add_heading("Summary judgement", level=1)
    report.add_paragraph(
        f"The scan included {len(included)} findings: {counts['CRITICAL']} critical, "
        f"{counts['HIGH']} high, {counts['MEDIUM']} medium and {counts['LOW']} low. "
        "Findings are evidence of possible document inconsistency or writing defects; "
        "they are not engineering approval or proof of design correctness."
    )
    report.add_paragraph(
        "BOTTOM LINE  Resolve the listed blocker findings before reissue, then regenerate "
        "the document navigation and review all referenced values."
    )

    report.add_heading("Scorecard", level=1)
    table = report.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Measure"
    scorecard_metrics = (
        ("Included findings", len(included)),
        ("Blockers", len(blockers)),
        ("Language and mechanics", len(language)),
        ("Other consistency findings", len(other)),
    )
    for label, value in scorecard_metrics:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    def findings_section(title: str, rows: list[Issue]) -> None:
        report.add_heading(title, level=1)
        if not rows:
            report.add_paragraph("No included findings in this section.")
            return
        for index, issue in enumerate(rows, 1):
            report.add_heading(f"{index}. {issue.type} - page {_page(issue)}", level=2)
            report.add_paragraph(f"Detected fact: {issue.message}")
            report.add_paragraph(f"Recommendation: {_recommendation(issue)}")
            if issue.reviewer_note:
                report.add_paragraph(f"Reviewer note: {issue.reviewer_note}")

    findings_section("Blockers", blockers)
    findings_section("Should fix in the next revision", other)
    findings_section("Language and mechanics by page", language)

    report.add_heading("What this document does well", level=1)
    report.add_paragraph(
        "The review records only detected inconsistencies. Absence of a finding is not a "
        "claim that the engineering analysis, calculations, or safety case is correct."
    )
    report.add_heading("Limits of this review", level=1)
    report.add_paragraph(
        "This report assesses internal consistency, technical writing, document structure, "
        "references, and extracted numerical relationships. It does not validate design "
        "fitness, material suitability, regulatory compliance, or safe operation."
    )
    report.add_paragraph("REVIEWSCORE | generated deterministically from included findings")
    output = io.BytesIO()
    report.save(output)
    return output.getvalue()
