"""Multi-Format Export Service for Document Findings and Audit Logs.

Generates:
1. Annotated PDF with visual bounding boxes and callout notes.
2. Multi-sheet Excel (.xlsx) workbook with summary, traceability, linguistic, and audit trail tabs.
3. Flat CSV issue log for data science and downstream reporting.
4. Machine-readable JSON audit package with full evidence and verification metadata.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import openpyxl
import pypdf
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from pypdf.annotations import Rectangle, Text

from domain.enums import IssueCategory, Severity

if TYPE_CHECKING:
    from models.audit import AuditEvent
    from models.document import Document
    from models.issue import Issue
    from services.storage.local import LocalStorage

EXPORT_SCHEMA_VERSION = "1.0"


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
            label = (
                f"[{issue.type}] {issue.severity.value}: {issue.message}\n"
                f"Decision: {issue.decision.value if issue.decision else 'PENDING'}\n"
                f"Disposition: {issue.disposition.value if issue.disposition else 'NONE'}"
            )

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


def export_excel_workbook(
    document: Document,
    issues: list[Issue],
    audit_events: list[AuditEvent],
) -> bytes:
    now = datetime.now(UTC)
    wb = openpyxl.Workbook()

    # Styling definitions
    header_fill = PatternFill(start_color="0B1326", end_color="0B1326", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    section_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    section_font = Font(name="Segoe UI", size=12, bold=True, color="38BDF8")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="0B1326")
    meta_label_font = Font(name="Segoe UI", size=10, bold=True, color="475569")
    meta_val_font = Font(name="Segoe UI", size=10, color="0F172A")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # -------------------------------------------------------------
    # Sheet 1: Summary
    # -------------------------------------------------------------
    ws_summary = cast(Worksheet, wb.active)
    ws_summary.title = "Summary"
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary["A1"] = "DocsQA — Document Inspection & Traceability Summary Log"
    ws_summary["A1"].font = title_font

    ws_summary["A3"] = "DOCUMENT METADATA"
    ws_summary["A3"].font = section_font
    ws_summary["A3"].fill = section_fill
    ws_summary.merge_cells("A3:B3")

    metadata_items = [
        ("Document ID", str(document.id)),
        ("Original Filename", document.original_filename),
        ("Safe Identifier", document.safe_filename),
        ("File SHA-256", document.sha256),
        ("Processing Status", document.status.value),
        ("Review Disposition", document.review_status.value),
        (
            "Uploaded At",
            document.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if document.created_at
            else now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        ),
        ("Export Generated At", now.strftime("%Y-%m-%d %H:%M:%S UTC")),
    ]

    for idx, (label, val) in enumerate(metadata_items, start=4):
        ws_summary[f"A{idx}"] = label
        ws_summary[f"A{idx}"].font = meta_label_font
        ws_summary[f"B{idx}"] = val
        ws_summary[f"B{idx}"].font = meta_val_font

    ws_summary["D3"] = "FINDINGS METRICS"
    ws_summary["D3"].font = section_font
    ws_summary["D3"].fill = section_fill
    ws_summary.merge_cells("D3:E3")

    # Metric counts
    total_count = len(issues)
    traceability_count = sum(1 for i in issues if i.category == IssueCategory.TRACEABILITY)
    linguistic_count = sum(1 for i in issues if i.category == IssueCategory.LINGUISTIC)
    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
    medium_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)
    low_count = sum(1 for i in issues if i.severity == Severity.LOW)
    resolved_count = sum(1 for i in issues if i.decision or i.disposition)
    unresolved_count = total_count - resolved_count

    metric_items = [
        ("Total Findings", total_count),
        ("Traceability Findings", traceability_count),
        ("Linguistic Findings", linguistic_count),
        ("Critical Severity", critical_count),
        ("High Severity", high_count),
        ("Medium Severity", medium_count),
        ("Low Severity", low_count),
        ("Resolved Findings", resolved_count),
        ("Pending Review", unresolved_count),
    ]

    for m_idx, (m_label, m_val) in enumerate(metric_items, start=4):
        ws_summary[f"D{m_idx}"] = m_label
        ws_summary[f"D{m_idx}"].font = meta_label_font
        ws_summary[f"E{m_idx}"] = m_val
        ws_summary[f"E{m_idx}"].font = meta_val_font

    # -------------------------------------------------------------
    # Sheet 2: Traceability Issues
    # -------------------------------------------------------------
    ws_trace = wb.create_sheet(title="Traceability Issues")
    ws_trace.views.sheetView[0].showGridLines = True
    trace_headers = [
        "Issue ID",
        "Rule Type",
        "Severity",
        "Page",
        "Message",
        "Stated Value",
        "Computed Value",
        "Delta",
        "Tolerance",
        "Review Decision",
        "Reviewer Comment",
        "Decided By",
        "Lead Disposition",
        "Disposition Justification",
        "Disposed By",
        "Version",
        "Created At",
    ]
    ws_trace.append(trace_headers)
    for col_idx in range(1, len(trace_headers) + 1):
        cell = ws_trace.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    trace_issues = [
        i for i in issues if i.category in (IssueCategory.TRACEABILITY, IssueCategory.SYSTEM)
    ]
    for row_idx, issue in enumerate(trace_issues, start=2):
        ev = issue.evidence or {}
        locs = _extract_locations(ev)
        page_str = str(locs[0][0] + 1) if locs else "N/A"

        row = [
            str(issue.id),
            issue.type,
            issue.severity.value,
            page_str,
            issue.message,
            str(ev.get("stated_value", "")),
            str(ev.get("computed_value", "")),
            str(ev.get("delta", "")),
            str(ev.get("tolerance", "")),
            issue.decision.value if issue.decision else "PENDING",
            issue.decision_comment or "",
            issue.decision_by or "",
            issue.disposition.value if issue.disposition else "NONE",
            issue.disposition_justification or "",
            issue.disposition_by or "",
            issue.version,
            issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else "",
        ]
        ws_trace.append(row)
        if row_idx % 2 == 1:
            for col_idx in range(1, len(trace_headers) + 1):
                ws_trace.cell(row=row_idx, column=col_idx).fill = alt_fill

    # -------------------------------------------------------------
    # Sheet 3: Linguistic Issues
    # -------------------------------------------------------------
    ws_ling = wb.create_sheet(title="Linguistic Issues")
    ws_ling.views.sheetView[0].showGridLines = True
    ling_headers = [
        "Issue ID",
        "Rule Type",
        "Severity",
        "Page",
        "Message",
        "Original Text",
        "Suggestion",
        "Review Decision",
        "Reviewer Comment",
        "Decided By",
        "Lead Disposition",
        "Version",
        "Created At",
    ]
    ws_ling.append(ling_headers)
    for col_idx in range(1, len(ling_headers) + 1):
        cell = ws_ling.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ling_issues = [i for i in issues if i.category == IssueCategory.LINGUISTIC]
    for row_idx, issue in enumerate(ling_issues, start=2):
        ev = issue.evidence or {}
        locs = _extract_locations(ev)
        page_str = str(locs[0][0] + 1) if locs else "N/A"

        row = [
            str(issue.id),
            issue.type,
            issue.severity.value,
            page_str,
            issue.message,
            str(ev.get("original_text", "")),
            str(ev.get("suggestion", "")),
            issue.decision.value if issue.decision else "PENDING",
            issue.decision_comment or "",
            issue.decision_by or "",
            issue.disposition.value if issue.disposition else "NONE",
            issue.version,
            issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else "",
        ]
        ws_ling.append(row)
        if row_idx % 2 == 1:
            for col_idx in range(1, len(ling_headers) + 1):
                ws_ling.cell(row=row_idx, column=col_idx).fill = alt_fill

    # -------------------------------------------------------------
    # Sheet 4: Audit Trail
    # -------------------------------------------------------------
    ws_audit = wb.create_sheet(title="Audit Trail")
    ws_audit.views.sheetView[0].showGridLines = True
    audit_headers = [
        "Event ID",
        "Timestamp",
        "Actor ID",
        "Actor Role",
        "Action",
        "Issue ID",
        "Justification / Notes",
        "Previous State",
        "New State",
    ]
    ws_audit.append(audit_headers)
    for col_idx in range(1, len(audit_headers) + 1):
        cell = ws_audit.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, event in enumerate(audit_events, start=2):
        row = [
            str(event.id),
            event.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if event.created_at
            else now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            event.actor_id,
            event.actor_role,
            event.action,
            str(event.issue_id) if event.issue_id else "DOCUMENT",
            event.notes or "",
            json.dumps(event.previous_state) if event.previous_state else "",
            json.dumps(event.new_state) if event.new_state else "",
        ]
        ws_audit.append(row)
        if row_idx % 2 == 1:
            for col_idx in range(1, len(audit_headers) + 1):
                ws_audit.cell(row=row_idx, column=col_idx).fill = alt_fill

    # Auto-adjust column widths for all sheets
    for ws in (ws_summary, ws_trace, ws_ling, ws_audit):
        for col in ws.columns:
            max_len = 0
            for cell in col:
                cell.border = thin_border
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            col_idx = int(col[0].column) if col[0].column is not None else 1
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 50))

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def export_csv_issues(
    document: Document,
    issues: list[Issue],
) -> str:
    """Generate a clean flat CSV export of all findings."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    headers = [
        "document_id",
        "issue_id",
        "category",
        "type",
        "severity",
        "page",
        "message",
        "stated_value",
        "computed_value",
        "original_text",
        "suggestion",
        "decision",
        "decision_comment",
        "decision_by",
        "disposition",
        "disposition_justification",
        "disposition_by",
        "version",
        "created_at",
    ]
    writer.writerow(headers)

    for issue in issues:
        ev = issue.evidence or {}
        locs = _extract_locations(ev)
        page_str = str(locs[0][0] + 1) if locs else ""

        writer.writerow(
            [
                str(document.id),
                str(issue.id),
                issue.category.value,
                issue.type,
                issue.severity.value,
                page_str,
                issue.message,
                str(ev.get("stated_value", "")),
                str(ev.get("computed_value", "")),
                str(ev.get("original_text", "")),
                str(ev.get("suggestion", "")),
                issue.decision.value if issue.decision else "PENDING",
                issue.decision_comment or "",
                issue.decision_by or "",
                issue.disposition.value if issue.disposition else "NONE",
                issue.disposition_justification or "",
                issue.disposition_by or "",
                issue.version,
                issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else "",
            ]
        )

    return buffer.getvalue()


