"""Unit tests for Contextual Ambiguity and Passive Voice Service (M4.4)."""

from uuid import uuid4

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact, PageMetadata, TextSpan
from services.ambiguity import analyze_ambiguity


def _make_span(text: str, page_index: int = 0) -> TextSpan:
    return TextSpan(
        text=text,
        bbox=CoordinateContract(
            page_index=page_index,
            x0=50.0,
            y0=100.0,
            x1=500.0,
            y1=120.0,
            page_width=612.0,
            page_height=792.0,
        ),
    )


def test_detects_inconsistent_material_grades() -> None:
    """Flags conflicting material grades (e.g. 316 vs 316L) across document sections."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[
            PageMetadata(page_index=0, width=612.0, height=792.0),
            PageMetadata(page_index=1, width=612.0, height=792.0),
        ],
        spans=[
            _make_span(
                "The vessel shell shall be fabricated from AISI 316 stainless steel.", page_index=0
            ),
            _make_span("All nozzle flanges shall be forged from 316L alloy.", page_index=1),
        ],
    )

    analysis = analyze_ambiguity(artifact)
    grade_findings = [f for f in analysis.findings if f.type == "AMBIGUOUS_SPECIFICATION"]

    assert len(grade_findings) == 2
    assert all(f.severity == Severity.MEDIUM for f in grade_findings)
    assert any("316" in f.message and "316L" in f.message for f in grade_findings)


def test_detects_vague_non_quantitative_directives() -> None:
    """Flags unquantifiable directives like 'sufficiently cooled' and 'as appropriate'."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=0, width=612.0, height=792.0)],
        spans=[
            _make_span(
                "Ensure the weld is sufficiently cooled before performing periodic inspection."
            ),
            _make_span("Apply protective coating as appropriate."),
        ],
    )

    analysis = analyze_ambiguity(artifact)
    vague_findings = [f for f in analysis.findings if f.type == "VAGUE_DIRECTIVE"]

    assert len(vague_findings) >= 3
    phrases = [f.original_text.lower() for f in vague_findings]
    assert any("sufficiently" in p for p in phrases)
    assert any("periodic" in p for p in phrases)
    assert any("as appropriate" in p for p in phrases)


def test_detects_passive_voice_with_active_voice_suggestion() -> None:
    """Flags passive voice with agent and suggests active voice equivalent."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=0, width=612.0, height=792.0)],
        spans=[
            _make_span("The final test shall be inspected by the contractor."),
        ],
    )

    analysis = analyze_ambiguity(artifact)
    passive_findings = [f for f in analysis.findings if f.type == "PASSIVE_VOICE"]

    assert len(passive_findings) == 1
    assert passive_findings[0].suggestion is not None
    assert "The contractor shall inspect" in passive_findings[0].suggestion


def test_unambiguous_quantified_text_yields_zero_findings() -> None:
    """Clear, quantitative directives with consistent grades yield no ambiguity findings."""
    artifact = ExtractionArtifact(
        document_id=uuid4(),
        pages=[PageMetadata(page_index=0, width=612.0, height=792.0)],
        spans=[
            _make_span(
                "Cool the workpiece to below 50 deg C within 30 minutes. "
                "Perform inspection every 24 hours."
            ),
        ],
    )

    analysis = analyze_ambiguity(artifact)
    assert len(analysis.findings) == 0
