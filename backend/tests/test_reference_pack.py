"""Unit tests for deterministic Reference Pack System.

Verifies loader, evaluator across all 5 rule kinds, benchmark execution
(precision >= 95%, recall >= 95%, FPR <= 5%), aggregation normalization,
and DOCX report provenance output.
"""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import docx
import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from domain.enums import DocumentStatus, EvaluationStatus, IssueCategory, Severity
from models.document import Document
from models.issue import Issue
from schemas.issues import ReferenceRuleEvidence
from schemas.reference_pack import (
    NumericLimitParameters,
    PackBundleUpload,
    PackManifest,
    PackOrigin,
    PackScope,
    RangeParameters,
    ReferenceFinding,
    ReferenceRule,
    RequiredReferenceParameters,
    RuleDefinition,
    RuleSeverity,
    TerminologyParameters,
    UnitParameters,
)
from services.aggregate import aggregate_document_findings, normalize_reference_findings
from services.reference_pack.benchmark import run_pack_benchmarks
from services.reference_pack.evaluator import ReferenceRuleEvaluator
from services.reference_pack.loader import (
    ReferencePack,
    ReferencePackLoader,
    get_default_registry,
)
from services.report import build_review_report


@pytest.fixture
def asme_pack() -> ReferencePack:
    """Load the default ASME BPVC Section VIII Division 1 reference pack."""
    pack_dir = Path(__file__).resolve().parents[1] / "reference_packs" / "asme_sec_viii_div1"
    return ReferencePackLoader.load_pack(pack_dir)


# ── 1. Reference Pack Loader Tests ────────────────────────────────────


def test_reference_pack_loader(asme_pack: ReferencePack) -> None:
    """ASME reference pack loads cleanly with valid schema and metadata."""
    assert asme_pack.manifest.pack_id == "asme_sec_viii_div1"
    assert asme_pack.manifest.standard_code == "ASME BPVC.VIII.1"
    assert asme_pack.manifest.edition == "2021"
    assert asme_pack.manifest.authority == "American Society of Mechanical Engineers (ASME)"
    assert len(asme_pack.rules) == 11
    assert len(asme_pack.benchmarks) == 22

    # Verify each rule has correct parameter sub-object
    for rule in asme_pack.rules:
        assert rule.standard == "ASME BPVC.VIII.1"
        assert rule.edition == "2021"
        assert rule.clause
        assert rule.standard_page > 0
        if rule.kind == "range":
            assert rule.range_params is not None
        elif rule.kind == "unit":
            assert rule.unit_params is not None
        elif rule.kind == "numeric_limit":
            assert rule.numeric_limit_params is not None
        elif rule.kind == "terminology":
            assert rule.terminology_params is not None
        elif rule.kind == "required_reference":
            assert rule.required_reference_params is not None


def test_reference_pack_loader_missing_files(tmp_path: Path) -> None:
    """Loader raises FileNotFoundError when directory is missing required files."""
    with pytest.raises(FileNotFoundError):
        ReferencePackLoader.load_pack(tmp_path)


def test_reference_pack_registry() -> None:
    """Registry discovers and resolves reference packs by ID and code."""
    registry = get_default_registry()
    registry.reload()

    pack_by_id = registry.get_pack("asme_sec_viii_div1")
    assert pack_by_id is not None
    assert pack_by_id.manifest.pack_id == "asme_sec_viii_div1"
    assert pack_by_id.manifest.status == "CONFIGURED"

    pack_by_code = registry.get_pack("ASME BPVC.VIII.1")
    assert pack_by_code is not None
    assert pack_by_code.manifest.pack_id == "asme_sec_viii_div1"

    packs = registry.list_all_packs()
    assert len(packs) >= 4
    pack_ids = {p.manifest.pack_id for p in packs}
    assert "asme_sec_viii_div1" in pack_ids
    assert "api_rp_580" in pack_ids
    assert "api_510" in pack_ids
    assert "api_579_1" in pack_ids

    configured_packs = registry.list_configured_packs()
    assert any(p.manifest.pack_id == "asme_sec_viii_div1" for p in configured_packs)
    assert not any(p.manifest.pack_id == "api_rp_580" for p in configured_packs)


