"""End-to-End Release Lifecycle Integration Test for Report-First Workflow.

Verifies full document lifecycle:
1. Document ingestion and metadata registration.
2. Findings detected and aggregated with included_in_report=True default.
3. Reviewer curation (include/exclude finding and reviewer note).
4. Report preview generation (ReviewReportPreview summary).
5. Deterministic export delivery (Annotated PDF and formal DOCX review report).
6. Security response headers enforcement.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import docx
import pypdf
import pytest
from httpx import ASGITransport, AsyncClient

from core.dependencies import get_storage
from db.session import get_session
from domain.enums import DocumentStatus, IssueCategory, Severity
from main import app
from models.document import Document
from models.issue import Issue
from services.storage.local import LocalStorage


@pytest.mark.anyio
async def test_full_document_lifecycle_e2e(tmp_path: Path) -> None:
    """Validate full end-to-end lifecycle from ingestion through curation and report export."""
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
        included_in_report=True,
        reviewer_note=None,
        created_at=now,
        updated_at=now,
    )

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
                            if "from issues" in stmt_str:
                                if (
                                    "included_in_report is true" in stmt_str
                                    and not issue.included_in_report
                                ):
                                    return []
                                return [issue]
                            return []

                    return MockScalars()

            return MockResult()

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

            # Step 4: Curation API (include/exclude + reviewer note)
            curate_res = await client.patch(
                f"/api/v1/issues/{issue_id}/curation",
                json={
                    "included_in_report": True,
                    "reviewer_note": "Confirmed calculation discrepancy with lead analyst.",
                },
            )
            assert curate_res.status_code == 200
            issue_data = curate_res.json()
            assert issue_data["included_in_report"] is True
            expected_note = "Confirmed calculation discrepancy with lead analyst."
            assert issue_data["reviewer_note"] == expected_note
            assert issue.reviewer_note == expected_note

            # Step 5: Report Preview API
            report_res = await client.get(f"/api/v1/documents/{doc_id}/report")
            assert report_res.status_code == 200
            report_preview = report_res.json()
            assert report_preview["document_id"] == str(doc_id)
            assert report_preview["included_findings"] == 1
            assert report_preview["blockers"] == 1
            assert "CRITICAL" in report_preview["counts_by_severity"]
            assert "Blockers require correction" in report_preview["summary_judgement"]

            # Step 6: Export Delivery
            # 6a: Annotated PDF
            export_pdf = await client.get(f"/api/v1/documents/{doc_id}/export?format=pdf")
            assert export_pdf.status_code == 200
            assert export_pdf.headers["content-type"] == "application/pdf"
            assert "eng_spec_2026_annotated.pdf" in export_pdf.headers["content-disposition"]
            pdf_reader = pypdf.PdfReader(io.BytesIO(export_pdf.content))
            assert len(pdf_reader.pages) >= 1
            assert "/Annots" in pdf_reader.pages[0]

            # 6b: DOCX Review Report
            export_docx = await client.get(f"/api/v1/documents/{doc_id}/export?format=docx")
            assert export_docx.status_code == 200
            assert (
                export_docx.headers["content-type"]
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            assert "eng_spec_2026_review.docx" in export_docx.headers["content-disposition"]
            word_doc = docx.Document(io.BytesIO(export_docx.content))
            doc_text = " ".join(p.text for p in word_doc.paragraphs)
            assert "DOCUMENT REVIEW ENGINEERING" in doc_text
            assert "ENG-SPEC-2026.pdf" in doc_text
            assert "Summary judgement" in doc_text
            assert "Scorecard" in doc_text
            assert "TABLE_MATH_MISMATCH" in doc_text

            # 6c: Unsupported legacy formats rejected
            export_xlsx = await client.get(f"/api/v1/documents/{doc_id}/export?format=xlsx")
            assert export_xlsx.status_code == 422
    finally:
        app.dependency_overrides.clear()
