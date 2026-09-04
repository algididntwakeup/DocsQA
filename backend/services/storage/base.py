"""Storage contract shared by local and future S3-compatible adapters."""

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


class ObjectTooLargeError(ValueError):
    """Raised after a stream crosses its configured byte limit."""


class ObjectAlreadyExistsError(FileExistsError):
    """Raised when a write would mutate an immutable stored object."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Immutable result of an atomic storage write."""

    uri: str
    size_bytes: int
    sha256: str


class Storage(Protocol):
    """Minimal storage behavior needed by secure upload and extraction."""

    def put_stream(
        self, key: str, stream: BinaryIO, *, max_bytes: int | None = None
    ) -> StoredObject:
        """Atomically persist a stream under an application-generated key."""

    def resolve(self, uri: str) -> Path:
        """Resolve a storage URI to a local readable path when supported."""

    def delete(self, uri: str) -> None:
        """Delete one exact stored object if it exists."""
