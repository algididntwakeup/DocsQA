"""Unit tests for Grammar and Style Analysis Service (M4.1b)."""

from uuid import uuid4

from schemas.extraction import CoordinateContract, ExtractionArtifact, PageMetadata, TextSpan
from services.grammar import GrammarAnalyzer, analyze_grammar


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


def test_detects_repeated_words() -> None:
    """Detects duplicated consecutive words like 'the the' and 'in in'."""
    artifact = _make_artifact("All welds must be inspected in the the shop prior to shipment.")
    analysis = analyze_grammar(artifact)

    repeated = [f for f in analysis.findings if f.rule_id == "RULE_GRAMMAR_REPEATED_WORD"]
    assert len(repeated) >= 1
    assert "the the" in repeated[0].original_text.lower()
    assert repeated[0].suggestion == "the"
    assert repeated[0].location.page_index == 0


def test_detects_homophone_and_contraction_errors() -> None:
    """Detects 'its' vs 'it's' and 'their' vs 'there' errors."""
    artifact = _make_artifact("Ensure that its is verified before measuring it's thickness.")
    analysis = analyze_grammar(artifact)

    homophones = [f for f in analysis.findings if f.rule_id == "RULE_GRAMMAR_HOMOPHONE"]
    assert len(homophones) >= 2

    flagged_texts = [f.original_text.lower() for f in homophones]
    assert any("its is" in t for t in flagged_texts)
    assert any("it's thickness" in t for t in flagged_texts)


def test_detects_subject_verb_disagreement() -> None:
    """Detects plural noun with singular verb disagreement."""
    artifact = _make_artifact("The test specimens was evaluated for toughness.")
    analysis = analyze_grammar(artifact)

    agreements = [f for f in analysis.findings if f.rule_id == "RULE_GRAMMAR_AGREEMENT"]
    assert len(agreements) >= 1
    assert "specimens was" in agreements[0].original_text.lower()
    assert agreements[0].suggestion is not None
    assert "specimens were" in agreements[0].suggestion.lower()


def test_clean_technical_text_has_zero_grammar_errors() -> None:
    """Clean specification text yields zero grammar findings."""
    artifact = _make_artifact(
        "The test specimens were evaluated in accordance with ASTM E23 at ambient temperature."
    )
    analysis = analyze_grammar(artifact)
    assert len(analysis.findings) == 0


def test_circuit_breaker_trips_safely() -> None:
    """If remote LT initialization fails or throws, circuit breaker engages gracefully."""
    analyzer = GrammarAnalyzer(enable_remote_lt=True)
    # Trigger lt check which will safely catch the java 1.8 failure and engage circuit breaker
    artifact = _make_artifact("Review the the weld procedures.")
    analysis = analyzer.analyze(artifact)

    assert analyzer._circuit_breaker_tripped is True
    # Still finds the repeated word using deterministic fallback
    assert any(f.rule_id == "RULE_GRAMMAR_REPEATED_WORD" for f in analysis.findings)