def test_unconfigured_api_packs() -> None:
    """API packs without source PDFs must be UNCONFIGURED with 0 active rules."""
    registry = get_default_registry()
    registry.reload()

    for pack_id, code in [
        ("api_rp_580", "API RP 580"),
        ("api_510", "API 510"),
        ("api_579_1", "API 579-1/ASME FFS-1"),
    ]:
        pack = registry.get_pack(pack_id)
        assert pack is not None, f"Missing pack {pack_id}"
        assert pack.manifest.standard_code == code
        assert pack.manifest.status == "UNCONFIGURED"
        assert len(pack.rules) == 0
        assert len(pack.benchmarks) == 0
        assert pack.manifest.rules_count == 0
        assert pack.manifest.benchmarks_count == 0
        # Source PDF is not yet in reference-library/
        assert pack.manifest.source_available is False


def test_engineering_judgement_unresolved_status() -> None:
    """Rules requiring engineering judgement emit UNRESOLVED compliance status."""
    rule = ReferenceRule(
        rule_id="RULE-ENG-JUDGEMENT",
        standard="ASME BPVC.VIII.1",
        edition="2021",
        clause="UG-99(f)",
        standard_page=77,
        title="Hydrostatic Test Stress Judgement",
        severity=Severity.HIGH,
        kind="numeric_limit",
        requires_engineering_judgement=True,
        numeric_limit_params=NumericLimitParameters(
            parameter_name="Coincident test stress ratio",
            pattern=r"coincident\s+stress\s+ratio\s*[:=]\s*(\d+(?:\.\d+)?)",
            operator="LE",
            limit_value=1.5,
        ),
        message_template=(
            "Coincident stress ratio requires professional engineering review: {value}"
        ),
        recommendation_template=(
            "Obtain licensed engineer review of coincident test stresses per {clause}."
        ),
    )
    evaluator = ReferenceRuleEvaluator([rule])
    findings = evaluator.evaluate_text("Vessel coincident stress ratio = 1.65", page_number=2)
    assert len(findings) == 1
    assert findings[0].compliance_status == "UNRESOLVED"
    assert findings[0].detected_fact

    # Normalization to issue propagates UNRESOLVED status
    issues = normalize_reference_findings(uuid4(), findings)
    assert len(issues) == 1
    ev = issues[0].evidence
    assert isinstance(ev, ReferenceRuleEvidence)
    assert ev.compliance_status == "UNRESOLVED"


# ── 2. Evaluator Unit Tests Across 5 Rule Kinds ────────────────────────


def test_evaluator_range_rule() -> None:
    """Range rule detects out-of-bounds values and respects bounds."""
    rule = ReferenceRule(
        rule_id="RULE-RANGE-TEST",
        standard="TEST.STD",
        edition="2024",
        clause="1.1",
        standard_page=10,
        title="Test Range",
        severity=Severity.HIGH,
        kind="range",
        range_params=RangeParameters(
            parameter_name="Test Parameter",
            pattern=r"param\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)",
            min_value=10.0,
            max_value=50.0,
            inclusive_min=True,
            inclusive_max=True,
        ),
        message_template="Param {value} is out of bounds [10, 50].",
        recommendation_template="Keep param between {min_val} and {max_val}.",
    )
    evaluator = ReferenceRuleEvaluator([rule])

    # In range
    assert evaluator.evaluate_text("param = 25.0") == []
    assert evaluator.evaluate_text("param = 10.0") == []
    assert evaluator.evaluate_text("param = 50.0") == []

    # Out of range (low)
    findings_low = evaluator.evaluate_text("param = 5.0")
    assert len(findings_low) == 1
    assert findings_low[0].rule_id == "RULE-RANGE-TEST"
    assert findings_low[0].detected_value == "5.0"

    # Out of range (high)
    findings_high = evaluator.evaluate_text("param = 55.0")
    assert len(findings_high) == 1
    assert findings_high[0].detected_value == "55.0"


