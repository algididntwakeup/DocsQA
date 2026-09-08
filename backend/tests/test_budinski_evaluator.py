"""
Unit tests for Budinski technical writing grading engine and Appendix 12 scorecard.
===================================================================================
Verifies deterministic grading of the 4 standing baseline measures and 41 Appendix 12
checklist items against the Review-ALE baseline report and synthetic variants.
"""

import pytest
from pydantic import ValidationError

from schemas.budinski import (
    BaselineMeasures,
    BudinskiScorecard,
    ScoreItem,
)
from schemas.extraction import CoordinateContract, LayoutAnomaly
from services.budinski_evaluator import BudinskiEvaluator


@pytest.fixture
def evaluator() -> BudinskiEvaluator:
    return BudinskiEvaluator()


@pytest.fixture
def ale_doc_sections() -> dict[str, object]:
    """Canonical document representation for the Review-ALE baseline report."""
    return {
        "doc_id": "ID-N-CG-MM1-DSR-PL-00-3001",
        "rev": "A",
        "date": "2026-08-21",
        "is_ale_baseline": True,
        "executive_summary": (
            "Assessment report for static equipment at Grissik Plant. "
            "Evaluated 175 components across 132 equipment items. "
            "Suitable for operation until 2040 with continued monitoring..."
        ),
        "exec_summary_repeats_results": True,
        "introduction": {
            "background": (
                "§2.1 gives 1998 commissioning, 20-year design life, "
                "2017 DNV GL extension to 2028, change of operator and post tie-in context."
            ),
            "purpose_of_work": "To determine whether the plant can be extended to 2040.",
            "objective_of_work": "§2.2, four numbered objectives.",
            "purpose_of_report": None,  # Never stated
            "objective_of_report": "Inferable from §2.3 Scope of Works.",
            "format_of_report": None,  # Absent
            "work_referenced": None,  # Absent
        },
        "procedure": {
            "has_formulas": True,
            "symbols_defined": True,
            "corrosion_rate_hierarchy": True,
            "assumptions": True,
            "tie_breaking_rules": True,
        },
        "procedure_repeatable": True,
        "results": {
            "table_count": 21,
            "figure_count": 8,
            "components_analyzed": 175,
            "equipment_items": 132,
        },
        "discussion": None,  # No discussion chapter exists
        "conclusions": [
            "1. No asset is classified as Criticality 1 (RUL <= 0 yrs)",
            (
                "3. 1 static component 35-V-101 shell is classified as Criticality 2 "
                "(6 < RUL <= 14 yrs), and 16 static components are classified as Criticality 3 "
                "(6 < RUL <= 14 yrs)"
            ),
            (
                "4. The summary of 2027 directly impacted by post tie-in condition "
                "criticality classification for component level as shown in Table 6-3 is "
                "listed below: a. Criticality 1 = 0 component b. Criticality 2 = 0 "
                "component c. Criticality 3 = 2 components d. Criticality 4 = 25 components."
            ),
            "5. The summary of directly impacted priority classification as shown in Figure 6-2...",
        ],
        "has_definition_contradiction": True,
        "recommendations": [
            (
                "Inspect and verify the 21 static components within classified as Priority "
                "by end-2027."
            ),
            "Perform periodic thickness measurement every 3 - 5 years.",
            "Verify component thickness before determining any further action before end-2027.",
        ],
        "recommendations_has_owner_column": False,
        "references": None,  # No reference section anywhere
        "blockers_count": 2,
        "majors_count": 12,
        "minors_count": 15,
    }


@pytest.fixture
def ale_layout_anomalies() -> list[LayoutAnomaly]:
    """Diagnostic layout anomalies observed on the Review-ALE report."""
    box = CoordinateContract(
        page_index=30, x0=50, y0=50, x1=500, y1=700, page_width=612, page_height=792
    )
    return [
        LayoutAnomaly(
            anomaly_type="UNCONTROLLED_PAGE",
            page_index=30,
            message="21 landscape data pages carry no page number, running header, or doc number.",
            location=box,
        ),
        LayoutAnomaly(
            anomaly_type="FRONT_MATTER_DRIFT",
            page_index=3,
            message="15 of 28 List of Figures and Tables entries carry wrong page numbers.",
            location=box,
        ),
        LayoutAnomaly(
            anomaly_type="UNINTENDED_WHITESPACE",
            page_index=31,
            message="Appendix divider titles sit at foot of otherwise blank pages.",
            location=box,
        ),
    ]


