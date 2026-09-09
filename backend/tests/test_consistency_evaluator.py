from services.consistency_evaluator import (
    DocumentSection,
    NumericInterval,
    detect_category_band_contradictions,
    harvest_definition_tables,
    parse_numeric_interval,
)


def _table(*rows: list[str]) -> dict[str, object]:
    return {
        "cells": [
            {"row_index": row_index, "col_index": col_index, "text": value}
            for row_index, row in enumerate(rows)
            for col_index, value in enumerate(row)
        ]
    }


def test_intra_sentence_collision_is_blocker_without_fixed_section_names() -> None:
    findings = detect_category_band_contradictions(
        [
            DocumentSection(
                "Executive Summary", "Pump P-101 Tier 1 (0-5yrs), Pump P-102 Tier 2 (0-5yrs)", 17
            )
        ],
        {},
    )
    assert len(findings) == 1
    assert findings[0].severity == "BLOCKER"
    assert findings[0].rule == "DUPLICATE_CATEGORY_BAND"
    assert "page 17" in findings[0].where


def test_narrative_mismatch_against_definition_table_is_blocker() -> None:
    ground_truth = harvest_definition_tables(
        [_table(["Priority", "Range years"], ["2", "1 to 3 years"])]
    )
    findings = detect_category_band_contradictions(
        [
            DocumentSection(
                "Conclusions",
                "The Priority 2 (5-10 years) equipment requires urgent action.",
                "xii",
            )
        ],
        ground_truth,
    )
    assert len(findings) == 1
    assert findings[0].severity == "BLOCKER"
    assert findings[0].rule == "CATEGORY_BAND_CONTRADICTION"


def test_matching_narrative_and_definition_has_no_blocker() -> None:
    ground_truth = {"priority": {"2": NumericInterval("1 to 3 years", "priority", 1, 3)}}
    findings = detect_category_band_contradictions(
        [DocumentSection("Summary", "Priority 2 (1 to 3 years) is acceptable.", 4)],
        ground_truth,
    )
    assert findings == []


def test_numeric_interval_parser_covers_comparator_and_word_forms() -> None:
    cases = {
        "0 < RUL <= 6": (0, 6, False, True),
        "RUL <= 0": (None, 0, True, True),
        "RUL > 14": (14, None, False, True),
        "6 < RUL <= 14 yrs": (6, 14, False, True),
        "0 to 6 years": (0, 6, True, True),
        "between 6 and 14 years": (6, 14, True, True),
        "greater than 14 yrs": (14, None, False, True),
        "less than or equal to 0": (None, 0, True, True),
    }
    for raw, expected in cases.items():
        interval = parse_numeric_interval(raw)
        assert interval is not None, raw
        assert (
            interval.low,
            interval.high,
            interval.low_inclusive,
            interval.high_inclusive,
        ) == expected