def test_evaluator_unit_rule() -> None:
    """Unit rule permits approved units and flags forbidden/unauthorized units."""
    rule = ReferenceRule(
        rule_id="RULE-UNIT-TEST",
        standard="TEST.STD",
        edition="2024",
        clause="2.1",
        standard_page=20,
        title="Test Unit",
        severity=Severity.MEDIUM,
        kind="unit",
        unit_params=UnitParameters(
            parameter_name="Test Pressure",
            pattern=r"pressure\s*=\s*[0-9]+(?:\.[0-9]+)?\s*([a-zA-Z0-9/]+)",
            canonical_unit="MPa",
            allowed_units=["MPa", "bar", "psi"],
            forbidden_units=["kg/cm2", "atm"],
        ),
        message_template="Forbidden unit '{unit}'.",
        recommendation_template="Use canonical unit {canonical}.",
    )
    evaluator = ReferenceRuleEvaluator([rule])

    # Valid units
    assert evaluator.evaluate_text("pressure = 2.5 MPa") == []
    assert evaluator.evaluate_text("pressure = 10 bar") == []
    assert evaluator.evaluate_text("pressure = 150 psi") == []

    # Forbidden unit
    findings = evaluator.evaluate_text("pressure = 15 kg/cm2")
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-UNIT-TEST"
    assert findings[0].detected_value == "kg/cm2"


def test_evaluator_numeric_limit_rule() -> None:
    """Numeric limit evaluates GE, LE thresholds with tolerance."""
    rule_ge = ReferenceRule(
        rule_id="RULE-LIMIT-GE",
        standard="TEST.STD",
        edition="2024",
        clause="3.1",
        standard_page=30,
        title="Test GE Limit",
        severity=Severity.CRITICAL,
        kind="numeric_limit",
        numeric_limit_params=NumericLimitParameters(
            parameter_name="Factor",
            pattern=r"factor\s*:\s*([0-9]+(?:\.[0-9]+)?)",
            operator="GE",
            limit_value=1.30,
            tolerance=0.001,
        ),
        message_template="Factor {value} < {limit}.",
        recommendation_template="Set factor >= {limit}.",
    )
    evaluator = ReferenceRuleEvaluator([rule_ge])

    assert evaluator.evaluate_text("factor: 1.30") == []
    assert evaluator.evaluate_text("factor: 1.45") == []

    findings = evaluator.evaluate_text("factor: 1.15")
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-LIMIT-GE"


def test_evaluator_terminology_rule() -> None:
    """Terminology rule flags deprecated terms when context keywords are satisfied."""
    rule = ReferenceRule(
        rule_id="RULE-TERM-TEST",
        standard="TEST.STD",
        edition="2024",
        clause="4.1",
        standard_page=40,
        title="Test Terminology",
        severity=Severity.MEDIUM,
        kind="terminology",
        terminology_params=TerminologyParameters(
            term="Pressure Term",
            preferred_term="MAWP",
            deprecated_terms=["safe working pressure"],
            context_keywords=["vessel", "pressure"],
        ),
        message_template="Deprecated '{deprecated}'. Use '{preferred}'.",
        recommendation_template="Replace with '{preferred}'.",
    )
    evaluator = ReferenceRuleEvaluator([rule])

    # Compliant
    assert evaluator.evaluate_text("The vessel MAWP is 2.0 MPa.") == []

    # Deprecated without context keywords: not triggered
    assert evaluator.evaluate_text("The safe working pressure was discussed.") == []

    # Deprecated with context keywords: triggered
    findings = evaluator.evaluate_text("The vessel safe working pressure is 2.0 MPa.")
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TERM-TEST"
    assert findings[0].detected_value == "safe working pressure"


def test_evaluator_required_reference_rule() -> None:
    """Required reference enforces citation unless exempted."""
    rule = ReferenceRule(
        rule_id="RULE-REQ-REF-TEST",
        standard="TEST.STD",
        edition="2024",
        clause="5.1",
        standard_page=50,
        title="Test Required Ref",
        severity=Severity.HIGH,
        kind="required_reference",
        required_reference_params=RequiredReferenceParameters(
            trigger_keywords=["radiographic examination"],
            required_standard="ASME Section V",
            exemption_keywords=["no NDE required"],
        ),
        message_template="Trigger '{trigger}' without '{required_standard}'.",
        recommendation_template="Cite {required_standard}.",
    )
    evaluator = ReferenceRuleEvaluator([rule])

    # Triggered without citation -> violation
    findings = evaluator.evaluate_text("Perform 100% radiographic examination on all seams.")
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-REQ-REF-TEST"

    # Triggered with citation -> compliant
    assert evaluator.evaluate_text(
        "Perform 100% radiographic examination per ASME Section V on all seams."
    ) == []

    # Triggered but exempted -> compliant
    assert evaluator.evaluate_text(
        "Radiographic examination considered, but no NDE required for category D."
    ) == []


