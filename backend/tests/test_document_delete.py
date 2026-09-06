"""Unit tests for DELETE /api/v1/documents/{document_id}."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.dependencies import get_storage
from db.session import get_session
from domain.enums import DocumentStatus
from main import app
from models.document import Document
from services.storage.local import LocalStorage

client = TestClient(app)


def test_delete_document_404_when_missing() -> None:
    """Deleting a non-existent document returns 404."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        response = client.delete(f"/api/v1/documents/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found."
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_delete_document_success(tmp_path: Path) -> None:
    """Deleting an existing document removes storage files, artifacts dir, and DB record."""
    storage = LocalStorage(root=tmp_path)
    doc_id = uuid4()

    # Setup dummy document file
    doc_file = tmp_path / "documents" / f"{doc_id}.pdf"
    doc_file.parent.mkdir(parents=True, exist_ok=True)
    doc_file.write_bytes(b"%PDF-1.7 dummy")

    # Setup dummy artifact dir
    art_dir = tmp_path / "artifacts" / str(doc_id)
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "extraction.json").write_text("{}", encoding="utf-8")

    mock_doc = Document(
        id=doc_id,
        original_filename="spec.pdf",
        safe_filename="spec",
        media_type="application/pdf",
        size_bytes=100,
        sha256="abc",
        status=DocumentStatus.COMPLETED,
        storage_uri=f"local://documents/{doc_id}.pdf",
        canonical_pdf_uri=None,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    async def _override_get_session() -> AsyncMock:
        return mock_session

    def _override_get_storage() -> LocalStorage:
        return storage

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_storage] = _override_get_storage

    try:
        response = client.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 204
        # Assert file was deleted
        assert not doc_file.exists()
        # Assert artifacts directory was deleted
        assert not art_dir.exists()
        # Assert commit was called
        mock_session.commit.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_storage, None)
