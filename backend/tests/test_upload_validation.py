"""Unit tests for file-type, DOCX structure, and filename validation."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from core.config import Settings
from core.errors import UploadRejectedError
from services.uploads import (
    DOCX_MEDIA_TYPE,
    PDF_MEDIA_TYPE,
    inspect_upload_header,
    validate_stored_document,
)


def make_docx(*, include_document_xml: bool = True, payload: bytes = b"document") -> bytes:
    """Create the smallest structurally valid DOCX-like ZIP fixture."""

    result = BytesIO()
    with ZipFile(result, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        if include_document_xml:
            archive.writestr("word/document.xml", payload)
    return result.getvalue()


def upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    """Build an UploadFile with an in-memory stream."""

    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def test_pdf_magic_bytes_override_filename_extension() -> None:
    """Extension is display-only; PDF bytes determine the persisted format."""

    profile = inspect_upload_header(upload("report.docx", b"%PDF-1.7\nbody", PDF_MEDIA_TYPE))

    assert profile.media_type == PDF_MEDIA_TYPE
    assert profile.extension == "pdf"
    assert profile.safe_filename.endswith(".pdf")


def test_filename_is_normalized_and_path_components_are_discarded() -> None:
    """Upload filenames cannot become storage paths or contain control characters."""

    profile = inspect_upload_header(upload("../unsafe\x00 name.pdf", b"%PDF-1.7", PDF_MEDIA_TYPE))

    assert profile.display_filename == "unsafe name.pdf"
    assert profile.safe_filename == "unsafe_name.pdf"


def test_declared_mime_mismatch_is_rejected() -> None:
    """A browser-declared DOCX cannot carry PDF bytes unnoticed."""

    with pytest.raises(UploadRejectedError, match="Declared media type"):
        inspect_upload_header(upload("report.docx", b"%PDF-1.7", DOCX_MEDIA_TYPE))


def test_docx_requires_office_document_parts(tmp_path: Path) -> None:
    """Generic ZIP archives cannot masquerade as DOCX uploads."""

    path = tmp_path / "missing-document.docx"
    path.write_bytes(make_docx(include_document_xml=False))
    profile = inspect_upload_header(upload("report.docx", path.read_bytes(), DOCX_MEDIA_TYPE))

    with pytest.raises(UploadRejectedError, match="required document parts"):
        validate_stored_document(path, profile, Settings())


def test_docx_compression_ratio_is_bounded(tmp_path: Path) -> None:
    """Highly compressible archive entries are rejected before extraction."""

    path = tmp_path / "ratio.docx"
    path.write_bytes(make_docx(payload=b"0" * 100_000))
    profile = inspect_upload_header(upload("report.docx", path.read_bytes(), DOCX_MEDIA_TYPE))

    with pytest.raises(UploadRejectedError, match="compression ratio"):
        validate_stored_document(path, profile, Settings(MAX_DOCX_COMPRESSION_RATIO=2))
