"""Unit tests for the generic RuleEvaluator engine with regex sandbox guardrails.

Covers all 8 rule types, PASS/FINDING/NOT_APPLICABLE/UNRESOLVED outcomes,
regex sandbox timeout (ReDoS guard), invalid patterns, and the
500-rules-per-run cap.
"""

from __future__ import annotations

import re
import time
from typing import Any

import pytest

from schemas.issues import BoundingBox
from schemas.reference_pack import (
    RuleDefinition,
    RuleEvaluationStatus,
    RuleSeverity,
    RuleType,
)
from services.reference_pack.evaluator import (
    MAX_RULES_PER_RUN,
    REGEX_TIMEOUT_SECONDS,
    RegexTimeoutError,
    RuleEvaluator,
    sandboxed_search,
)


def make_rule(
    rule_type: RuleType,
    parameters: dict[str, Any],
    rule_id: str = "RULE-001",
    expected_condition: str = "expected",
) -> RuleDefinition:
    return RuleDefinition(
        rule_id=rule_id,
        standard_code="TEST.STD",
        clause="1.1",
        rule_type=rule_type,
        severity=RuleSeverity.MAJOR,
        parameters=parameters,
        expected_condition=expected_condition,
        recommendation_template="Fix per clause.",
    )


def make_facts(**overrides: Any) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "text": "",
        "page": 3,
        "edition": "2021",
        "coordinates": [],
    }
    facts.update(overrides)
    return facts


def make_bbox(page_index: int = 2) -> BoundingBox:
    return BoundingBox(
        page_index=page_index, x0=0.0, y0=0.0, x1=100.0, y1=50.0,
        page_width=612.0, page_height=792.0,
    )


@pytest.fixture
def evaluator() -> RuleEvaluator:
    return RuleEvaluator(pack_id="test_pack", rules=[])


# ── 1. required_citation ──────────────────────────────────────────────


def test_required_citation_triggered_without_reference(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_CITATION,
        {
            "trigger_keywords": "radiographic examination",
            "required_standard": "ASME Section V",
        },
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="Perform 100% radiographic examination on seams.")
    )
    assert result.status is RuleEvaluationStatus.FINDING
    assert "ASME Section V" in (result.detected_fact or "")


def test_required_citation_with_reference_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_CITATION,
        {
            "trigger_keywords": "radiographic examination",
            "required_standard": "ASME Section V",
        },
    )
    result = evaluator.evaluate_rule(
        rule,
        make_facts(text="Radiographic examination per ASME Section V is required."),
    )
    assert result.status is RuleEvaluationStatus.PASS


def test_required_citation_exemption_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_CITATION,
        {
            "trigger_keywords": "radiographic examination",
            "required_standard": "ASME Section V",
            "exemption_keywords": ["no NDE required"],
        },
    )
    result = evaluator.evaluate_rule(
        rule,
        make_facts(text="Radiographic examination discussed; no NDE required."),
    )
    assert result.status is RuleEvaluationStatus.PASS
    assert result.confidence < 1.0


def test_required_citation_not_triggered_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_CITATION,
        {
            "trigger_keywords": "radiographic examination",
            "required_standard": "ASME Section V",
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="Visual inspection only."))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


# ── 2. citation_edition_match ─────────────────────────────────────────


def test_citation_edition_match_ok(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.CITATION_EDITION_MATCH,
        {"citation_pattern": r"ASME BPVC\.VIII\.1[ \-]*(\d{4})", "expected_edition": "2021"},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="Design per ASME BPVC.VIII.1 2021.")
    )
    assert result.status is RuleEvaluationStatus.PASS


def test_citation_edition_mismatch_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.CITATION_EDITION_MATCH,
        {"citation_pattern": r"ASME BPVC\.VIII\.1[ \-]*(\d{4})", "expected_edition": "2021"},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="Design per ASME BPVC.VIII.1 2019.")
    )
    assert result.status is RuleEvaluationStatus.FINDING
    assert "2019" in (result.detected_fact or "")


def test_citation_edition_no_citation_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.CITATION_EDITION_MATCH,
        {"citation_pattern": r"ASME BPVC\.VIII\.1[ \-]*(\d{4})", "expected_edition": "2021"},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="No citations here."))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


# ── 3. required_section_field ─────────────────────────────────────────


