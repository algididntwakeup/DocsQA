"""Contract smoke tests for M0.3."""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from schemas.issues import BoundingBox, IssueRead, TableMathEvidence

client = TestClient(app)


def test_health_is_available() -> None:
    """The only implemented endpoint remains a simple health probe."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_unimplemented_endpoint_uses_problem_details() -> None:
    """Contract-first placeholders fail explicitly with the public error shape."""

    response = client.get("/api/v1/standards-registry")

    assert response.status_code == 501
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "FEATURE_NOT_READY"
    assert response.json()["instance"] == "/api/v1/standards-registry"


def test_validation_error_uses_problem_details() -> None:
    """Invalid path values do not leak FastAPI's framework-specific error shape."""

    response = client.get("/api/v1/documents/not-a-uuid/status")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "path.document_id"


def test_openapi_contains_required_contract_paths() -> None:
    """The generated contract exposes every agreed resource group."""

    paths = app.openapi()["paths"]

    assert {
        "/api/v1/documents",
        "/api/v1/documents/upload",
        "/api/v1/documents/{document_id}",
        "/api/v1/documents/{document_id}/status",
        "/api/v1/documents/{document_id}/issues",
        "/api/v1/documents/{document_id}/export",
        "/api/v1/issues/{issue_id}/decision",
        "/api/v1/issues/{issue_id}/disposition",
        "/api/v1/dictionary/terms",
        "/api/v1/standards-registry",
    }.issubset(paths)


def test_issue_evidence_is_discriminated_and_decimal_safe() -> None:
    """Traceability evidence retains typed locations and exact decimal values."""

    location = BoundingBox(
        page_index=0,
        x0=10,
        y0=20,
        x1=30,
        y1=40,
        page_width=612,
        page_height=792,
    )
    evidence = TableMathEvidence(
        extractor_version="extractor-v1",
        rule_version="table-math-v1",
        computed_value=Decimal("142.5"),
        stated_value=Decimal("143.0"),
        delta=Decimal("0.5"),
        tolerance=Decimal("0.1"),
        operand_locations=[location],
        total_location=location,
    )

    payload = {
        "id": uuid4(),
        "document_id": uuid4(),
        "category": "TRACEABILITY",
        "type": "TABLE_MATH_MISMATCH",
        "severity": "CRITICAL",
        "confidence": 1,
        "message": "The stated total does not match the computed value.",
        "evidence": evidence,
        "version": 1,
        "created_at": "2026-09-04T04:00:00Z",
        "updated_at": "2026-09-04T04:00:00Z",
    }

    issue = IssueRead.model_validate(payload)

    assert issue.evidence.kind == "TABLE_MATH"
    assert issue.evidence.delta == Decimal("0.5")
