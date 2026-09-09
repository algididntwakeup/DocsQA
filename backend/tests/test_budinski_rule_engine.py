from schemas.budinski import DocumentMetadata, EvaluationContext, ExtractedSections
from services.budinski_evaluator import generate_scorecard_item


def _context(
    *,
    sections: ExtractedSections | None = None,
    findings: list[dict] | None = None,
    cover_date: str = "2026-09-10",
    creation_date: str = "2026-09-01",
) -> EvaluationContext:
    return EvaluationContext(
        metadata=DocumentMetadata(
            title="Report",
            doc_no="DOC-1",
            rev="A",
            cover_date=cover_date,
            creation_date=creation_date,
            page_count=10,
        ),
        sections=sections or ExtractedSections(),
        findings=findings or [],
    )


def test_group_i_clean_rules() -> None:
    context = _context(
        sections=ExtractedSections(
            headings=["AB (Alpha Beta)"],
            procedures=[
                "Methodology and evaluation criteria: Step 1 calculate x = y; "
                "then evaluate results."
            ],
            conclusions=["Results support the conclusion."],
            introduction=["See references [1] and [2] for previous work."],
        )
    )
    assert generate_scorecard_item("engineering_approach_logical", context).score == 5
    assert generate_scorecard_item("adequate_research_previous_work", context).score == 5
    assert generate_scorecard_item("conclusions_supported_by_work", context).score == 5
    assert generate_scorecard_item("timely", context).score == 5


def test_group_i_weak_rules() -> None:
    context = _context(
        sections=ExtractedSections(
            conclusions=["Results are stated."], introduction=["No citations."]
        ),
        cover_date="2026-12-10",
        creation_date="2026-01-01",
    )
    assert generate_scorecard_item("engineering_approach_logical", context).score == 2
    assert generate_scorecard_item("adequate_research_previous_work", context).score == 2
    assert generate_scorecard_item("timely", context).score == 2


def test_conclusions_supported_counts_math_and_category_findings() -> None:
    context = _context(
        findings=[
            {"type": "TABLE_MATH_MISMATCH"},
            {"type": "CATEGORY_BAND_CONTRADICTION"},
        ]
    )
    item = generate_scorecard_item("conclusions_supported_by_work", context)
    assert item.score == 2
    assert "1 arithmetic discrepancy" in item.note


def test_group_ii_clean_rules() -> None:
    context = _context(
        sections=ExtractedSections(
            headings=["AB (Alpha Beta)"], introduction=["See references [1]."]
        )
    )
    assert generate_scorecard_item("free_of_jargon", context).score == 5
    assert generate_scorecard_item("english_usage", context).score == 4
    assert generate_scorecard_item("standard_writing_practice", context).score == 5
    assert generate_scorecard_item("page_layout_whitespace", context).score == 5


def test_group_ii_findings_lower_scores() -> None:
    findings = [{"type": "SPELLING_ERROR"}] * 11
    findings.extend(
        [
            {"type": "REF_DRIFT"},
            {"type": "UNCONTROLLED_PAGE"},
            {"type": "UNINTENDED_WHITESPACE"},
        ]
    )
    context = _context(findings=findings)
    assert generate_scorecard_item("english_usage", context).score == 2
    assert generate_scorecard_item("standard_writing_practice", context).score == 2
    assert generate_scorecard_item("page_layout_whitespace", context).score == 2


def test_group_iii_and_iv_rules_dispatch() -> None:
    context = _context(
        sections=ExtractedSections(
            introduction=[
                "The purpose of this report is to present results. "
                "The report is organized into four sections."
            ],
            procedures=["Formula x = y. Assumption: constant temperature."],
            conclusions=["The assessment supports continued operation."],
            headings=["References"],
        ),
        findings=[{"type": "CROSS_PAGE_BREAK"}],
    )
    assert generate_scorecard_item("purpose_of_report_clear", context).score == 5
    assert generate_scorecard_item("format_of_report_stated", context).score == 5
    assert generate_scorecard_item("adequate_detail_repeat", context).score == 5
    assert generate_scorecard_item("conclusions_clear", context).score == 5
    assert generate_scorecard_item("references_properly_attributed", context).score == 5
    assert generate_scorecard_item("sentence_paragraph_length", context).score == 2
