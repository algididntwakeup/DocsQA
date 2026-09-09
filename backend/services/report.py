"""Deterministic DOCX review report builder.

The report describes document-internal evidence only; it never certifies
engineering adequacy, code compliance, or operational safety.
"""
from __future__ import annotations

import io
from collections import Counter
from collections.abc import Iterable
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


_SEVERITY_ORDER = {
    "BLOCKER": 0,
    "CRITICAL": 1,
    "HIGH": 2,
    "MAJOR": 3,
    "MEDIUM": 4,
    "MINOR": 5,
    "LOW": 6,
    "INFO": 7,
}


def _severity(issue: Issue) -> str:
    return str(getattr(issue.severity, "value", issue.severity)).upper()


def _paragraph_key(issue: Issue) -> tuple[Any, ...]:
    """Group language findings that point to the same extracted paragraph."""
    evidence = issue.evidence or {}
    location = evidence.get("location") or evidence.get("original_location") or {}
    if not isinstance(location, dict):
        return (issue.page_number, issue.type)
    page = location.get("page_index", issue.page_number)
    # Extraction does not persist a paragraph id. A 24-point band is a stable,
    # conservative approximation that prevents one typo from becoming a page-long list.
    y0 = location.get("y0")
    band = round(float(y0) / 24) if isinstance(y0, (int, float)) else None
    return (page, band, issue.type)


def _group_issue_rows(issues: Iterable[Issue]) -> list[tuple[Issue, int, str]]:
    """Collapse repeated findings into one compact report row per rule."""
    grouped: dict[tuple[Any, ...], Issue] = {}
    counts: dict[tuple[Any, ...], int] = {}
    locations: dict[tuple[Any, ...], list[str]] = {}
    for issue in issues:
        evidence = issue.evidence or {}
        category = str(getattr(issue.category, "value", issue.category))
        if category in {"LINGUISTIC", "SPELLING", "GRAMMAR", "DICTIONARY"}:
            key = (category, issue.type, _paragraph_key(issue))
        else:
            key = (category, issue.type)
        if key not in grouped:
            grouped[key] = issue
            counts[key] = 1
            locations[key] = []
        else:
            counts[key] += 1
            grouped[key].message = f"{grouped[key].message}; {issue.message}"
            if evidence.get("kind") == "REFERENCE_RULE" and evidence.get("standard"):
                grouped[key].message += f" [standard: {evidence['standard']}]"
            if not grouped[key].reviewer_note and issue.reviewer_note:
                grouped[key].reviewer_note = issue.reviewer_note
        if evidence.get("kind") == "REFERENCE_DRIFT":
            location = str(evidence.get("referenced_page_label", "not located"))
        else:
            location = _page(issue)
        if location not in locations[key]:
            locations[key].append(location)
    rows = [
        (issue, counts[key], ", ".join(locations[key]))
        for key, issue in grouped.items()
    ]
    return sorted(
        rows,
        key=lambda row: (
            _SEVERITY_ORDER.get(_severity(row[0]), 99),
            str(row[0].created_at),
            str(row[0].id),
        ),
    )


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
    if evidence.get("kind") == "REFERENCE_RULE":
        std = evidence.get("standard", "governing standard")
        clause = evidence.get("clause", "")
        clause_str = f" clause {clause}" if clause else ""
        return f"Align specification and design parameters with {std}{clause_str}."
    if evidence.get("what_would_fix_it"):
        return str(evidence["what_would_fix_it"])
    if evidence.get("suggested_fix"):
        return str(evidence["suggested_fix"])
    return "Verify this statement against the cited source and correct the document if needed."