def test_required_section_field_present(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_SECTION_FIELD,
        {"section_name": "design_data", "field_name": "design_pressure"},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(sections={"design_data": {"design_pressure": "2.5 MPa"}})
    )
    assert result.status is RuleEvaluationStatus.PASS


def test_required_section_field_missing_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.REQUIRED_SECTION_FIELD,
        {"section_name": "design_data", "field_name": "design_temperature"},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(sections={"design_data": {"design_pressure": "2.5 MPa"}})
    )
    assert result.status is RuleEvaluationStatus.FINDING


def test_required_section_field_section_absent_not_applicable(
    evaluator: RuleEvaluator,
) -> None:
    rule = make_rule(
        RuleType.REQUIRED_SECTION_FIELD,
        {"section_name": "design_data", "field_name": "design_pressure"},
    )
    result = evaluator.evaluate_rule(rule, make_facts(sections={}))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


# ── 4. numeric_range ──────────────────────────────────────────────────


def test_numeric_range_in_range_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"ratio\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)", "min_value": 1.3, "max_value": 1.5},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="ratio = 1.40"))
    assert result.status is RuleEvaluationStatus.PASS


def test_numeric_range_out_of_range_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"ratio\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)", "min_value": 1.3, "max_value": 1.5},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="ratio = 1.15"))
    assert result.status is RuleEvaluationStatus.FINDING
    assert "1.15" in (result.detected_fact or "")


def test_numeric_range_boundary_inclusive(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {
            "pattern": r"ratio\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)",
            "min_value": 1.3,
            "inclusive_min": True,
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="ratio = 1.30"))
    assert result.status is RuleEvaluationStatus.PASS


def test_numeric_range_boundary_exclusive_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {
            "pattern": r"ratio\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)",
            "min_value": 1.3,
            "inclusive_min": False,
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="ratio = 1.30"))
    assert result.status is RuleEvaluationStatus.FINDING


def test_numeric_range_no_match_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"ratio\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)", "min_value": 1.3},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="nothing numeric"))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


def test_numeric_range_unparseable_value_unresolved(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"value\s*=\s*([a-z]+)", "min_value": 1.0},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="value = abc"))
    assert result.status is RuleEvaluationStatus.UNRESOLVED


# ── 5. unit_compatibility ─────────────────────────────────────────────


def test_unit_compatibility_allowed_unit_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.UNIT_COMPATIBILITY,
        {
            "pattern": r"pressure\s*=\s*[0-9.]+\s*([a-zA-Z/]+)",
            "allowed_units": ["MPa", "bar"],
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="pressure = 2.5 MPa"))
    assert result.status is RuleEvaluationStatus.PASS


def test_unit_compatibility_forbidden_unit_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.UNIT_COMPATIBILITY,
        {
            "pattern": r"pressure\s*=\s*[0-9.]+\s*([a-zA-Z/0-9]+)",
            "allowed_units": ["MPa"],
            "forbidden_units": ["kg/cm2"],
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="pressure = 25 kg/cm2"))
    assert result.status is RuleEvaluationStatus.FINDING
    assert "kg/cm2" in (result.detected_fact or "")
    assert "forbidden" in (result.detected_fact or "").lower()


def test_unit_compatibility_unknown_unit_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.UNIT_COMPATIBILITY,
        {
            "pattern": r"pressure\s*=\s*[0-9.]+\s*([a-zA-Z/]+)",
            "allowed_units": ["MPa"],
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="pressure = 300 furlongs"))
    assert result.status is RuleEvaluationStatus.FINDING


def test_unit_compatibility_no_match_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.UNIT_COMPATIBILITY,
        {"pattern": r"pressure\s*=\s*[0-9.]+\s*([a-zA-Z/]+)", "allowed_units": ["MPa"]},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="no pressures"))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


# ── 6. terminology_consistency ────────────────────────────────────────


def test_terminology_deprecated_with_context_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TERMINOLOGY_CONSISTENCY,
        {
            "preferred_term": "MAWP",
            "deprecated_terms": ["safe working pressure"],
            "context_keywords": ["vessel"],
        },
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="The vessel safe working pressure is 2.0 MPa.")
    )
    assert result.status is RuleEvaluationStatus.FINDING
    assert "safe working pressure" in (result.detected_fact or "")


