"""Atomic local-filesystem storage adapter for development and tests."""

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from services.storage.base import ObjectAlreadyExistsError, ObjectTooLargeError, StoredObject


class LocalStorage:
    """Persist objects below one configured root without trusting filenames."""

    scheme = "local://"

    def __init__(self, root: Path, *, chunk_size: int = 1024 * 1024) -> None:
        self.root = root.resolve()
        self.chunk_size = chunk_size
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_key(key: str) -> PurePosixPath:
        candidate = PurePosixPath(key)
        if (
            not key
            or candidate.is_absolute()
            or ".." in candidate.parts
            or any(part in {"", "."} for part in candidate.parts)
            or "\\" in key
        ):
            raise ValueError("Storage key must be a safe relative POSIX path.")
        return candidate

    def _path_for_key(self, key: str) -> Path:
        candidate = self._validate_key(key)
        path = self.root.joinpath(*candidate.parts).resolve()
        if self.root not in path.parents:
            raise ValueError("Storage key resolves outside the configured root.")
        return path

    def put_stream(
        self, key: str, stream: BinaryIO, *, max_bytes: int | None = None
    ) -> StoredObject:
        """Write in chunks, hash bytes, enforce the limit, then replace atomically."""

        target = self._path_for_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size_bytes = 0
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=".upload-", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := stream.read(self.chunk_size):
                    size_bytes += len(chunk)
                    if max_bytes is not None and size_bytes > max_bytes:
                        raise ObjectTooLargeError(
                            f"Object exceeded the {max_bytes}-byte storage limit."
                        )
                    digest.update(chunk)
                    temporary.write(chunk)
                temporary.flush()
                os.fsync(temporary.fileno())

            try:
                os.link(temporary_path, target)
            except FileExistsError as exc:
                raise ObjectAlreadyExistsError(f"Storage object already exists: {key}") from exc
            temporary_path.unlink()
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        return StoredObject(
            uri=f"{self.scheme}{key}",
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
        )

    def resolve(self, uri: str) -> Path:
        """Resolve an exact local URI and reject other storage schemes."""

        if not uri.startswith(self.scheme):
            raise ValueError("Unsupported storage URI.")
        return self._path_for_key(uri.removeprefix(self.scheme))

    def delete(self, uri: str) -> None:
        """Delete one exact object; missing objects are already deleted."""

        self.resolve(uri).unlink(missing_ok=True)
