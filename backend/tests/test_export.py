"""Unit and integration tests for Multi-Format Export Service (M5.1)."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import openpyxl
import pypdf
import pytest
from httpx import ASGITransport, AsyncClient

from domain.enums import DocumentStatus, IssueCategory, ReviewStatus, Severity
from main import app
from models.audit import AuditEvent
from models.document import Document
from models.issue import Issue
from services.export import (
    export_annotated_pdf,
    export_csv_issues,
    export_excel_workbook,
    export_json_audit_bundle,
)
from services.storage.local import LocalStorage


def _make_sample_models(
    tmp_path: Path | str,
) -> tuple[Document, list[Issue], list[AuditEvent]]:
    """Create sample Document, Issue, and AuditEvent models for export testing."""
    doc_id = uuid4()
    now = datetime.now(UTC)

    doc = Document(
        id=doc_id,
        original_filename="WELD-SPEC-001.pdf",
        safe_filename="weld_spec_001",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        status=DocumentStatus.COMPLETED,
        review_status=ReviewStatus.IN_REVIEW,
        storage_uri=f"file://documents/{doc_id}.pdf",
        canonical_pdf_uri=f"file://documents/{doc_id}.pdf",
        created_at=now,
        updated_at=now,
    )

    issue_trace = Issue(
        id=uuid4(),
        document_id=doc_id,
        category=IssueCategory.TRACEABILITY,
        type="TABLE_MATH_MISMATCH",
        severity=Severity.CRITICAL,
        confidence=0.98,
        message="Column sum mismatch in Table 2.1: stated 1,250.00 != computed 1,350.00",
        evidence={
            "kind": "TABLE_MATH",
            "stated_value": "1,250.00",
            "computed_value": "1,350.00",
            "delta": "100.00",
            "tolerance": "0.01",
            "total_location": {
                "page_index": 0,
                "x0": 100.0,
                "y0": 200.0,
                "x1": 300.0,
                "y1": 250.0,
                "page_width": 612.0,
                "page_height": 792.0,
            },
        },
        decision=None,
        disposition=None,
        version=1,
        created_at=now,
        updated_at=now,
    )

    issue_ling = Issue(
        id=uuid4(),
        document_id=doc_id,
        category=IssueCategory.LINGUISTIC,
        type="SPELLING_ERROR",
        severity=Severity.LOW,
        confidence=0.92,
        message="Possible spelling error 'temprature'. Suggested replacement: 'temperature'.",
        evidence={
            "kind": "LINGUISTIC",
            "original_text": "temprature",
            "suggestion": "temperature",
            "location": {
                "page_index": 0,
                "x0": 50.0,
                "y0": 80.0,
                "x1": 150.0,
                "y1": 100.0,
                "page_width": 612.0,
                "page_height": 792.0,
            },
        },
        decision=None,
        disposition=None,
        version=1,
        created_at=now,
        updated_at=now,
    )

    audit = AuditEvent(
        id=uuid4(),
        document_id=doc_id,
        issue_id=issue_trace.id,
        actor_id="qa_reviewer@local",
        actor_role="QA_ENGINEER",
        action="ISSUE_DECISION_RECORDED",
        previous_state={"decision": None},
        new_state={"decision": "ACCEPTED"},
        notes="Confirmed table sum error against vendor data sheet.",
        created_at=now,
    )

    return doc, [issue_trace, issue_ling], [audit]


def test_export_annotated_pdf(tmp_path: Path) -> None:
    """Export annotated PDF embeds bounding boxes and callout popups without error."""
    storage = LocalStorage(root=tmp_path)
    doc, issues, _ = _make_sample_models(tmp_path)

    pdf_bytes = export_annotated_pdf(doc, issues, storage)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")

    # Validate PDF structure with pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    page = reader.pages[0]
    # Page must contain annotations
    assert "/Annots" in page


def test_export_excel_workbook(tmp_path: Path) -> None:
    """Export Excel generates valid multi-sheet workbook with Summary, Issues, and Audit tabs."""
    doc, issues, audits = _make_sample_models(tmp_path)

    xlsx_bytes = export_excel_workbook(doc, issues, audits)
    assert len(xlsx_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    sheet_names = wb.sheetnames
    assert "Summary" in sheet_names
    assert "Traceability Issues" in sheet_names
    assert "Linguistic Issues" in sheet_names
    assert "Audit Trail" in sheet_names

    # Check Summary metadata
    ws_summary = wb["Summary"]
    assert "DocsQA" in str(ws_summary["A1"].value)
    assert doc.original_filename in [str(ws_summary[f"B{r}"].value) for r in range(4, 12)]

    # Check Traceability rows
    ws_trace = wb["Traceability Issues"]
    assert ws_trace.max_row >= 2
    assert ws_trace["B2"].value == "TABLE_MATH_MISMATCH"

    # Check Linguistic rows
    ws_ling = wb["Linguistic Issues"]
    assert ws_ling.max_row >= 2
    assert ws_ling["B2"].value == "SPELLING_ERROR"

    # Check Audit rows
    ws_audit = wb["Audit Trail"]
    assert ws_audit.max_row >= 2
    assert ws_audit["C2"].value == "qa_reviewer@local"


def test_export_csv_issues(tmp_path: Path) -> None:
    """Export CSV produces clean comma-separated issue logs."""
    doc, issues, _ = _make_sample_models(tmp_path)

    csv_text = export_csv_issues(doc, issues)
    lines = csv_text.strip().splitlines()
    assert len(lines) == 3  # Header + 2 issues
    assert "document_id,issue_id,category,type,severity" in lines[0]
    assert "TABLE_MATH_MISMATCH" in lines[1]
    assert "SPELLING_ERROR" in lines[2]


def test_export_json_audit_bundle(tmp_path: Path) -> None:
    """Export JSON creates machine-readable audit package."""
    doc, issues, audits = _make_sample_models(tmp_path)

    bundle = export_json_audit_bundle(doc, issues, audits)
    assert bundle["schema_version"] == "1.0"
    assert bundle["document"]["filename"] == "WELD-SPEC-001.pdf"
    assert bundle["summary"]["total_issues"] == 2
    assert bundle["summary"]["critical_count"] == 1
    assert len(bundle["issues"]) == 2
    assert len(bundle["audit_events"]) == 1


@pytest.mark.anyio
async def test_export_endpoints(tmp_path: Path) -> None:
    """HTTP export endpoint handles all four formats correctly."""
    from core.dependencies import get_storage
    from db.session import get_session

    doc, issues, audits = _make_sample_models(tmp_path)
    storage = LocalStorage(root=tmp_path)

    class MockAsyncSession:
        async def execute(self, stmt: Any) -> Any:
            class MockResult:
                def scalar_one_or_none(self) -> Any:
                    # Return document
                    return doc

                def scalars(self) -> Any:
                    class MockScalars:
                        def all(self) -> list[Any]:
                            stmt_str = str(stmt).lower()
                            if "from audit_events" in stmt_str or "auditevent" in stmt_str:
                                return audits
                            return issues

                    return MockScalars()

            return MockResult()

    async def override_get_session() -> Any:
        yield MockAsyncSession()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage] = lambda: storage

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. PDF
            res_pdf = await client.get(f"/api/v1/documents/{doc.id}/export?format=pdf")
            assert res_pdf.status_code == 200
            assert res_pdf.headers["content-type"] == "application/pdf"
            assert "attachment" in res_pdf.headers["content-disposition"]
            assert res_pdf.content.startswith(b"%PDF-")

            # 2. XLSX
            res_xlsx = await client.get(f"/api/v1/documents/{doc.id}/export?format=xlsx")
            assert res_xlsx.status_code == 200
            assert "spreadsheetml" in res_xlsx.headers["content-type"]
            assert "attachment" in res_xlsx.headers["content-disposition"]

            # 3. CSV
            res_csv = await client.get(f"/api/v1/documents/{doc.id}/export?format=csv")
            assert res_csv.status_code == 200
            assert "text/csv" in res_csv.headers["content-type"]
            assert "TABLE_MATH_MISMATCH" in res_csv.text

            # 4. JSON
            res_json = await client.get(f"/api/v1/documents/{doc.id}/export?format=json")
            assert res_json.status_code == 200
            data = res_json.json()
            assert data["schema_version"] == "1.0"
            assert data["document"]["filename"] == doc.original_filename
            assert data["summary"]["total_issues"] == 2
    finally:
        app.dependency_overrides.clear()
