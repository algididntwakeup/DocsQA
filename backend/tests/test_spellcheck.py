"""Unit tests for deterministic typo and spelling detection (M4.1a)."""

from uuid import uuid4

from schemas.extraction import CoordinateContract, ExtractionArtifact, PageMetadata, TextSpan
from services.spellcheck import analyze_spelling


def _make_artifact(text: str, page_index: int = 0) -> ExtractionArtifact:
    """Create a minimal ExtractionArtifact with one span for test inputs."""
    bbox = CoordinateContract(
        page_index=page_index,
        x0=50.0,
        y0=100.0,
        x1=500.0,
        y1=120.0,
        page_width=612.0,
        page_height=792.0,
    )
    return ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=page_index, width=612.0, height=792.0)],
        spans=[TextSpan(text=text, bbox=bbox)],
    )


def test_detects_common_typos_with_suggestions() -> None:
    """Detects common typos like 'teh' and 'temprature' with correct suggestions."""
    artifact = _make_artifact(
        "All welds must comply with teh procedure. Check the temprature daily."
    )
    analysis = analyze_spelling(artifact)

    words_flagged = {f.original_text: f.suggestion for f in analysis.findings}
    assert "teh" in words_flagged
    assert words_flagged["teh"] == "the"
    assert "temprature" in words_flagged
    assert words_flagged["temprature"] == "temperature"

    # Verify bounding boxes are within page bounds
    for finding in analysis.findings:
        assert finding.location.page_index == 0
        assert 0.0 <= finding.location.x0 < finding.location.x1 <= 612.0
        assert finding.confidence >= 0.90


def test_whitelists_custom_engineering_dictionary() -> None:
    """Custom dictionary terms are exempt from spellcheck alerts."""
    artifact = _make_artifact("The microstructure exhibits SuperSpecialPhase and CustomAlloyName.")
    custom_dict = {"SuperSpecialPhase", "CustomAlloyName"}

    analysis = analyze_spelling(artifact, custom_dictionary=custom_dict)
    flagged = [f.original_text for f in analysis.findings]
    assert "SuperSpecialPhase" not in flagged
    assert "CustomAlloyName" not in flagged


def test_whitelists_engineering_acronyms_and_chemical_symbols() -> None:
    """Standard acronyms (WPS, PQR, HAZ, ASME) and chemical symbols (Fe, Cr, Ni) are exempt."""
    text = (
        "WPS and PQR documentation for ASME Section IX. "
        "Material contains Fe, Cr, Ni, Mo in the HAZ."
    )
    artifact = _make_artifact(text)

    analysis = analyze_spelling(artifact)
    assert len(analysis.findings) == 0


def test_whitelists_specifications_with_hyphens_and_numbers() -> None:
    """Grades and specs like SA-516, Gr.70, AISI-316L are exempt."""
    text = "Plate fabricated from SA-516 Grade 70 steel according to ASTM A36 specification."
    artifact = _make_artifact(text)

    analysis = analyze_spelling(artifact)
    assert len(analysis.findings) == 0


def test_clean_technical_text_yields_zero_findings() -> None:
    """Clean technical specification text produces zero false positives (< 5% FP goal)."""
    text = (
        "The test specimen was inspected for surface defects. Tensile and yield strength "
        "measurements were recorded in the laboratory test report. Calibration was approved."
    )
    artifact = _make_artifact(text)

    analysis = analyze_spelling(artifact)
    assert len(analysis.findings) == 0


def test_spellcheck_empty_and_capitalization_handling() -> None:
    """Empty spans and title case typos are handled properly."""
    empty_artifact = _make_artifact("")
    assert len(analyze_spelling(empty_artifact).findings) == 0

    title_artifact = _make_artifact("Teh report was signed.")
    analysis = analyze_spelling(title_artifact)
    assert len(analysis.findings) == 1
    assert analysis.findings[0].original_text == "Teh"
    assert analysis.findings[0].suggestion == "The"
