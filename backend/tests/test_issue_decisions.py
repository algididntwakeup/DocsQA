"""Unit and contract tests for issue decisions, dispositions, and audit events (M3)."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.dependencies import get_storage
from db.session import get_session
from domain.enums import (
    Decision,
    DocumentStatus,
    IssueCategory,
    ReviewStatus,
    Severity,
)
from main import app
from models.audit import AuditEvent
from models.document import Document
from models.issue import Issue
from schemas.issues import BoundingBox, LinguisticEvidence

client = TestClient(app)


def _make_dummy_issue(
    issue_id: UUID,
    doc_id: UUID,
    category: IssueCategory = IssueCategory.LINGUISTIC,
    version: int = 1,
) -> Issue:
    now = datetime.now(UTC)
    return Issue(
        id=issue_id,
        document_id=doc_id,
        category=category,
        type="SPELLING_ERROR" if category == IssueCategory.LINGUISTIC else "TABLE_MATH_MISMATCH",
        severity=Severity.MEDIUM if category == IssueCategory.LINGUISTIC else Severity.CRITICAL,
        confidence=0.95,
        message="Typo in domain word",
        page_number=1,
        evidence=LinguisticEvidence(
            extractor_version="1.0",
            rule_version="spell/1.0.0",
            original_text="austentic",
            suggestion="austenitic",
            location=BoundingBox(
                page_index=0,
                x0=10.0,
                y0=10.0,
                x1=40.0,
                y1=20.0,
                page_width=612.0,
                page_height=792.0,
            ),
        ).model_dump(mode="json"),
        decision=None,
        decision_comment=None,
        decision_by=None,
        disposition=None,
        disposition_justification=None,
        disposition_by=None,
        version=version,
        created_at=now,
        updated_at=now,
    )


def test_decide_issue_success() -> None:
    """QA decision mutates issue state, increments version, and writes AuditEvent."""
    doc_id = uuid4()
    issue_id = uuid4()
    mock_issue = _make_dummy_issue(issue_id, doc_id, version=1)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_issue
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "decision": "ACCEPTED",
            "expected_version": 1,
            "comment": "Verified spelling correction",
            "actor_id": "reviewer@corp.com",
            "actor_role": "QA_ENGINEER",
        }
        response = client.patch(f"/api/v1/issues/{issue_id}/decision", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(issue_id)
        assert data["decision"] == "ACCEPTED"
        assert data["decision_comment"] == "Verified spelling correction"
        assert data["decision_by"] == "reviewer@corp.com"
        assert data["version"] == 2

        # Verify AuditEvent added to session
        added_objs = [call.args[0] for call in mock_session.add.call_args_list]
        audit_events = [obj for obj in added_objs if isinstance(obj, AuditEvent)]
        assert len(audit_events) == 1
        event = audit_events[0]
        assert event.document_id == doc_id
        assert event.issue_id == issue_id
        assert event.action == "ISSUE_DECISION"
        assert event.actor_id == "reviewer@corp.com"
        assert event.new_state["decision"] == "ACCEPTED"
        assert event.new_state["version"] == 2
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_decide_issue_version_mismatch_returns_409() -> None:
    """OCC violation returns 409 Conflict without mutating the record."""
    doc_id = uuid4()
    issue_id = uuid4()
    mock_issue = _make_dummy_issue(issue_id, doc_id, version=2)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_issue
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "decision": "REJECTED",
            "expected_version": 1,  # Stale version
            "actor_id": "reviewer@corp.com",
            "actor_role": "QA_ENGINEER",
        }
        response = client.patch(f"/api/v1/issues/{issue_id}/decision", json=payload)
        assert response.status_code == 409
        assert "Conflict: issue version is 2, but expected 1." in response.json()["detail"]
        mock_session.add.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_decide_issue_not_found_returns_404() -> None:
    """Non-existent issue returns 404."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "decision": "ACCEPTED",
            "expected_version": 1,
        }
        response = client.patch(f"/api/v1/issues/{uuid4()}/decision", json=payload)
        assert response.status_code == 404
        assert response.json()["detail"] == "Issue not found."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_dispose_issue_success() -> None:
    """Lead Reviewer disposition mutates issue, increments version, and writes AuditEvent."""
    doc_id = uuid4()
    issue_id = uuid4()
    mock_issue = _make_dummy_issue(issue_id, doc_id, category=IssueCategory.TRACEABILITY, version=1)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_issue
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "disposition": "JUSTIFIED_EXCEPTION",
            "expected_version": 1,
            "justification": "Client approved variance per NCR-2026-08.",
            "actor_id": "lead.reviewer@corp.com",
            "actor_role": "LEAD_REVIEWER",
        }
        response = client.patch(f"/api/v1/issues/{issue_id}/disposition", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["disposition"] == "JUSTIFIED_EXCEPTION"
        assert data["disposition_justification"] == "Client approved variance per NCR-2026-08."
        assert data["disposition_by"] == "lead.reviewer@corp.com"
        assert data["version"] == 2

        # Check AuditEvent
        added_objs = [call.args[0] for call in mock_session.add.call_args_list]
        audit_events = [obj for obj in added_objs if isinstance(obj, AuditEvent)]
        assert len(audit_events) == 1
        assert audit_events[0].action == "ISSUE_DISPOSITION"
        assert audit_events[0].notes == "Client approved variance per NCR-2026-08."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_bulk_decision_traceability_prohibited() -> None:
    """Traceability bulk accept is strictly rejected with 422 per Scenario A-10."""
    doc_id = uuid4()
    issue1 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.LINGUISTIC)
    issue2 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.TRACEABILITY)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [issue1, issue2]
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "issue_ids": [str(issue1.id), str(issue2.id)],
            "decision": "ACCEPTED",
            "comment": "Bulk approve",
        }
        response = client.post("/api/v1/issues/bulk-decision", json=payload)
        assert response.status_code == 422
        assert "bulk acceptance is strictly prohibited" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_bulk_decision_linguistic_allowed() -> None:
    """Linguistic bulk accept succeeds and applies decisions across items."""
    doc_id = uuid4()
    issue1 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.LINGUISTIC)
    issue2 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.LINGUISTIC)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [issue1, issue2]
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "issue_ids": [str(issue1.id), str(issue2.id)],
            "decision": "ACCEPTED",
            "comment": "Bulk accepted spelling fixes",
        }
        response = client.post("/api/v1/issues/bulk-decision", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        assert data["decision"] == "ACCEPTED"
        assert set(data["updated_issue_ids"]) == {str(issue1.id), str(issue2.id)}
        assert issue1.decision == Decision.ACCEPTED
        assert issue2.decision == Decision.ACCEPTED
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_document_disposition_lifecycle() -> None:
    """Lead Reviewer final sign-off mutates document review_status and logs audit event."""
    doc_id = uuid4()
    now = datetime.now(UTC)
    mock_doc = Document(
        id=doc_id,
        original_filename="specs.pdf",
        safe_filename="specs.pdf",
        media_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,
        storage_uri="local://documents/specs.pdf",
        status=DocumentStatus.COMPLETED,
        review_status=ReviewStatus.IN_REVIEW,
        progress_pct=100,
        created_at=now,
        updated_at=now,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        payload = {
            "disposition": "APPROVED",
            "justification": "All findings resolved and accepted.",
            "actor_id": "chief.engineer@corp.com",
            "actor_role": "LEAD_REVIEWER",
        }
        response = client.post(f"/api/v1/documents/{doc_id}/disposition", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "APPROVED"
        assert mock_doc.review_status == ReviewStatus.APPROVED

        added_objs = [call.args[0] for call in mock_session.add.call_args_list]
        audit_events = [obj for obj in added_objs if isinstance(obj, AuditEvent)]
        assert len(audit_events) == 1
        assert audit_events[0].action == "DOCUMENT_DISPOSITION"
        assert audit_events[0].notes == "All findings resolved and accepted."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_list_document_audit_events() -> None:
    """Audit events endpoint returns all historical events for a document."""
    doc_id = uuid4()
    mock_doc = Document(id=doc_id, original_filename="specs.pdf", status=DocumentStatus.COMPLETED)
    now = datetime.now(UTC)

    event1 = AuditEvent(
        id=uuid4(),
        document_id=doc_id,
        issue_id=uuid4(),
        actor_id="qa@test.com",
        actor_role="QA_ENGINEER",
        action="ISSUE_DECISION",
        previous_state=None,
        new_state={"decision": "ACCEPTED"},
        notes="Checked",
        created_at=now,
        updated_at=now,
    )

    mock_session = AsyncMock()
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    events_result = MagicMock()
    events_result.scalars.return_value.all.return_value = [event1]

    mock_session.execute.side_effect = [doc_result, events_result]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get(f"/api/v1/documents/{doc_id}/audit-events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["action"] == "ISSUE_DECISION"
        assert data["events"][0]["actor_id"] == "qa@test.com"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_get_traceability_summary_endpoint() -> None:
    """Traceability summary returns structured counts for audit dashboard."""
    doc_id = uuid4()
    mock_doc = Document(id=doc_id, original_filename="specs.pdf", status=DocumentStatus.COMPLETED)
    issue1 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.TRACEABILITY)
    issue1.type = "TABLE_MATH_MISMATCH"
    issue1.severity = Severity.CRITICAL

    issue2 = _make_dummy_issue(uuid4(), doc_id, category=IssueCategory.TRACEABILITY)
    issue2.type = "REF_DRIFT"
    issue2.severity = Severity.HIGH
    issue2.decision = Decision.ACCEPTED

    mock_session = AsyncMock()
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    issues_result = MagicMock()
    issues_result.scalars.return_value.all.return_value = [issue1, issue2]

    mock_session.execute.side_effect = [doc_result, issues_result]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get(f"/api/v1/documents/{doc_id}/traceability-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(doc_id)
        assert data["counts_by_type"] == {"TABLE_MATH_MISMATCH": 1, "REF_DRIFT": 1}
        assert data["critical_count"] == 1
        assert data["unresolved_count"] == 1
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_get_document_pdf_stream_success(tmp_path: Path) -> None:
    """Streaming endpoint returns 200 with application/pdf when file exists."""
    doc_id = uuid4()
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 mock content")

    mock_doc = Document(
        id=doc_id,
        original_filename="sample.pdf",
        safe_filename="sample.pdf",
        media_type="application/pdf",
        size_bytes=len(b"%PDF-1.4 mock content"),
        sha256="b" * 64,
        storage_uri="local://documents/sample.pdf",
        status=DocumentStatus.COMPLETED,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    mock_storage = MagicMock()
    mock_storage.scheme = "local://"
    mock_storage._path_for_key.return_value = pdf_file

    async def _override_get_session() -> AsyncMock:
        return mock_session

    def _override_get_storage() -> MagicMock:
        return mock_storage

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_storage] = _override_get_storage
    try:
        response = client.get(f"/api/v1/documents/{doc_id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4 mock content"
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_storage, None)


def test_get_document_pdf_not_found() -> None:
    """Streaming endpoint returns 404 if document does not exist."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get(f"/api/v1/documents/{uuid4()}/pdf")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found."
    finally:
        app.dependency_overrides.pop(get_session, None)