def test_terminology_deprecated_without_context_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TERMINOLOGY_CONSISTENCY,
        {
            "preferred_term": "MAWP",
            "deprecated_terms": ["safe working pressure"],
            "context_keywords": ["vessel"],
        },
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="The safe working pressure was discussed generally.")
    )
    assert result.status is RuleEvaluationStatus.PASS


def test_terminology_clean_text_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TERMINOLOGY_CONSISTENCY,
        {
            "preferred_term": "MAWP",
            "deprecated_terms": ["safe working pressure"],
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="The MAWP is 2.0 MPa."))
    assert result.status is RuleEvaluationStatus.PASS


# ── 7. table_prose_reconciliation ─────────────────────────────────────


def test_table_prose_match_passes(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TABLE_PROSE_RECONCILIATION,
        {"tolerance": 0.01},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(table_value=2.50, prose_value=2.5)
    )
    assert result.status is RuleEvaluationStatus.PASS


def test_table_prose_mismatch_is_finding(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TABLE_PROSE_RECONCILIATION,
        {"tolerance": 0.01},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(table_value=2.50, prose_value=2.75)
    )
    assert result.status is RuleEvaluationStatus.FINDING


def test_table_prose_missing_pair_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TABLE_PROSE_RECONCILIATION,
        {"tolerance": 0.01},
    )
    result = evaluator.evaluate_rule(rule, make_facts(table_value=2.5))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


def test_table_prose_non_numeric_unresolved(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.TABLE_PROSE_RECONCILIATION,
        {"tolerance": 0.01},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(table_value="abc", prose_value=2.5)
    )
    assert result.status is RuleEvaluationStatus.UNRESOLVED


# ── 8. applicability_condition ────────────────────────────────────────


def test_applicability_condition_met_is_unresolved(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.APPLICABILITY_CONDITION,
        {"condition_pattern": r"coincident\s+stress\s+ratio\s*>\s*1\.5"},
    )
    result = evaluator.evaluate_rule(
        rule, make_facts(text="Coincident stress ratio > 1.5 applies to this vessel.")
    )
    assert result.status is RuleEvaluationStatus.UNRESOLVED
    assert result.confidence < 1.0


def test_applicability_condition_not_met_not_applicable(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.APPLICABILITY_CONDITION,
        {"condition_pattern": r"coincident\s+stress\s+ratio\s*>\s*1\.5"},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="No special conditions."))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


# ── Result metadata ───────────────────────────────────────────────────


def test_result_metadata_fields(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"ratio\s*=\s*([0-9.]+)", "min_value": 1.0},
        rule_id="META-001",
    )
    result = evaluator.evaluate_rule(
        rule,
        make_facts(
            text="ratio = 1.4",
            page=7,
            coordinates=[make_bbox(page_index=6)],
        ),
    )
    assert result.pack_id == "test_pack"
    assert result.rule_id == "META-001"
    assert result.standard_code == "TEST.STD"
    assert result.clause == "1.1"
    assert result.edition == "2021"
    assert result.source_page == 7
    assert result.expected_condition == "expected"
    assert len(result.evidence_coordinates) == 1
    assert result.evidence_coordinates[0].page_index == 6
    assert result.confidence == 1.0


def test_evaluate_facts_batch(evaluator: RuleEvaluator) -> None:
    rules = [
        make_rule(
            RuleType.NUMERIC_RANGE,
            {"pattern": r"ratio\s*=\s*([0-9.]+)", "min_value": 1.3},
            rule_id="R-A",
        ),
        make_rule(
            RuleType.REQUIRED_CITATION,
            {"trigger_keywords": "x", "required_standard": "Y"},
            rule_id="R-B",
        ),
    ]
    ev = RuleEvaluator(pack_id="p", rules=rules)
    results = ev.evaluate_facts(make_facts(text="ratio = 1.4"))
    assert [r.rule_id for r in results] == ["R-A", "R-B"]


# ── Regex sandbox: ReDoS timeout & invalid patterns ───────────────────


def test_sandboxed_search_matches_normally() -> None:
    compiled = re.compile(r"ratio\s*=\s*([0-9.]+)")
    match = sandboxed_search(compiled, "ratio = 1.4")
    assert match is not None
    assert match.group(1) == "1.4"


