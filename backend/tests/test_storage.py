"""Unit tests for the local atomic storage adapter."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

from services.storage import LocalStorage, ObjectAlreadyExistsError, ObjectTooLargeError


def test_put_stream_is_atomic_and_returns_integrity_metadata(tmp_path: Path) -> None:
    """A completed write is resolvable and reports its exact hash and size."""

    storage = LocalStorage(tmp_path)
    content = b"document-qc-test"

    stored = storage.put_stream("documents/abc/source.pdf", BytesIO(content))

    assert stored.uri == "local://documents/abc/source.pdf"
    assert stored.size_bytes == len(content)
    assert stored.sha256 == sha256(content).hexdigest()
    assert storage.resolve(stored.uri).read_bytes() == content


@pytest.mark.parametrize(
    "key",
    ["", "../secret", "documents/../../secret", "/absolute/file", r"..\secret"],
)
def test_storage_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    """Application storage cannot be escaped with path traversal syntax."""

    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="Storage key"):
        storage.put_stream(key, BytesIO(b"unsafe"))


def test_oversize_stream_leaves_no_target_or_temporary_file(tmp_path: Path) -> None:
    """A failed size check does not persist partial document bytes."""

    storage = LocalStorage(tmp_path, chunk_size=4)

    with pytest.raises(ObjectTooLargeError):
        storage.put_stream("documents/large/source.pdf", BytesIO(b"123456789"), max_bytes=8)

    assert not (tmp_path / "documents" / "large" / "source.pdf").exists()
    assert list(tmp_path.rglob(".upload-*")) == []


def test_delete_is_idempotent(tmp_path: Path) -> None:
    """Retention workers can safely retry deletion of one exact object."""

    storage = LocalStorage(tmp_path)
    stored = storage.put_stream("documents/delete/source.pdf", BytesIO(b"delete me"))

    storage.delete(stored.uri)
    storage.delete(stored.uri)

    assert not storage.resolve(stored.uri).exists()


def test_existing_object_cannot_be_overwritten(tmp_path: Path) -> None:
    """Reusing a key fails without mutating the first object's bytes."""

    storage = LocalStorage(tmp_path)
    uri = storage.put_stream("documents/immutable/source.pdf", BytesIO(b"original")).uri

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put_stream("documents/immutable/source.pdf", BytesIO(b"replacement"))

    assert storage.resolve(uri).read_bytes() == b"original"
