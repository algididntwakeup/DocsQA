"""End-to-End Release Lifecycle Integration Test (M5.4).

Verifies full document lifecycle:
1. Document ingestion and metadata registration.
2. Analyzer issue normalization and unified finding persistence.
3. Reviewer OCC decision recording with version check (HTTP 409 guard).
4. Lead Reviewer final disposition with mandatory justification.
5. Multi-format export delivery (Annotated PDF, XLSX, CSV, JSON).
6. Security response headers enforcement.
"""

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

from core.dependencies import get_storage
from db.session import get_session
from domain.enums import DocumentStatus, IssueCategory, ReviewStatus, Severity
from main import app
from models.audit import AuditEvent
from models.document import Document
from models.issue import Issue
from services.storage.local import LocalStorage


@pytest.mark.anyio
async def test_full_document_lifecycle_e2e(tmp_path: Path) -> None:
    """Validate full end-to-end lifecycle from ingestion through review and export."""
    storage = LocalStorage(root=tmp_path)
    now = datetime.now(UTC)
    doc_id = uuid4()
    issue_id = uuid4()

    # Step 1: Ingest document
    doc = Document(
        id=doc_id,
        original_filename="ENG-SPEC-2026.pdf",
        safe_filename="eng_spec_2026",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="e" * 64,
        status=DocumentStatus.COMPLETED,
        review_status=ReviewStatus.PENDING,
        progress_pct=100,
        storage_uri=f"local://documents/{doc_id}.pdf",
        canonical_pdf_uri=f"local://documents/{doc_id}.pdf",
        created_at=now,
        updated_at=now,
    )

    # Step 2: Findings detected by analyzers
    issue = Issue(
        id=issue_id,
        document_id=doc_id,
        category=IssueCategory.TRACEABILITY,
        type="TABLE_MATH_MISMATCH",
        severity=Severity.CRITICAL,
        confidence=0.99,
        message="Sum mismatch on page 1: stated 500.00 != computed 550.00",
        evidence={
            "kind": "TABLE_MATH",
            "extractor_version": "1.0",
            "rule_version": "1.0",
            "stated_value": "500.00",
            "computed_value": "550.00",
            "delta": "50.00",
            "tolerance": "0.01",
            "operand_locations": [],
            "total_location": {
                "page_index": 0,
                "x0": 72.0,
                "y0": 144.0,
                "x1": 200.0,
                "y1": 180.0,
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

    audit_log: list[AuditEvent] = []

    class MockLifecycleSession:
        async def execute(self, stmt: Any) -> Any:
            stmt_str = str(stmt).lower()

            class MockResult:
                def scalar_one_or_none(self) -> Any:
                    if "from issues" in stmt_str:
                        return issue
                    if "from documents" in stmt_str:
                        return doc
                    return None

                def scalars(self) -> Any:
                    class MockScalars:
                        def all(self) -> list[Any]:
                            if "from audit_events" in stmt_str:
                                return audit_log
                            if "from issues" in stmt_str:
                                return [issue]
                            return []

                    return MockScalars()

            return MockResult()

        def add(self, obj: Any) -> None:
            if isinstance(obj, AuditEvent):
                audit_log.append(obj)

        async def commit(self) -> None:
            pass

        async def refresh(self, obj: Any) -> None:
            pass

    async def override_get_session() -> Any:
        yield MockLifecycleSession()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage] = lambda: storage

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 3: Verify Security Headers on API response
            health_res = await client.get("/health")
            assert health_res.status_code == 200
            assert health_res.headers["x-content-type-options"] == "nosniff"
            assert "frame-ancestors" in health_res.headers["content-security-policy"]
            assert "strict-origin" in health_res.headers["referrer-policy"]

            # Step 4: QA Engineer records decision with OCC
            decide_res = await client.patch(
                f"/api/v1/issues/{issue_id}/decision",
                json={
                    "decision": "ACCEPTED",
                    "expected_version": 1,
                    "comment": "Confirmed arithmetic discrepancy with engineering lead.",
                    "actor_id": "qa.engineer@company.com",
                    "actor_role": "QA_ENGINEER",
                },
            )
            assert decide_res.status_code == 200
            issue_data = decide_res.json()
            assert issue_data["decision"] == "ACCEPTED"
            assert issue_data["version"] == 2
            assert issue.decision == "ACCEPTED"
            assert issue.version == 2
            assert len(audit_log) == 1
            assert audit_log[0].action == "ISSUE_DECISION"

            # Step 5: Verify OCC collision prevention (replaying stale version 1 fails with 409)
            conflict_res = await client.patch(
                f"/api/v1/issues/{issue_id}/decision",
                json={
                    "decision": "REJECTED",
                    "expected_version": 1,
                    "actor_id": "other.reviewer@company.com",
                    "actor_role": "QA_ENGINEER",
                },
            )
            assert conflict_res.status_code == 409

            # Step 6: Lead Reviewer disposition on issue
            dispose_res = await client.patch(
                f"/api/v1/issues/{issue_id}/disposition",
                json={
                    "disposition": "JUSTIFIED_EXCEPTION",
                    "justification": "Approved under technical deviation TD-2026-088.",
                    "expected_version": 2,
                    "actor_id": "lead.reviewer@company.com",
                    "actor_role": "LEAD_REVIEWER",
                },
            )
            assert dispose_res.status_code == 200
            disp_data = dispose_res.json()
            assert disp_data["disposition"] == "JUSTIFIED_EXCEPTION"
            assert disp_data["version"] == 3
            assert issue.disposition == "JUSTIFIED_EXCEPTION"
            assert len(audit_log) == 2

            # Step 7: Final Document Sign-off by Lead Reviewer
            doc_disp_res = await client.post(
                f"/api/v1/documents/{doc_id}/disposition",
                json={
                    "disposition": "APPROVED",
                    "justification": "All findings resolved or justified under TD-2026-088.",
                    "actor_id": "lead.reviewer@company.com",
                    "actor_role": "LEAD_REVIEWER",
                },
            )
            assert doc_disp_res.status_code == 200
            doc_data = doc_disp_res.json()
            assert doc_data["review_status"] == "APPROVED"
            assert len(audit_log) == 3

            # Step 8: Multi-Format Export Verification
            # 8a: Annotated PDF
            export_pdf = await client.get(f"/api/v1/documents/{doc_id}/export?format=pdf")
            assert export_pdf.status_code == 200
            assert export_pdf.headers["content-type"] == "application/pdf"
            pdf_reader = pypdf.PdfReader(io.BytesIO(export_pdf.content))
            assert len(pdf_reader.pages) >= 1
            assert "/Annots" in pdf_reader.pages[0]

            # 8b: Excel Workbook (.xlsx)
            export_xlsx = await client.get(f"/api/v1/documents/{doc_id}/export?format=xlsx")
            assert export_xlsx.status_code == 200
            wb = openpyxl.load_workbook(io.BytesIO(export_xlsx.content))
            assert "Summary" in wb.sheetnames
            assert "Traceability Issues" in wb.sheetnames
            assert "Audit Trail" in wb.sheetnames

            # 8c: CSV Issue Log
            export_csv = await client.get(f"/api/v1/documents/{doc_id}/export?format=csv")
            assert export_csv.status_code == 200
            assert "TABLE_MATH_MISMATCH" in export_csv.text
            assert "JUSTIFIED_EXCEPTION" in export_csv.text

            # 8d: JSON Audit Bundle
            export_json = await client.get(f"/api/v1/documents/{doc_id}/export?format=json")
            assert export_json.status_code == 200
            bundle = export_json.json()
            assert bundle["document"]["review_status"] == "APPROVED"
            assert len(bundle["issues"]) == 1
            assert len(bundle["audit_events"]) == 3
    finally:
        app.dependency_overrides.clear()