# ── 3. Benchmark Verification Suite (Precision, Recall, FPR) ──────────


def test_asme_benchmark_verification_suite(asme_pack: ReferencePack) -> None:
    """ASME BPVC Section VIII Div 1 benchmark suite passes with >=95% metrics and <=5% FPR."""
    results = run_pack_benchmarks(asme_pack)

    assert results.total_cases == 22
    assert results.total_rules == 11
    assert results.tp_count == 11
    assert results.fp_count == 0
    assert results.fn_count == 0
    assert results.tn_count == 231  # 22 cases * 11 rules - 11 TP

    # Required quality metrics
    assert results.precision >= 0.95, f"Precision {results.precision} below 95%"
    assert results.recall >= 0.95, f"Recall {results.recall} below 95%"
    assert results.false_positive_rate <= 0.05, f"FPR {results.false_positive_rate} above 5%"

    # Exact deterministic performance
    assert results.precision == 1.0
    assert results.recall == 1.0
    assert results.false_positive_rate == 0.0

    # All 22 individual cases must pass
    for case in results.case_results:
        assert case.passed, (
            f"Benchmark case failed: {case.case_id} "
            f"(FP: {case.false_positives}, FN: {case.false_negatives})"
        )


# ── 4. Aggregation & Normalization Tests ───────────────────────────────


def test_normalize_reference_findings() -> None:
    """Reference findings normalize to IssueRead records with ReferenceRuleEvidence."""
    doc_id = uuid4()
    finding = ReferenceFinding(
        rule_id="ASME-VIII-1-UG99-HYDRO-RATIO",
        standard="ASME BPVC.VIII.1",
        edition="2021",
        clause="UG-99(b)",
        standard_page=76,
        rule_kind="numeric_limit",
        severity=Severity.CRITICAL,
        message="Hydrostatic test ratio 1.15 is below mandatory factor 1.30.",
        recommendation="Increase hydrostatic test ratio to at least 1.30.",
        detected_fact="Hydrotest ratio 1.15 is below 1.30.",
        detected_parameter="Hydrostatic test pressure ratio",
        detected_value="1.15",
        page_number=3,
    )

    issues = normalize_reference_findings(doc_id, [finding])
    assert len(issues) == 1
    issue = issues[0]
    assert issue.document_id == doc_id
    assert issue.category == IssueCategory.TRACEABILITY
    assert issue.type == "ASME-VIII-1-UG99-HYDRO-RATIO"
    assert issue.severity == Severity.CRITICAL
    assert isinstance(issue.evidence, ReferenceRuleEvidence)
    assert issue.evidence.kind == "REFERENCE_RULE"
    assert issue.evidence.standard == "ASME BPVC.VIII.1"
    assert issue.evidence.edition == "2021"
    assert issue.evidence.clause == "UG-99(b)"
    assert issue.evidence.standard_page == 76
    assert issue.evidence.detected_parameter == "Hydrostatic test pressure ratio"
    assert issue.evidence.detected_value == "1.15"
    assert issue.evidence.location.page_index == 2  # 1-indexed page 3 -> 0-indexed 2


def test_aggregate_document_findings_with_reference_rules() -> None:
    """Aggregation pipeline integrates reference findings and deduplicates identically."""
    doc_id = uuid4()
    finding = ReferenceFinding(
        rule_id="ASME-VIII-1-UW12-JOINT-EFFICIENCY",
        standard="ASME BPVC.VIII.1",
        edition="2021",
        clause="UW-12",
        standard_page=142,
        rule_kind="range",
        severity=Severity.HIGH,
        message="Joint efficiency 0.35 is below permitted range.",
        recommendation="Assign joint efficiency between 0.45 and 1.00.",
        detected_fact="Joint efficiency 0.35 violates range.",
        detected_parameter="Joint efficiency (E)",
        detected_value="0.35",
        page_number=2,
    )

    # Passing duplicate finding to test deduplication
    result = aggregate_document_findings(
        document_id=doc_id,
        reference_findings=[finding, finding],
    )
    assert result.total_issues == 1
    assert result.issues_by_category["TRACEABILITY"] == 1
    assert result.issues_by_severity["HIGH"] == 1


