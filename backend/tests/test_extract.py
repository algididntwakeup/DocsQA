from pathlib import Path
from uuid import uuid4

import pytest

from schemas.extraction import ExtractionArtifact
from services.extract import extract_document

# Test file location relative to pytest execution directory (assuming execution from backend)
TESTCASE_DIR = Path(__file__).parent.parent.parent / "docs" / "testcase"
STATIC_EQUIP_PDF = TESTCASE_DIR / "05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf"


@pytest.fixture
def sample_pdf_path() -> Path:
    return STATIC_EQUIP_PDF


def test_extract_pdf_valid(sample_pdf_path: Path) -> None:
    if not sample_pdf_path.exists():
        pytest.skip(f"Test file not found: {sample_pdf_path}")

    doc_id = uuid4()
    artifact = extract_document(sample_pdf_path, doc_id, "application/pdf")

    assert isinstance(artifact, ExtractionArtifact)
    assert artifact.document_id == doc_id

    # If the environment lacks PyMuPDF dependencies (like VC++ redistributable),
    # fitz will raise a DLL load failure, and our extractor will catch it and
    # return warnings.
    if artifact.warnings and any("DLL load failed" in warning for warning in artifact.warnings):
        pytest.skip(
            "Environment is missing PyMuPDF DLL dependencies. "
            "Skipping assertion of extracted content."
        )

    assert len(artifact.pages) > 0
    assert len(artifact.spans) > 0

    # Check that coordinates exist and are non-zero (since it's a real PDF)
    assert artifact.spans[0].bbox.page_width > 0
    assert artifact.spans[0].bbox.page_height > 0


def test_extract_invalid_file_type(tmp_path: Path) -> None:
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("Hello World")

    doc_id = uuid4()
    artifact = extract_document(invalid_file, doc_id, "text/plain")

    assert len(artifact.pages) == 0
    assert len(artifact.warnings) == 1
    assert "Unsupported file type" in artifact.warnings[0]