# ── 1. Baseline Measures Tests ──────────────────────────────────────────────


def test_baseline_purpose_vs_objective_fail(evaluator: BudinskiEvaluator) -> None:
    """Baseline 1 fails if report purpose is not explicitly stated distinct from study objective."""
    sections = {
        "introduction": {
            "objective_of_work": "Evaluate asset life extension to 2040.",
            "purpose_of_report": None,
        }
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert not baseline.purpose_distinct_from_objective
    assert "Nothing states what the document itself is for" in baseline.reasons.get(
        "purpose_distinct_from_objective", ""
    )


def test_baseline_purpose_vs_objective_pass(evaluator: BudinskiEvaluator) -> None:
    """Baseline 1 passes when purpose of document and objective of work are distinct."""
    sections = {
        "introduction": {
            "purpose_of_report": (
                "To present the findings of the life-extension assessment to the operations team."
            ),
            "objective_of_work": (
                "To evaluate whether Grissik static equipment can operate reliably to 2040."
            ),
        }
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert baseline.purpose_distinct_from_objective


def test_baseline_procedure_repeatable_pass(evaluator: BudinskiEvaluator) -> None:
    """Baseline 2 passes when procedural calculations and assumptions are complete."""
    sections = {
        "procedure": {
            "has_formulas": True,
            "symbols_defined": True,
            "corrosion_rate_hierarchy": True,
            "assumptions": True,
        }
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert baseline.procedure_repeatable


def test_baseline_procedure_repeatable_fail(evaluator: BudinskiEvaluator) -> None:
    """Baseline 2 fails when procedure merely refers to external document without details."""
    sections = {
        "procedure": "The test rig used was previously described elsewhere in standard reports."
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert not baseline.procedure_repeatable


def test_baseline_conclusions_valid_fail_table_refs(evaluator: BudinskiEvaluator) -> None:
    """Baseline 3 fails if conclusions contain references to Table or Figure numbers."""
    sections = {
        "conclusions": [
            "Component criticality classification as shown in Table 6-3 is confirmed.",
            "Priority distribution follows Figure 6-2.",
        ]
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert not baseline.conclusions_valid
    reason = baseline.reasons.get("conclusions_valid", "")
    assert (
        "Table 6-3" in reason
        or "Figure 6-2" in reason
        or "table and figure references" in reason
    )


def test_baseline_conclusions_valid_fail_raw_counts(evaluator: BudinskiEvaluator) -> None:
    """Baseline 3 fails if conclusions restate full raw result counts rather than inferences."""
    sections = {
        "conclusions": [
            "Criticality 1 = 0 component, Criticality 2 = 1 component, Criticality 4 = 158.",
        ]
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert not baseline.conclusions_valid


def test_baseline_conclusions_valid_pass(evaluator: BudinskiEvaluator) -> None:
    """Baseline 3 passes when conclusions are pure numbered single-sentence inferences."""
    sections = {
        "conclusions": [
            "No static component has exhausted its structural corrosion allowance.",
            "Ninety percent of assessed components are projected to achieve the 2040 target.",
            "One vessel shell requires wall thickness verification prior to life extension.",
        ]
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert baseline.conclusions_valid


def test_baseline_recommendations_actionable_fail_missing_owner(
    evaluator: BudinskiEvaluator,
) -> None:
    """Baseline 4 fails when recommendations have dates but lack an assigned owner."""
    sections = {
        "recommendations": [
            "Perform ultrasonic thickness measurement before end-2027.",
            "Update risk ranking by 2028.",
        ],
        "recommendations_has_owner_column": False,
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert not baseline.recommendations_actionable
    assert "only the owner column is missing" in baseline.reasons.get(
        "recommendations_actionable", ""
    ) or "None names an owner" in baseline.reasons.get("recommendations_actionable", "")


def test_baseline_recommendations_actionable_pass(evaluator: BudinskiEvaluator) -> None:
    """Baseline 4 passes when every recommendation includes an explicit owner and date."""
    sections = {
        "recommendations": [
            {
                "action": "Inspect 21 Priority 2 static components.",
                "owner": "Asset Integrity Lead",
                "date": "2027-12-31",
            },
            {
                "action": "Verify component thickness for 35-V-101.",
                "owner": "Plant Inspection Team",
                "date": "2026-12-31",
            },
        ],
        "recommendations_has_owner_column": True,
    }
    baseline = evaluator.evaluate_four_baselines(sections)
    assert baseline.recommendations_actionable


def test_baseline_ale_sample_score(
    evaluator: BudinskiEvaluator, ale_doc_sections: dict[str, object]
) -> None:
    """On Review-ALE sample, exactly 1 of 4 baselines passes (procedure repeatable)."""
    baseline = evaluator.evaluate_four_baselines(ale_doc_sections)
    assert isinstance(baseline, BaselineMeasures)
    assert not baseline.purpose_distinct_from_objective
    assert baseline.procedure_repeatable
    assert not baseline.conclusions_valid
    assert not baseline.recommendations_actionable
    assert baseline.score == 1
    assert baseline.summary_ratio == "1/4"


# ── 2. 41 Appendix 12 Checklist Items & Scorecard Tests ─────────────────────


def test_ale_baseline_scorecard_group_averages(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Verify group averages match the Review-ALE baseline report exactly."""
    scorecard = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)
    assert isinstance(scorecard, BudinskiScorecard)

    assert scorecard.group_i_average == 4.00
    assert scorecard.group_ii_average == 3.64
    assert scorecard.group_iii_average == 3.45
    assert scorecard.group_iv_average == 3.10
    assert scorecard.overall_average == 3.54


def test_ale_baseline_scorecard_all_41_item_scores(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Verify all 41 items in the 4 groups match the Review-ALE report scores."""
    scorecard = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)

    # Group I: Technical Content (9 items)
    g1 = scorecard.technical_content
    assert g1.message_clear.score == 4
    assert g1.logical_approach.score == 5
    assert g1.adequate_research.score == 3
    assert g1.adequate_comparison.score == 3
    assert g1.conclusions_supported.score == 3
    assert g1.value_stated.score == 5
    assert g1.objective_met.score == 5
    assert g1.original_free_of_plagiarism.score == 4
    assert g1.timely.score == 4

    # Group II: Style (11 items)
    g2 = scorecard.style
    assert g2.objective_tone.score == 5
    assert g2.sections_logical.score == 4
    assert g2.readership_level.score == 5
    assert g2.free_of_jargon.score == 4
    assert g2.english_usage.score == 2
    assert g2.concise.score == 3
    assert g2.interesting.score == 4
    assert g2.free_of_personal_opinion.score == 5
    assert g2.no_over_explain.score == 3
    assert g2.standard_writing_practice.score == 2
    assert g2.layout_and_whitespace.score == 3

    # Group III: Report Mechanics (11 items)
    g3 = scorecard.report_mechanics
    assert g3.sufficient_background.score == 5
    assert g3.purpose_of_work_clear.score == 5
    assert g3.objective_of_work_clear.score == 5
    assert g3.purpose_of_report_clear.score == 1
    assert g3.objective_of_report_clear.score == 3
    assert g3.format_stated.score == 1
    assert g3.work_referenced.score == 1
    assert g3.experimental_steps_outlined.score == 5
    assert g3.adequate_detail_to_repeat.score == 5
    assert g3.free_of_trade_names.score == 4
    assert g3.test_standards_cited.score == 3

    # Group IV: Conclusions & Craft (10 items)
    g4 = scorecard.conclusions_and_craft
    assert g4.results_clearly_stated.score == 5
    assert g4.results_free_of_discussion.score == 4
    assert g4.graphs_and_tables_proper.score == 3
    assert g4.sufficient_results.score == 5
    assert g4.discussion_relates_to_others.score == 2
    assert g4.discussion_length_appropriate.score == 2
    assert g4.conclusions_follow_from_results.score == 3
    assert g4.conclusions_clear.score == 2
    assert g4.references_properly_attributed.score == 1
    assert g4.sentence_paragraph_length.score == 4


def test_ale_baseline_rework_items(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Verify that get_rework_items() returns items with score <= 2."""
    scorecard = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)
    rework = scorecard.get_rework_items()

    rework_keys = [key for _, key, _ in rework]
    assert "english_usage" in rework_keys
    assert "standard_writing_practice" in rework_keys
    assert "purpose_of_report_clear" in rework_keys
    assert "format_stated" in rework_keys
    assert "work_referenced" in rework_keys
    assert "discussion_relates_to_others" in rework_keys
    assert "discussion_length_appropriate" in rework_keys
    assert "conclusions_clear" in rework_keys
    assert "references_properly_attributed" in rework_keys

    # Every item in rework list must have score <= 2
    for _, _, item in rework:
        assert item.score <= 2


def test_ale_review_summary_score_string(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Verify the summary line matches the exact header format from the report."""
    scorecard = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)

    expected = (
        "REVIEWSCORE | doc=ID-N-CG-MM1-DSR-PL-00-3001 | rev=A | date=2026-08-21 | "
        "I=4.00 II=3.64 III=3.45 IV=3.10 | baseline=1/4 | blockers=2 majors=12 minors=15"
    )
    assert scorecard.review_score_string == expected


def test_all_items_count(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Verify total checklist items count is exactly 41."""
    scorecard = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)
    all_items = scorecard.get_all_items()
    assert len(all_items) == 41


def test_ideal_document_evaluation(evaluator: BudinskiEvaluator) -> None:
    """Test a fully compliant document achieving high scores across all groups."""
    ideal_sections = {
        "doc_id": "PERFECT-DOC-001",
        "rev": "0",
        "date": "2026-09-01",
        "executive_summary": "Concise 1-page summary answering the research question.",
        "introduction": {
            "sufficient_background": True,
            "purpose_of_work": "Determine material integrity.",
            "objective_of_work": "Verify 2040 lifespan.",
            "purpose_of_report": "This report documents test results for plant management.",
            "objective_of_report": "To enable management decision on alloy selection.",
            "format_of_report": "Section 1 introduces, Section 2 tests, Section 3 concludes.",
        },
        "purpose_distinct_from_objective": True,
        "format_stated": True,
        "procedure_repeatable": True,
        "references": [
            "ASME Section VIII Div 1, 2023 Edition.",
            "API 580, 4th Edition, 2020.",
        ],
        "standards_edition_cited": True,
        "discussion": "Results agree with Chalmers (1998) and Campbell (2001).",
        "conclusions": [
            "Alloy C2 provides three times greater abrasion resistance than 440C stainless steel.",
            "Corrosion rates in tested acidic environments are negligible.",
        ],
        "conclusions_valid": True,
        "recommendations": [
            {
                "action": "Procure C2 alloy bushings for pump line.",
                "owner": "Maintenance Lead",
                "date": "2026-11-01",
            }
        ],
        "recommendations_has_owner_column": True,
        "recommendations_actionable": True,
    }

    scorecard = evaluator.evaluate_41_checklist_items(ideal_sections, [])
    baselines = scorecard.baseline_measures
    assert baselines is not None
    assert baselines.score == 4
    assert baselines.summary_ratio == "4/4"
    assert scorecard.overall_average >= 4.5
    assert len(scorecard.get_rework_items()) == 0


def test_schema_score_item_bounds() -> None:
    """ScoreItem must validate that score is between 1 and 5 inclusive."""
    with pytest.raises(ValidationError):
        ScoreItem(name="Test", score=0, note="Invalid score below 1")

    with pytest.raises(ValidationError):
        ScoreItem(name="Test", score=6, note="Invalid score above 5")

    valid = ScoreItem(name="Test", score=3, note="Valid score")
    assert valid.score == 3


def test_determinism_repeated_calls(
    evaluator: BudinskiEvaluator,
    ale_doc_sections: dict[str, object],
    ale_layout_anomalies: list[LayoutAnomaly],
) -> None:
    """Repeated calls with identical inputs must produce identical outputs."""
    scorecard1 = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)
    scorecard2 = evaluator.evaluate_41_checklist_items(ale_doc_sections, ale_layout_anomalies)

    assert scorecard1.model_dump() == scorecard2.model_dump()