# ── 6. Pack Manifest & Rule Definition Parsing (pack.yaml / rules.yaml) ──


VALID_PACK_YAML = """
pack_id: tenant_asme_custom
name: Custom Tenant ASME Pack
standard_code: ASME BPVC.VIII.1
edition_year: "2021"
origin: CUSTOM
scope: GLOBAL_TENANT
version: 1.2.0
status: UNCONFIGURED
tenant_id: "42"
description: Tenant-curated ASME pack
"""

VALID_RULES_YAML = """
rules:
  - rule_id: ASME-VIII-1-UG99-HYDRO-RATIO
    standard_code: ASME BPVC.VIII.1
    clause: UG-99(b)
    rule_type: numeric_range
    severity: CRITICAL
    parameters:
      parameter_name: Hydrostatic test pressure ratio
      min_value: 1.30
      max_value: 1.50
    expected_condition: "hydrostatic test ratio >= 1.30"
    recommendation_template: "Increase hydrostatic test ratio to at least 1.30."
  - rule_id: ASME-VIII-1-PRESSURE-UNITS
    standard_code: ASME BPVC.VIII.1
    clause: "2.3"
    rule_type: unit_compatibility
    severity: MAJOR
    parameters:
      canonical_unit: MPa
      forbidden_units: [kg/cm2]
    expected_condition: "all pressures use compatible units"
    recommendation_template: "Express pressure in MPa or bar."
"""


def _parse_pack_yaml(text: str) -> PackManifest:
    return PackManifest.model_validate(yaml.safe_load(text))


def _parse_rules_yaml(text: str) -> list[RuleDefinition]:
    raw = yaml.safe_load(text)
    return [RuleDefinition.model_validate(r) for r in raw["rules"]]


def test_valid_pack_yaml_parsing() -> None:
    manifest = _parse_pack_yaml(VALID_PACK_YAML)
    assert manifest.pack_id == "tenant_asme_custom"
    assert manifest.name == "Custom Tenant ASME Pack"
    assert manifest.standard_code == "ASME BPVC.VIII.1"
    assert manifest.edition_year == "2021"
    assert manifest.origin is PackOrigin.CUSTOM
    assert manifest.scope is PackScope.GLOBAL_TENANT
    assert manifest.version == "1.2.0"
    assert manifest.status == "UNCONFIGURED"
    assert manifest.tenant_id == "42"


def test_valid_rules_yaml_parsing() -> None:
    rules = _parse_rules_yaml(VALID_RULES_YAML)
    assert len(rules) == 2
    assert rules[0].rule_id == "ASME-VIII-1-UG99-HYDRO-RATIO"
    assert rules[0].rule_type.value == "numeric_range"
    assert rules[0].severity is RuleSeverity.CRITICAL
    assert rules[0].parameters["min_value"] == 1.30
    assert rules[1].rule_type.value == "unit_compatibility"
    assert rules[1].severity is RuleSeverity.MAJOR


def test_invalid_pack_yaml_bad_version() -> None:
    bad = VALID_PACK_YAML.replace("version: 1.2.0", "version: 1.2")
    with pytest.raises(ValidationError):
        _parse_pack_yaml(bad)


def test_invalid_pack_yaml_bad_edition_year() -> None:
    bad = VALID_PACK_YAML.replace('edition_year: "2021"', "edition_year: 21st")
    with pytest.raises(ValidationError):
        _parse_pack_yaml(bad)


def test_invalid_pack_yaml_custom_without_tenant() -> None:
    bad = VALID_PACK_YAML.replace('tenant_id: "42"\n', "")
    with pytest.raises(ValidationError, match="tenant_id"):
        _parse_pack_yaml(bad)


def test_invalid_pack_yaml_unknown_field() -> None:
    bad = VALID_PACK_YAML + "surprise_field: true\n"
    with pytest.raises(ValidationError):
        _parse_pack_yaml(bad)