def build_review_report(
    document: Document,
    issues: list[Issue],
    scorecard: dict[str, Any] | None = None,
    include_minors: bool = False,
) -> bytes:
    """Build a concise evidence-led review report for included findings."""
    included = [
        item
        for item in issues
        if item.included_in_report
        and (include_minors or _severity(item) not in {"MINOR", "INFO", "LOW"})
    ]
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
        item
        for item in included
        if getattr(item.category, "value", str(item.category)) == "BUDINSKI"
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
    if not include_minors:
        suppressed_minors = sum(
            1
            for item in issues
            if item.included_in_report and _severity(item) in {"MINOR", "INFO", "LOW"}
        )
        if suppressed_minors:
            report.add_paragraph(
                f"{suppressed_minors} minor language/mechanics findings are omitted from this "
                "report by default. Use the include-minors export option for the full detail."
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
        ("Reference standard violations", len(reference_issues)),
        ("Language and mechanics", len(language)),
        ("Other consistency findings", len(other)),
    )
    for label, value in scorecard_metrics:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    report.add_heading("The four baseline measures", level=1)
    baseline_table = report.add_table(rows=1, cols=3)
    baseline_table.style = "Table Grid"
    for cell, label in zip(
        baseline_table.rows[0].cells, ("Measure", "Result", "Evidence"), strict=False
    ):
        cell.text = label
    baseline_rows = (
        (
            "Purpose distinct from objective",
            "PASS" if any("purpose" in i.message.lower() for i in budinski) is False else "REVIEW",
            "Extracted purpose/objective signals",
        ),
        (
            "Procedure repeatable",
            "REVIEW",
            "Procedure and methodology text extracted from source",
        ),
        (
            "Conclusions valid",
            "REVIEW",
            "Conclusion section and cross-page findings",
        ),
        (
            "Recommendations actionable",
            "REVIEW",
            "Owner/date evidence is checked where available",
        ),
    )
    for label, result, evidence in baseline_rows:
        cells = baseline_table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = label, result, evidence

    if scorecard:
        report.add_heading("Budinski Appendix 12 scorecard", level=1)
        baseline = scorecard.get("baseline_measures") or {}
        baseline_keys = (
            "purpose_distinct_from_objective",
            "procedure_repeatable",
            "conclusions_valid",
            "recommendations_actionable",
        )
        report.add_paragraph(
            f"Baseline score: {sum(1 for k in baseline_keys if baseline.get(k) is True)} of 4."
        )
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
        score_table = report.add_table(rows=1, cols=4)
        score_table.style = "Table Grid"
        for cell, label in zip(
            score_table.rows[0].cells,
            ("Group", "Checklist item", "Score", "Note"),
            strict=False,
        ):
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

    finding_rows = _group_issue_rows(included)
    def add_findings_table(title: str, rows: list[tuple[Issue, int, str]]) -> None:
        report.add_heading(title, level=1)
        if not rows:
            report.add_paragraph("None identified.")
            return
        table = report.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        for cell, label in zip(
            table.rows[0].cells,
            ("Severity", "Rule", "Location", "What should be fixed", "Count"),
            strict=False,
        ):
            cell.text = label
        for issue, occurrence_count, locations in rows:
            evidence = issue.evidence or {}
            kind = evidence.get("kind")
            location = locations
            if kind == "REFERENCE_DRIFT":
                location = f"{evidence.get('label', 'reference')}; printed pages {locations}"
            elif kind == "REFERENCE_RULE":
                boxes = _valid_scan_coordinates(evidence)
                if boxes:
                    location = f"document page {boxes[0].get('page_index', 0) + 1}"
            fix = _recommendation(issue)
            if evidence.get("kind") == "REFERENCE_RULE":
                fix = (
                    f"{fix} Standard {evidence.get('standard', '?')}; "
                    f"Source: Clause {evidence.get('clause', '?')}, "
                    f"standard page {evidence.get('standard_page', '?')}."
                )
            if kind == "REFERENCE_DRIFT":
                fix = (
                    f"Correct {evidence.get('label', 'the reference')} and verify printed page "
                    f"{evidence.get('referenced_page_label', '?')}."
                )
            if issue.reviewer_note:
                fix = f"{fix} Reviewer note: {issue.reviewer_note}"
            evidence_summary = _evidence_text(evidence)
            if evidence_summary != "(see finding detail)":
                fix = f"{fix} Evidence: {evidence_summary}."
            cells = table.add_row().cells
            cells[0].text = _severity(issue)
            cells[1].text = issue.type
            cells[2].text = location
            cells[3].text = f"{fix} {issue.message}"
            cells[4].text = str(occurrence_count)

    blocker_rows = [
        row for row in finding_rows if _severity(row[0]) in {"BLOCKER", "CRITICAL", "MAJOR", "HIGH"}
    ]
    next_revision_rows = [row for row in finding_rows if row not in blocker_rows]
    add_findings_table("Blockers", blocker_rows)
    for issue, _count, _locations in blocker_rows:
        report.add_paragraph(f"{_severity(issue)}: {issue.type} - {issue.message}")
    add_findings_table("Next revision findings", next_revision_rows)

    report.add_heading("Language and mechanics", level=1)
    if not language:
        report.add_paragraph("No language or mechanics findings are included.")
    else:
        grouped_language: dict[str, list[Issue]] = {}
        for item in language:
            grouped_language.setdefault(item.type, []).append(item)
        summary_parts = []
        for rule, findings in sorted(grouped_language.items()):
            pages = sorted({str(_page(item)) for item in findings})
            summary_parts.append(
                f"{len(findings)} {rule.lower()} finding(s) on page(s) {', '.join(pages)}"
            )
        report.add_paragraph(
            "Language and mechanics findings are consolidated by rule to keep the report "
            "actionable without repeating every individual token: " + "; ".join(summary_parts) + "."
        )

    report.add_heading("Scope and limitations", level=1)
    report.add_paragraph(
        "This is an internal-consistency and document-quality review. It does not approve "
        "engineering work, certify safety, or validate design fitness or external compliance."
    )
    report.add_paragraph("REVIEWSCORE | generated deterministically from included findings")
    output = io.BytesIO()
    report.save(output)
    return output.getvalue()
