"""Unit and contract tests for governed engineering dictionary endpoints (M4.2)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from db.session import get_session
from main import app
from models.dictionary import DictionaryTerm
from schemas.dictionary import DictionaryTermStatus
from services.dictionary import get_approved_dictionary_terms

client = TestClient(app)


def test_create_dictionary_term_success() -> None:
    """Proposing a valid dictionary term creates a PROPOSED entry."""
    mock_session = AsyncMock()

    # Query for existing term returns None (no duplicate)
    mock_existing = MagicMock()
    mock_existing.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_existing

    term_id = uuid4()
    now = datetime.now(UTC)

    async def _mock_refresh(obj: DictionaryTerm) -> None:
        obj.id = term_id
        obj.created_at = now
        obj.updated_at = now

    mock_session.refresh.side_effect = _mock_refresh

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.post(
            "/api/v1/dictionary/terms",
            json={
                "term": "Austenitic",
                "scope": "organization",
                "rationale": "Common metallurgical microstructure term",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["term"] == "Austenitic"
        assert data["scope"] == "organization"
        assert data["status"] == "PROPOSED"
        assert data["id"] == str(term_id)
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_create_dictionary_term_duplicate_conflict() -> None:
    """Proposing a term that already exists in the same scope raises 409 Conflict."""
    mock_session = AsyncMock()

    existing_term = DictionaryTerm(
        id=uuid4(),
        term="Austenitic",
        scope="organization",
        status=DictionaryTermStatus.APPROVED.value,
    )
    mock_existing = MagicMock()
    mock_existing.scalar_one_or_none.return_value = existing_term
    mock_session.execute.return_value = mock_existing

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.post(
            "/api/v1/dictionary/terms",
            json={
                "term": "Austenitic",
                "scope": "organization",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_create_dictionary_term_invalid_scope() -> None:
    """Scope must match 'organization' or 'project:<uuid>' pattern."""
    response = client.post(
        "/api/v1/dictionary/terms",
        json={
            "term": "Ferritic",
            "scope": "invalid-scope-name",
        },
    )
    assert response.status_code == 422


def test_list_dictionary_terms() -> None:
    """Listing returns paginated terms with scope and status."""
    mock_session = AsyncMock()

    term1 = DictionaryTerm(
        id=uuid4(),
        term="HAZ",
        scope="organization",
        status=DictionaryTermStatus.APPROVED.value,
        created_at=datetime.now(UTC),
    )
    term2 = DictionaryTerm(
        id=uuid4(),
        term="WPS",
        scope="organization",
        status=DictionaryTermStatus.PROPOSED.value,
        created_at=datetime.now(UTC),
    )

    count_res = MagicMock()
    count_res.scalar_one.return_value = 2

    terms_res = MagicMock()
    terms_res.scalars.return_value.all.return_value = [term1, term2]

    mock_session.execute.side_effect = [count_res, terms_res]

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.get("/api/v1/dictionary/terms?scope=organization&page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["terms"]) == 2
        assert data["pagination"]["total"] == 2
        assert data["terms"][0]["term"] == "HAZ"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_approve_dictionary_term_success() -> None:
    """Admin approval updates status to APPROVED and records approval metadata."""
    mock_session = AsyncMock()
    term_id = uuid4()

    existing_term = DictionaryTerm(
        id=term_id,
        term="PQR",
        scope="organization",
        status=DictionaryTermStatus.PROPOSED.value,
        created_at=datetime.now(UTC),
    )

    mock_term_res = MagicMock()
    mock_term_res.scalar_one_or_none.return_value = existing_term
    mock_session.execute.return_value = mock_term_res

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.patch(
            f"/api/v1/dictionary/terms/{term_id}/approve",
            json={
                "status": "APPROVED",
                "comment": "Verified per ASME Section IX terminology",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"
        assert existing_term.approved_by == "admin@local"
        assert existing_term.approved_at is not None
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_approve_dictionary_term_not_found() -> None:
    """Attempting to approve a non-existent term returns 404."""
    mock_session = AsyncMock()

    mock_term_res = MagicMock()
    mock_term_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_term_res

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.patch(
            f"/api/v1/dictionary/terms/{uuid4()}/approve",
            json={"status": "APPROVED"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.anyio
async def test_get_approved_dictionary_terms_service() -> None:
    """Service function filters by organization and project scope."""
    mock_session = AsyncMock()
    proj_id = uuid4()

    mock_exec = MagicMock()
    mock_exec.fetchall.return_value = [("Austenitic",), ("martensitic",), ("Inconel",)]
    mock_session.execute.return_value = mock_exec

    terms = await get_approved_dictionary_terms(mock_session, project_id=proj_id)
    assert terms == {"Austenitic", "martensitic", "Inconel"}