def test_invalid_rules_yaml_unknown_rule_type() -> None:
    bad = VALID_RULES_YAML.replace("rule_type: numeric_range", "rule_type: magic_check")
    with pytest.raises(ValidationError):
        _parse_rules_yaml(bad)


def test_invalid_rules_yaml_missing_expected_condition() -> None:
    bad = VALID_RULES_YAML.replace(
        '    expected_condition: "hydrostatic test ratio >= 1.30"\n', ""
    )
    with pytest.raises(ValidationError):
        _parse_rules_yaml(bad)


def test_invalid_rules_yaml_unknown_severity() -> None:
    bad = VALID_RULES_YAML.replace("severity: CRITICAL", "severity: BLOCKER")
    with pytest.raises(ValidationError):
        _parse_rules_yaml(bad)


def test_pack_bundle_upload_valid() -> None:
    manifest = _parse_pack_yaml(VALID_PACK_YAML)
    rules = _parse_rules_yaml(VALID_RULES_YAML)
    bundle = PackBundleUpload.model_validate(
        {"manifest": manifest.model_dump(mode="json"), "rules": [
            r.model_dump(mode="json") for r in rules
        ]}
    )
    assert bundle.manifest.origin is PackOrigin.CUSTOM
    assert len(bundle.rules) == 2


def test_pack_bundle_upload_rejects_system_origin() -> None:
    system_manifest = PackManifest(
        pack_id="system_pack",
        name="System Pack",
        standard_code="ASME BPVC.VIII.1",
        edition_year="2021",
        version="1.0.0",
    )
    with pytest.raises(ValidationError, match="origin=CUSTOM"):
        PackBundleUpload.model_validate(
            {"manifest": system_manifest.model_dump(mode="json"), "rules": []}
        )


def test_pack_bundle_upload_rejects_duplicate_rule_ids() -> None:
    manifest = _parse_pack_yaml(VALID_PACK_YAML)
    rules = _parse_rules_yaml(VALID_RULES_YAML)
    with pytest.raises(ValidationError, match="Duplicate rule_id"):
        PackBundleUpload.model_validate(
            {"manifest": manifest.model_dump(mode="json"),
             "rules": [r.model_dump(mode="json") for r in rules]
             + [rules[0].model_dump(mode="json")]}
        )


def test_pack_bundle_upload_rejects_standard_code_mismatch() -> None:
    manifest = _parse_pack_yaml(VALID_PACK_YAML)
    rules = _parse_rules_yaml(VALID_RULES_YAML)
    for r in rules:
        r.standard_code = "API 510"
    with pytest.raises(ValidationError, match="standard_code does not match"):
        PackBundleUpload.model_validate(
            {"manifest": manifest.model_dump(mode="json"), "rules": [
                r.model_dump(mode="json") for r in rules
            ]}
        )


# ── BenchmarkCase Expectation schema ──────────────────────────────────


def test_benchmark_expectation_valid() -> None:
    from schemas.reference_pack import BenchmarkExpectation

    exp = BenchmarkExpectation.model_validate(
        {
            "case_id": "BM-001",
            "description": "Hydro ratio below 1.30",
            "input_fact": {"parameter": "hydrostatic_test_ratio", "value": 1.15},
            "expected_status": EvaluationStatus.MISMATCH,
            "expected_rule_id": "ASME-VIII-1-UG99-HYDRO-RATIO",
        }
    )
    assert exp.expected_status is EvaluationStatus.MISMATCH
    assert exp.expected_rule_id == "ASME-VIII-1-UG99-HYDRO-RATIO"


def test_benchmark_expectation_invalid_status() -> None:
    from schemas.reference_pack import BenchmarkExpectation

    with pytest.raises(ValidationError):
        BenchmarkExpectation.model_validate(
            {
                "case_id": "BM-002",
                "description": "Bad status",
                "input_fact": {"value": 1},
                "expected_status": "SOMETHING_ELSE",
            }
        )


# ── 5. DOCX Review Report Integration Tests ───────────────────────────


