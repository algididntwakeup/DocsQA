"""Secure upload validation and persistence for native-text PDF and DOCX files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from unicodedata import normalize
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.errors import UploadRejectedError
from domain.enums import DocumentStatus
from models.document import Document
from services.storage import LocalStorage, ObjectTooLargeError, StoredObject

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_DECLARED_MEDIA_TYPES = {PDF_MEDIA_TYPE, DOCX_MEDIA_TYPE, "application/octet-stream"}


@dataclass(frozen=True, slots=True)
class UploadProfile:
    """Trusted format and display metadata determined from uploaded bytes."""

    display_filename: str
    safe_filename: str
    media_type: str
    extension: str


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Persisted or deduplicated document returned to the HTTP layer."""

    document: Document
    deduplicated: bool


def _safe_display_filename(filename: str | None) -> tuple[str, str]:
    """Normalize an untrusted upload filename without using it as a path."""

    raw_name = normalize("NFKC", filename or "").replace("\\", "/").split("/")[-1]
    raw_name = "".join(character for character in raw_name if character.isprintable()).strip(" .")
    if not raw_name:
        raise UploadRejectedError("INVALID_FILENAME", "A non-empty filename is required.")

    display_name = raw_name[:255]
    safe_stem = sub(r"[^A-Za-z0-9._-]+", "_", display_name).strip("._")
    if not safe_stem:
        safe_stem = "document"
    return display_name, safe_stem[:255]


def inspect_upload_header(file: UploadFile) -> UploadProfile:
    """Identify PDF or DOCX from magic bytes and reject declared-type conflicts."""

    display_name, safe_name = _safe_display_filename(file.filename)
    declared_type = (file.content_type or "application/octet-stream").lower()
    if declared_type not in ALLOWED_DECLARED_MEDIA_TYPES:
        raise UploadRejectedError("UNSUPPORTED_MEDIA_TYPE", "Only PDF and DOCX files are accepted.")

    stream = file.file
    stream.seek(0)
    signature = stream.read(8)
    stream.seek(0)

    if signature.startswith(b"%PDF-"):
        detected_type, extension = PDF_MEDIA_TYPE, "pdf"
    elif signature.startswith(b"PK\x03\x04"):
        detected_type, extension = DOCX_MEDIA_TYPE, "docx"
    else:
        raise UploadRejectedError("INVALID_FILE_SIGNATURE", "File bytes are not a PDF or DOCX.")

    if declared_type not in {"application/octet-stream", detected_type}:
        raise UploadRejectedError(
            "MEDIA_TYPE_MISMATCH",
            "Declared media type does not match the uploaded file bytes.",
        )
    return UploadProfile(
        display_filename=display_name,
        safe_filename=f"{Path(safe_name).stem[:240]}.{extension}",
        media_type=detected_type,
        extension=extension,
    )


def validate_stored_document(path: Path, profile: UploadProfile, settings: Settings) -> None:
    """Perform bounded structural validation after atomic temporary storage."""

    if profile.media_type == PDF_MEDIA_TYPE:
        if not path.read_bytes()[:5] == b"%PDF-":
            raise UploadRejectedError("INVALID_FILE_SIGNATURE", "Stored PDF signature is invalid.")
        return

    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > settings.MAX_DOCX_ENTRY_COUNT:
                raise UploadRejectedError(
                    "DOCX_TOO_MANY_ENTRIES", "DOCX contains too many archive entries."
                )

            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                normalized_name = member.filename.replace("\\", "/")
                if normalized_name.startswith("/") or ".." in normalized_name.split("/"):
                    raise UploadRejectedError(
                        "MALFORMED_DOCX", "DOCX contains an unsafe archive path."
                    )
                if member.flag_bits & 0x1:
                    raise UploadRejectedError(
                        "ENCRYPTED_DOCX", "Password-protected DOCX files are unsupported."
                    )
                total_uncompressed += member.file_size
                if total_uncompressed > settings.MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise UploadRejectedError(
                        "DOCX_UNCOMPRESSED_TOO_LARGE", "DOCX expands beyond the safe limit."
                    )
                if member.file_size and member.compress_size == 0:
                    raise UploadRejectedError(
                        "MALFORMED_DOCX", "DOCX contains an invalid compressed entry."
                    )
                if (
                    member.compress_size
                    and member.file_size / member.compress_size
                    > settings.MAX_DOCX_COMPRESSION_RATIO
                ):
                    raise UploadRejectedError(
                        "DOCX_COMPRESSION_RATIO_EXCEEDED", "DOCX compression ratio is unsafe."
                    )
                names.add(normalized_name)
    except BadZipFile as exc:
        raise UploadRejectedError("MALFORMED_DOCX", "DOCX archive is malformed.") from exc

    if {"[Content_Types].xml", "word/document.xml"} - names:
        raise UploadRejectedError("MALFORMED_DOCX", "DOCX required document parts are missing.")


class UploadService:
    """Persist validated uploads and collapse simultaneous scans by content hash."""

    def __init__(self, storage: LocalStorage, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    @staticmethod
    def _active_hash_query(sha256: str) -> Select[tuple[Document]]:
        return (
            select(Document)
            .where(
                Document.sha256 == sha256,
                Document.status.in_([DocumentStatus.QUEUED, DocumentStatus.PROCESSING]),
            )
            .order_by(Document.created_at.desc())
            .limit(1)
        )

    async def _delete_stored_object(self, stored: StoredObject) -> None:
        """Clean a rejected temporary upload without masking its validation error."""

        await run_in_threadpool(self.storage.delete, stored.uri)

    async def create_or_reuse(self, file: UploadFile, session: AsyncSession) -> UploadResult:
        """Store one validated document or return its existing active scan."""

        profile = inspect_upload_header(file)
        document_id = uuid4()
        key = f"documents/{document_id}/source.{profile.extension}"
        file.file.seek(0)
        max_bytes = self.settings.MAX_FILE_SIZE_MB * 1024 * 1024
        try:
            stored = await run_in_threadpool(
                self.storage.put_stream,
                key,
                file.file,
                max_bytes=max_bytes,
            )
        except ObjectTooLargeError as exc:
            raise UploadRejectedError(
                "FILE_TOO_LARGE", "File exceeds the configured upload limit."
            ) from exc

        try:
            await run_in_threadpool(
                validate_stored_document,
                self.storage.resolve(stored.uri),
                profile,
                self.settings,
            )
            existing = (
                await session.execute(self._active_hash_query(stored.sha256))
            ).scalar_one_or_none()
            if existing is not None:
                await self._delete_stored_object(stored)
                return UploadResult(document=existing, deduplicated=True)

            document = Document(
                id=document_id,
                original_filename=profile.display_filename,
                safe_filename=profile.safe_filename,
                media_type=profile.media_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_uri=stored.uri,
            )
            session.add(document)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = (
                    await session.execute(self._active_hash_query(stored.sha256))
                ).scalar_one_or_none()
                if existing is None:
                    raise
                await self._delete_stored_object(stored)
                return UploadResult(document=existing, deduplicated=True)
            await session.refresh(document)
            return UploadResult(document=document, deduplicated=False)
        except Exception:
            await self._delete_stored_object(stored)
            raise
