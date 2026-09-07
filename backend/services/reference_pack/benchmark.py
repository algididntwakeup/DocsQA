"""Benchmark execution and metric calculation for reference standards packs."""

from __future__ import annotations

from schemas.reference_pack import (
    BenchmarkCaseResult,
    BenchmarkEvaluationResult,
)
from services.reference_pack.evaluator import ReferenceRuleEvaluator
from services.reference_pack.loader import ReferencePack


def run_pack_benchmarks(pack: ReferencePack) -> BenchmarkEvaluationResult:
    """Run all benchmark cases against pack rules and compute precision/recall/FPR metrics."""
    evaluator = ReferenceRuleEvaluator(pack.rules)
    all_rule_ids = {r.rule_id for r in pack.rules}

    total_tp = 0
    total_fp = 0
    total_tn = 0
    total_fn = 0
    case_results: list[BenchmarkCaseResult] = []

    for case in pack.benchmarks:
        findings = evaluator.evaluate_text(case.document_text)
        actual_triggers = sorted(list({f.rule_id for f in findings}))
        expected_triggers = sorted(list(set(case.expected_triggers)))

        actual_set = set(actual_triggers)
        expected_set = set(expected_triggers)

        tp_set = actual_set & expected_set
        fp_set = actual_set - expected_set
        fn_set = expected_set - actual_set
        tn_set = (all_rule_ids - actual_set) - expected_set

        total_tp += len(tp_set)
        total_fp += len(fp_set)
        total_fn += len(fn_set)
        total_tn += len(tn_set)

        passed = actual_set == expected_set

        case_results.append(
            BenchmarkCaseResult(
                case_id=case.case_id,
                passed=passed,
                expected_triggers=expected_triggers,
                actual_triggers=actual_triggers,
                true_positives=sorted(list(tp_set)),
                false_positives=sorted(list(fp_set)),
                false_negatives=sorted(list(fn_set)),
            )
        )

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    fpr = total_fp / (total_fp + total_tn) if (total_fp + total_tn) > 0 else 0.0

    return BenchmarkEvaluationResult(
        standard_code=pack.manifest.standard_code,
        edition=pack.manifest.edition,
        total_cases=len(pack.benchmarks),
        total_rules=len(pack.rules),
        tp_count=total_tp,
        fp_count=total_fp,
        tn_count=total_tn,
        fn_count=total_fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        false_positive_rate=round(fpr, 4),
        case_results=case_results,
    )
