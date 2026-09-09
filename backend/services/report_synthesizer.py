"""Deterministic narrative synthesis for executive review reports."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def _value(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


class ReportSynthesizer:
    """Turn normalized findings into concise, repeatable report prose and tables."""

    def generate_summary_judgement(
        self, findings: Iterable[Any], scorecard: Any, metadata: Any
    ) -> str:
        findings_list = list(findings)
        arithmetic = sum(
            "MATH" in str(_value(item, "type")).upper()
            or "ARITH" in str(_value(item, "type")).upper()
            for item in findings_list
        )
        structural = sum(
            any(
                token in (str(_value(item, "type")) + " " + str(_value(item, "message"))).upper()
                for token in ("TOC", "NAVIGATION", "UNCONTROLLED", "REFERENCE")
            )
            for item in findings_list
        )
        total = len(findings_list)
        title = _value(metadata, "document_reviewed", "the reviewed document")
        baseline = _value(scorecard, "baseline_score", "")
        return "\n\n".join(
            [
                f"The review of {title} identified {total} normalized finding(s). "
                f"Arithmetic and count integrity signals: {arithmetic}; the report should preserve "
                "any reconciled totals while correcting confirmed exceptions.",
                f"Structural and navigation signals: {structural}, including table-of-contents, "
                "uncontrolled-page, or reference closure issues where detected. "
                f"The Budinski baseline score is {baseline} where available.",
                "Closure status is determined by the blocking findings and the reviewer’s "
                "inclusion choices; a reissue should not proceed until critical blockers "
                "are resolved.",
            ]
        )

    def generate_bottom_line(self, blockers: Iterable[Any]) -> str:
        first = next(iter(blockers), None)
        if first is None:
            return (
                "No blocking finding was identified; close the remaining findings in the "
                "next controlled review."
            )
        title = _value(first, "title", _value(first, "finding", "the critical blocker"))
        fix = _value(first, "what_would_fix_it", "resolve the finding and verify the evidence")
        return f"Resolve {title} before reissue: {fix}."

    def synthesize_baseline_measures(
        self, doc_sections: Any, findings: Iterable[Any]
    ) -> list[dict[str, str]]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        checks = [
            (
                "Purpose distinct from objective",
                bool(sections.get("purpose_of_report_stated")),
                "State the report purpose separately from the work objective.",
            ),
            (
                "Procedure repeatable",
                bool(sections.get("procedure_repeatable", True)),
                "Provide enough method detail for another competent party to repeat the work.",
            ),
            (
                "Conclusions are conclusions",
                bool(sections.get("conclusions_valid", True)),
                "Separate conclusions from results and discussion.",
            ),
            (
                "Recommendations actionable",
                bool(sections.get("recommendations_actionable", True)),
                "Name an owner and due date for each recommendation.",
            ),
        ]
        return [
            {"measure": name, "result": "PASS" if passed else "FAIL", "reason": reason}
            for name, passed, reason in checks
        ]

    def synthesize_blockers(self, blockers: Iterable[Any]) -> list[dict[str, str]]:
        fields = (
            "where_location",
            "what_it_says",
            "what_body_has",
            "why_it_matters",
            "what_would_fix_it",
        )
        return [
            {label.replace("_", " ").title(): str(_value(item, label)) for label in fields}
            for item in blockers
        ]

    def synthesize_major_findings(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        selected = []
        for item in findings:
            text = (str(_value(item, "type")) + " " + str(_value(item, "message"))).upper()
            if any(
                token in text
                for token in (
                    "TOC",
                    "NAVIGATION",
                    "UNCONTROLLED",
                    "BIBLIO",
                    "DUPLICATE",
                    "DEFINITION",
                )
            ):
                selected.append(item)
        return [
            {
                "#": str(index),
                "FINDING": str(_value(item, "message", _value(item, "finding"))),
                "WHAT WOULD FIX IT": str(
                    _value(item, "suggestion", "Correct, verify, and reissue the affected section.")
                ),
            }
            for index, item in enumerate(selected, 1)
        ]

    def synthesize_language_mechanics(self, minor_findings: Iterable[Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in minor_findings:
            evidence = _value(item, "evidence", {}) or {}
            page = str(_value(evidence, "page", _value(item, "page", "—")))
            original = str(_value(evidence, "original_text", _value(item, "message", "")))
            suggested = str(
                _value(evidence, "suggestion", _value(item, "suggested", "Review wording."))
            )
            key = (page, original, suggested)
            if key not in seen:
                seen.add(key)
                rows.append({"PAGE": page, "AS WRITTEN": original, "SUGGESTED": suggested})
        return rows

    def generate_demonstration_rewrite(
        self, sections: Any, findings: Iterable[Any]
    ) -> dict[str, Any]:
        raw = (
            sections.get("conclusions", "")
            if isinstance(sections, dict)
            else getattr(sections, "conclusions", "")
        )
        text = " ".join(raw) if isinstance(raw, list) else str(raw)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        return {
            "section_title": "Conclusions",
            "as_written": text or "No conclusion text was extracted.",
            "demonstration": [sentence.rstrip(".") + "." for sentence in sentences[:8]],
        }

    def synthesize_praise(self, doc_sections: Any, findings: Iterable[Any]) -> list[str]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        praise = []
        if sections.get("arithmetic_reconciles"):
            praise.append("Arithmetic and count totals reconcile across the checked tables.")
        if sections.get("priority_rules_explicit"):
            praise.append("Priority rules are explicit and can be audited independently.")
        if sections.get("assumptions"):
            praise.append("Assumptions are recorded explicitly for review and reuse.")
        return praise or [
            "The report provides a traceable basis for the findings and requested corrections."
        ]
