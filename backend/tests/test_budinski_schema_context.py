from schemas.budinski import (
    BudinskiScorecard,
    DocumentMetadata,
    EvaluationContext,
    ExtractedSections,
    ScorecardEntry,
)


def test_phase_one_context_and_flat_scorecard_properties() -> None:
    metadata = DocumentMetadata(
        title="Technical Report",
        doc_no="DOC-001",
        rev="A",
        cover_date="2026-09-10",
        creation_date="2026-09-01",
        page_count=42,
    )
    sections = ExtractedSections(
        headings=["Introduction", "Conclusions"],
        introduction=["Purpose and scope"],
        procedures=["Procedure details"],
        conclusions=["Conclusion"],
        recommendations=["Recommendation"],
    )
    context = EvaluationContext(metadata=metadata, sections=sections)
    scorecard = BudinskiScorecard(
        items=[
            ScorecardEntry(item_id="I-1", score=4, note="Clear", group="Group I"),
            ScorecardEntry(item_id="II-1", score=3, note="Adequate", group="Group II"),
            ScorecardEntry(item_id="III-1", score=5, note="Strong", group="Group III"),
            ScorecardEntry(item_id="IV-1", score=2, note="Needs work", group="Group IV"),
            ScorecardEntry(item_id="B-1", score=4, note="Pass", group="Baseline"),
        ]
    )

    assert context.metadata.page_count == 42
    assert scorecard.baseline_score == 1.0
    assert scorecard.group_averages == {
        "Group I": 4.0,
        "Group II": 3.0,
        "Group III": 5.0,
        "Group IV": 2.0,
    }
