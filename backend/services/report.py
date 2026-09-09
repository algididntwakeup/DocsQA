"""Deterministic DOCX review report builder.

The report describes document-internal evidence only; it never certifies
engineering adequacy, code compliance, or operational safety.
"""
from __future__ import annotations

import io
from collections import Counter
from typing import TYPE_CHECKING, Any

from docx import Document as WordDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from domain.enums import Severity

if TYPE_CHECKING:
    from models.document import Document
    from models.issue import Issue


def _page(issue: Issue) -> str:
    return str(issue.page_number) if issue.page_number else "not located"


def _valid_scan_coordinates(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Bounding boxes pointing at the scanned document itself (not the source standard).

    Standard-source provenance is deliberately kept as text locators (clause and
    standard page) only; any coordinate-like payload referencing the standard
    source is rejected so PDF overlays never point at the wrong document.
    """
    raw = evidence.get(
        "evidence_coordinates",
        evidence.get("location", evidence.get("bounding_box")),
    )
    boxes = raw if isinstance(raw, list) else [raw]
    valid = []
    for box in boxes:
        if not isinstance(box, dict):
            continue
        try:
            if (
                0 <= int(box["x0"]) <= int(box["x1"])
                and 0 <= int(box["y0"]) <= int(box["y1"])
                and int(box["page_width"]) > 0
                and int(box["x1"]) <= int(box["page_width"])
                and int(box["page_height"]) > 0
                and int(box["y1"]) <= int(box["page_height"])
            ):
                valid.append(box)
        except (KeyError, TypeError, ValueError):
            continue
    return valid


def _evidence_text(evidence: dict[str, Any]) -> str:
    for key in (
        "detected_fact",
        "detected_value",
        "original_text",
        "what_it_says",
        "snippet",
        "last_text",
        "text",
    ):
        value = evidence.get(key)
        if value:
            return str(value)
    return "(see finding detail)"


def _recommendation(issue: Issue) -> str:
    evidence = issue.evidence or {}
    suggestion = evidence.get("suggestion")
    if suggestion:
        return f"Review and apply the suggested correction: {suggestion}"
    if evidence.get("what_would_fix_it"):
        return str(evidence["what_would_fix_it"])
    if evidence.get("suggested_fix"):
        return str(evidence["suggested_fix"])
    return "Verify this statement against the cited source and correct the document if needed."


def build_review_report(
    document: Document,
    issues: list[Issue],
    scorecard: dict[str, Any] | None = None,
) -> bytes:
    """Build a concise evidence-led review report for included findings."""
    included = [item for item in issues if item.included_in_report]
    counts = Counter(getattr(item.severity, "value", str(item.severity)) for item in included)
    blocker_levels = {
        Severity.BLOCKER,
        Severity.CRITICAL,
        Severity.HIGH,
        "BLOCKER",
        "CRITICAL",
        "HIGH",
    }
    blockers = [item for item in included if item.severity in blocker_levels]
    language = [
        item
        for item in included
        if getattr(item.category, "value", str(item.category)) == "LINGUISTIC"
    ]
    reference_issues = [
        item for item in included if (item.evidence or {}).get("kind") == "REFERENCE_RULE"
    ]
    budinski = [
        item for item in included if getattr(item.category, "value", str(item.category)) == "BUDINSKI"
    ]
    layout = [
        item for item in included if getattr(item.category, "value", str(item.category)) == "LAYOUT"
    ]
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

    report.add_heading("The four baseline measures", level=1)
    baseline_table = report.add_table(rows=1, cols=3)
    baseline_table.style = "Table Grid"
    for cell, label in zip(baseline_table.rows[0].cells, ("Measure", "Result", "Evidence"), strict=False):
        cell.text = label
    baseline_rows = (
        ("Purpose distinct from objective", "PASS" if any("purpose" in i.message.lower() for i in budinski) is False else "REVIEW", "Extracted purpose/objective signals"),
        ("Procedure repeatable", "REVIEW", "Procedure and methodology text extracted from source"),
        ("Conclusions valid", "REVIEW", "Conclusion section and cross-page findings"),
        ("Recommendations actionable", "REVIEW", "Owner/date evidence is checked where available"),
    )
    for label, result, evidence in baseline_rows:
        cells = baseline_table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = label, result, evidence

    report.add_heading("Scorecard", level=1)
    table = report.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Measure"
    scorecard_metrics = (
        ("Included findings", len(included)),
        ("Blockers", len(blockers)),
        ("Internal reference checks", len(reference_issues)),
        ("Language and mechanics", len(language)),
        ("Other consistency findings", len(other)),
    )
    for label, value in scorecard_metrics:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    if scorecard:
        report.add_heading("Budinski Appendix 12 scorecard", level=1)
        baseline = scorecard.get("baseline_measures") or {}
        report.add_paragraph(
            f"Baseline score: {sum(1 for key in ('purpose_distinct_from_objective', 'procedure_repeatable', 'conclusions_valid', 'recommendations_actionable') if baseline.get(key) is True)} of 4."
        )
        score_table = report.add_table(rows=1, cols=4)
        score_table.style = "Table Grid"
        for cell, label in zip(score_table.rows[0].cells, ("Group", "Checklist item", "Score", "Note"), strict=False):
            cell.text = label
        for group_key, group_label in (
            ("technical_content", "I. Technical Content"),
            ("style", "II. Style"),
            ("report_mechanics", "III. Report Mechanics"),
            ("conclusions_and_craft", "IV. Conclusions and Craft"),
        ):
            group = scorecard.get(group_key) or {}
            for item_key, item in group.items():
                if not isinstance(item, dict) or "score" not in item:
                    continue
                cells = score_table.add_row().cells
                cells[0].text = group_label
                cells[1].text = str(item.get("name", item_key))
                cells[2].text = str(item.get("score", ""))
                cells[3].text = str(item.get("note", ""))
        report.add_paragraph(
            "Group averages: "
            + ", ".join(
                f"{label} {scorecard.get(key, 0):.2f}"
                for key, label in (
                    ("group_i_average", "I"),
                    ("group_ii_average", "II"),
                    ("group_iii_average", "III"),
                    ("group_iv_average", "IV"),
                )
            )
        )

    def findings_section(title: str, rows: list[Issue]) -> None:
        report.add_heading(title, level=1)
        if not rows:
            report.add_paragraph("No included findings in this section.")
            return
        for index, issue in enumerate(rows, 1):
            report.add_heading(f"{index}. {issue.type} - page {_page(issue)}", level=2)
            report.add_paragraph(f"Detected fact: {issue.message}")
            evidence = issue.evidence or {}
            report.add_paragraph(f"Rule ID: {issue.type}")
            report.add_paragraph(f"Source evidence: {_evidence_text(evidence)}")
            if evidence.get("where_location"):
                report.add_paragraph(f"Evidence location: {evidence['where_location']}")
            report.add_paragraph(f"Recommendation: {_recommendation(issue)}")
            if issue.reviewer_note:
                report.add_paragraph(f"Reviewer note: {issue.reviewer_note}")

    findings_section("Blockers", blockers)
    findings_section("Should fix in the next revision", [item for item in other if item not in budinski and item not in layout])
    findings_section("Budinski technical writing findings", budinski)
    findings_section("Layout and page-continuity findings", layout)
    findings_section("Language and mechanics by page", language)

    # External standards packs are intentionally not evaluated or presented.
    # Citation and bibliography inconsistencies remain ordinary internal findings.

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
