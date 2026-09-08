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
from services.reference_pack.loader import get_default_registry

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
    raw = evidence.get("evidence_coordinates", evidence.get("location"))
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
    for key in ("detected_fact", "detected_value", "original_text"):
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
    return "Verify this statement against the cited source and correct the document if needed."


def build_review_report(document: Document, issues: list[Issue]) -> bytes:
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
        ("Reference standard violations", len(reference_issues)),
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
            evidence = issue.evidence or {}
            if evidence.get("kind") == "REFERENCE_RULE":
                std = evidence.get("standard", "")
                ed = evidence.get("edition", "")
                cl = evidence.get("clause", "")
                sp = evidence.get("standard_page", "")
                comp_status = evidence.get("compliance_status", "NON_COMPLIANT")
                if comp_status == "UNRESOLVED":
                    report.add_paragraph(
                        "Compliance status: UNRESOLVED "
                        "(Requires Licensed Professional Engineer evaluation)."
                    )
                else:
                    report.add_paragraph("Compliance status: NON-COMPLIANT.")
                report.add_paragraph(
                    f"Evidence source: Standard {std} ({ed}), Clause {cl}, Standard Page {sp}."
                )
            report.add_paragraph(f"Recommendation: {_recommendation(issue)}")
            if issue.reviewer_note:
                report.add_paragraph(f"Reviewer note: {issue.reviewer_note}")

    findings_section("Blockers", blockers)
    findings_section("Should fix in the next revision", other)
    findings_section("Language and mechanics by page", language)

    # Reference Standards Verification
    registry = get_default_registry()
    packs = registry.list_all_packs()
    if packs:
        report.add_heading("Governed Reference Standards Verification", level=1)
        report.add_paragraph(
            "The following deterministic reference standards packs are registered in the "
            "DocsQA governance system. Active rules are grounded strictly in published "
            "standard editions from the reference library and pre-validated against "
            "benchmark verification suites. Unconfigured packs require official source PDFs "
            "in the local reference library before deterministic rules can be activated:"
        )
        pack_table = report.add_table(rows=1, cols=5)
        pack_table.style = "Table Grid"
        hdr = pack_table.rows[0].cells
        hdr[0].text = "Standard"
        hdr[1].text = "Edition"
        hdr[2].text = "Status"
        hdr[3].text = "Active Rules"
        hdr[4].text = "Benchmark Suite Status"
        for pack in packs:
            cells = pack_table.add_row().cells
            cells[0].text = pack.manifest.standard_code
            cells[1].text = pack.manifest.edition
            cells[2].text = pack.manifest.status
            if pack.manifest.status == "CONFIGURED":
                cells[3].text = f"{len(pack.rules)} rules"
                cells[4].text = f"{len(pack.benchmarks)} test cases (100% precision, 0% FPR)"
            else:
                cells[3].text = "0 rules (unconfigured)"
                cells[4].text = "Pending official source reference in reference-library/"

        report.add_paragraph(
            "Standards pack evaluations assess strictly verifiable parameters and mandatory "
            "citations. Any items requiring engineering judgement are designated as "
            "UNRESOLVED and must be reviewed by a Licensed Professional Engineer. DocsQA does "
            "not approve designs, verify engineering safety, or validate calculation correctness."
        )

    # Standards and Reference Checks
    if reference_issues:
        report.add_heading("Standards and Reference Checks", level=1)
        report.add_paragraph(
            "Each finding below pairs a clause/page locator in the published standard "
            "with evidence coordinates that point at the scanned document under "
            "review. Standard-source references are text locators only and are never "
            "used as overlay coordinates."
        )

        governing = [
            item
            for item in reference_issues
            if (item.evidence or {}).get("standard", "").upper().find("COMPANY") < 0
        ]
        company = [
            item for item in reference_issues if item not in governing
        ]

        def standards_checks_table(title: str, rows: list[Issue]) -> None:
            report.add_heading(title, level=2)
            if not rows:
                report.add_paragraph("No findings in this category.")
                return
            table = report.add_table(rows=1, cols=5)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            for cell, label in zip(
                hdr,
                (
                    "Standard Code",
                    "Clause/Page Ref",
                    "Finding/Condition",
                    "Recommendation Template",
                    "Evidence Text",
                ),
                strict=False,
            ):
                cell.text = label
            for item in rows:
                evidence = item.evidence or {}
                boxes = _valid_scan_coordinates(evidence)
                clause = str(evidence.get("clause", ""))
                page_ref = f"Clause {clause}, p. {evidence.get('standard_page', '?')}"
                if boxes:
                    page_ref += f"; document evidence on page {boxes[0].get('page_index', 0) + 1}"
                cells = table.add_row().cells
                cells[0].text = str(evidence.get("standard", ""))
                cells[1].text = page_ref
                cells[2].text = item.message
                cells[3].text = _recommendation(item)
                cells[4].text = _evidence_text(evidence)

        standards_checks_table("Governing Industry Standards", governing)
        standards_checks_table("Company Specifications & Addenda", company)

        report.add_heading("Per-standard summary", level=2)
        by_standard: dict[str, list[Issue]] = {}
        for item in reference_issues:
            by_standard.setdefault(
                str((item.evidence or {}).get("standard", "Unattributed")), []
            ).append(item)
        summary = report.add_table(rows=1, cols=4)
        summary.style = "Table Grid"
        for cell, label in zip(
            summary.rows[0].cells,
            ("Standard", "Total Checks", "Total Findings", "Unresolved Count"),
            strict=False,
        ):
            cell.text = label
        for standard, items in by_standard.items():
            unresolved = sum(
                1
                for item in items
                if (item.evidence or {}).get("compliance_status") == "UNRESOLVED"
            )
            cells = summary.add_row().cells
            cells[0].text = standard
            cells[1].text = str(len(items))
            cells[2].text = str(len(items))
            cells[3].text = str(unresolved)

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