def test_sandboxed_search_times_out_on_redos() -> None:
    # Classic catastrophic backtracking: (a+)+$ against a long non-matching run.
    evil = re.compile(r"(a+)+$")
    text = "a" * 40 + "X"
    start = time.monotonic()
    with pytest.raises(RegexTimeoutError, match="Evaluation timeout"):
        sandboxed_search(evil, text, timeout=REGEX_TIMEOUT_SECONDS)
    elapsed = time.monotonic() - start
    # Guard must cut execution well below a full backtracking run.
    assert elapsed < 2.0


def test_redos_pattern_in_rule_yields_unresolved(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {
            "pattern": r"(a+)+$",
            "min_value": 1.0,
        },
    )
    text = "a" * 40 + "X"
    start = time.monotonic()
    result = evaluator.evaluate_rule(rule, make_facts(text=text))
    elapsed = time.monotonic() - start
    assert result.status is RuleEvaluationStatus.UNRESOLVED
    assert "Evaluation timeout" in (result.detected_fact or "")
    # Allow generous slack for process spawn + pipeline overhead on loaded CI.
    assert elapsed < 10.0


def test_terminology_terms_are_escaped_not_treated_as_patterns(
    evaluator: RuleEvaluator,
) -> None:
    # Untrusted pack terms must be matched literally (re.escape), never as regex.
    rule = make_rule(
        RuleType.TERMINOLOGY_CONSISTENCY,
        {
            "preferred_term": "X",
            "deprecated_terms": ["(a+)+b"],
            "context_keywords": [],
        },
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="Use of (a+)+b verbatim."))
    assert result.status is RuleEvaluationStatus.FINDING
    assert "(a+)+b" in (result.detected_fact or "")
    # Must not match a long 'a' run (which the unescaped pattern would).
    assert evaluator.evaluate_rule(
        rule, make_facts(text="a" * 40)
    ).status is RuleEvaluationStatus.PASS


def test_invalid_regex_pattern_is_not_applicable_not_crash(evaluator: RuleEvaluator) -> None:
    rule = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"([unclosed", "min_value": 1.0},
    )
    result = evaluator.evaluate_rule(rule, make_facts(text="ratio = 1.4"))
    assert result.status is RuleEvaluationStatus.NOT_APPLICABLE


def test_regex_timeout_isolated_per_pattern_call() -> None:
    # A timed-out pattern must not poison subsequent evaluations.
    evaluator = RuleEvaluator(pack_id="p", rules=[])
    good = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"ratio\s*=\s*([0-9.]+)", "min_value": 1.3},
        rule_id="GOOD",
    )
    assert evaluator.evaluate_rule(good, make_facts(text="ratio = 1.4")).status is \
        RuleEvaluationStatus.PASS
    evil = make_rule(
        RuleType.NUMERIC_RANGE,
        {"pattern": r"(a+)+$", "min_value": 1.0},
        rule_id="EVIL",
    )
    assert evaluator.evaluate_rule(
        evil, make_facts(text="a" * 40 + "X")
    ).status is RuleEvaluationStatus.UNRESOLVED
    assert evaluator.evaluate_rule(good, make_facts(text="ratio = 1.4")).status is \
        RuleEvaluationStatus.PASS


# ── Rule cap guardrail ────────────────────────────────────────────────


def test_rule_cap_rejects_oversized_rule_set() -> None:
    rules = [
        make_rule(
            RuleType.NUMERIC_RANGE,
            {"pattern": r"x\s*=\s*([0-9.]+)", "min_value": 0.0},
            rule_id=f"R-{i}",
        )
        for i in range(MAX_RULES_PER_RUN + 1)
    ]
    with pytest.raises(ValueError, match="500 rules per run"):
        RuleEvaluator(pack_id="p", rules=rules)


def test_rule_cap_allows_exactly_500_rules() -> None:
    rules = [
        make_rule(
            RuleType.NUMERIC_RANGE,
            {"pattern": r"x\s*=\s*([0-9.]+)", "min_value": 0.0},
            rule_id=f"R-{i}",
        )
        for i in range(MAX_RULES_PER_RUN)
    ]
    evaluator = RuleEvaluator(pack_id="p", rules=rules)
    assert len(evaluator.rules) == MAX_RULES_PER_RUN