def export_json_audit_bundle(
    document: Document,
    issues: list[Issue],
    audit_events: list[AuditEvent],
) -> dict[str, Any]:
    """Generate a comprehensive JSON verification artifact."""
    now = datetime.now(UTC)

    counts_by_category: dict[str, int] = {}
    counts_by_severity: dict[str, int] = {}
    critical_count = 0
    resolved_count = 0

    for issue in issues:
        cat_key = issue.category.value
        counts_by_category[cat_key] = counts_by_category.get(cat_key, 0) + 1

        sev_key = issue.severity.value
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1

        if issue.severity == Severity.CRITICAL:
            critical_count += 1
        if issue.decision or issue.disposition:
            resolved_count += 1

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": now.isoformat(),
        "document": {
            "id": str(document.id),
            "filename": document.original_filename,
            "safe_filename": document.safe_filename,
            "file_hash": document.sha256,
            "status": document.status.value,
            "review_status": document.review_status.value,
            "created_at": document.created_at.isoformat()
            if document.created_at
            else now.isoformat(),
            "updated_at": document.updated_at.isoformat()
            if document.updated_at
            else now.isoformat(),
        },
        "summary": {
            "total_issues": len(issues),
            "counts_by_category": counts_by_category,
            "counts_by_severity": counts_by_severity,
            "critical_count": critical_count,
            "resolved_count": resolved_count,
            "unresolved_count": len(issues) - resolved_count,
        },
        "issues": [
            {
                "id": str(i.id),
                "document_id": str(i.document_id),
                "category": i.category.value,
                "type": i.type,
                "severity": i.severity.value,
                "confidence": i.confidence,
                "message": i.message,
                "evidence": i.evidence,
                "decision": i.decision.value if i.decision else None,
                "decision_comment": i.decision_comment,
                "decision_by": i.decision_by,
                "disposition": i.disposition.value if i.disposition else None,
                "disposition_justification": i.disposition_justification,
                "disposition_by": i.disposition_by,
                "version": i.version,
                "created_at": i.created_at.isoformat() if i.created_at else now.isoformat(),
                "updated_at": i.updated_at.isoformat() if i.updated_at else now.isoformat(),
            }
            for i in issues
        ],
        "audit_events": [
            {
                "id": str(e.id),
                "document_id": str(e.document_id),
                "issue_id": str(e.issue_id) if e.issue_id else None,
                "actor_id": e.actor_id,
                "actor_role": e.actor_role,
                "action": e.action,
                "notes": e.notes,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "created_at": e.created_at.isoformat() if e.created_at else now.isoformat(),
            }
            for e in audit_events
        ],
    }