def test_docx_report_with_reference_rule_findings() -> None:
    """DOCX review report includes evidence source provenance and verified reference standards."""
    doc = uuid4()
    document = Document(
        id=doc,
        original_filename="PRESSURE_VESSEL_SPEC.pdf",
        safe_filename="pressure_vessel_spec",
        status=DocumentStatus.COMPLETED,
    )

    issue_ref = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.TRACEABILITY,
        type="ASME-VIII-1-UG99-HYDRO-RATIO",
        severity=Severity.CRITICAL,
        message=(
            "Hydrostatic test ratio 1.15 is below mandatory ASME VIII-1 UG-99(b) factor of 1.30."
        ),
        page_number=4,
        evidence={
            "kind": "REFERENCE_RULE",
            "extractor_version": "1.0",
            "rule_version": "ASME BPVC.VIII.1:2021",
            "standard": "ASME BPVC.VIII.1",
            "edition": "2021",
            "clause": "UG-99(b)",
            "standard_page": 76,
            "rule_kind": "numeric_limit",
            "detected_parameter": "Hydrostatic test pressure ratio",
            "detected_value": "1.15",
            "location": {
                "page_index": 3,
                "x0": 0.0,
                "y0": 0.0,
                "x1": 612.0,
                "y1": 792.0,
                "page_width": 612.0,
                "page_height": 792.0,
            },
        },
        included_in_report=True,
        reviewer_note="Confirmed discrepancy with design calculations.",
    )

    # Add an UNRESOLVED reference rule issue requiring engineering judgement
    issue_unresolved = Issue(
        id=uuid4(),
        document_id=doc,
        category=IssueCategory.TRACEABILITY,
        type="RULE-ENG-JUDGEMENT",
        severity=Severity.HIGH,
        message="Coincident stress ratio requires professional engineering review: 1.65",
        page_number=2,
        evidence={
            "kind": "REFERENCE_RULE",
            "extractor_version": "1.0",
            "rule_version": "ASME BPVC.VIII.1:2021",
            "standard": "ASME BPVC.VIII.1",
            "edition": "2021",
            "clause": "UG-99(f)",
            "standard_page": 77,
            "rule_kind": "numeric_limit",
            "detected_parameter": "Coincident test stress ratio",
            "detected_value": "1.65",
            "compliance_status": "UNRESOLVED",
            "location": {
                "page_index": 1,
                "x0": 0.0,
                "y0": 0.0,
                "x1": 612.0,
                "y1": 792.0,
                "page_width": 612.0,
                "page_height": 792.0,
            },
        },
        included_in_report=True,
        reviewer_note="Forward to stress engineering team.",
    )

    docx_bytes = build_review_report(document, [issue_ref, issue_unresolved])
    assert len(docx_bytes) > 0

    word_doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)

    # Standard provenance evidence format
    expected_prov = (
        "Evidence source: Standard ASME BPVC.VIII.1 (2021), Clause UG-99(b), Standard Page 76."
    )
    assert expected_prov in full_text
    assert (
        "Discrepancy with design calculations" in full_text
        or "Confirmed discrepancy" in full_text
    )
    assert "Align specification and design parameters with ASME BPVC.VIII.1" in full_text

    # UNRESOLVED compliance status rendering
    assert (
        "Compliance status: UNRESOLVED (Requires Licensed Professional Engineer evaluation)."
        in full_text
    )
    assert "Compliance status: NON-COMPLIANT." in full_text

    # Reference standards verification section contains all 4 standards
    assert "Governed Reference Standards Verification" in full_text
    all_table_text = "\n".join(
        " ".join(cell.text for cell in row.cells)
        for t in word_doc.tables
        for row in t.rows
    )
    assert "ASME BPVC.VIII.1" in all_table_text
    assert "API RP 580" in all_table_text
    assert "API 510" in all_table_text
    assert "API 579-1/ASME FFS-1" in all_table_text
    assert "CONFIGURED" in all_table_text
    assert "UNCONFIGURED" in all_table_text

    # Disclaimer against approval/safety certification
    assert "DocsQA does not approve designs, verify engineering safety" in full_text

    # Scorecard table
    table = word_doc.tables[0]
    data = {row.cells[0].text: row.cells[1].text for row in table.rows[1:]}
    assert data["Included findings"] == "2"
    assert data["Blockers"] == "2"
    assert data["Reference standard violations"] == "2"
