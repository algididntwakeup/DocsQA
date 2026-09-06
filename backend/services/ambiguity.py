"""Contextual Ambiguity and Passive Voice Analysis Service (M4.4).

Detects ambiguous specifications, inconsistent material grades (e.g. 316 vs 316L),
vague non-quantitative directives, and passive voice constructions with suggested
active voice rewrites.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Final

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.issues import BoundingBox
from schemas.linguistic import AmbiguityAnalysis, LinguisticFinding

AMBIGUITY_SCHEMA_VERSION = "1.0"
AMBIGUITY_RULE_VERSION = "ambiguity/1.0.0"

# Common material grade patterns for consistency tracking
# Matches patterns like: 316, 316L, 304, 304L, 317L, 321, A36, SA-516-60, SA-516-70
MATERIAL_GRADE_PATTERN = re.compile(
    r"\b((?:AISI|UNS|ASTM|ASME|SA|A|SS)?[- ]?"
    r"(?:304L?|316L?|317L?|321H?|410|420|2205|2507|516-(?:60|65|70)|A36))\b",
    re.IGNORECASE,
)

# Grade family groups that might indicate ambiguous or conflicting specs if mixed
GRADE_FAMILIES: Final[dict[str, str]] = {
    "316": "316_FAMILY",
    "316l": "316_FAMILY",
    "304": "304_FAMILY",
    "304l": "304_FAMILY",
    "317": "317_FAMILY",
    "317l": "317_FAMILY",
    "516-60": "SA516_FAMILY",
    "516-65": "SA516_FAMILY",
    "516-70": "SA516_FAMILY",
}

# Vague non-quantitative directives that fail auditability
VAGUE_DIRECTIVE_PATTERNS: Final[list[tuple[re.Pattern[str], str]]] = [
    (
        re.compile(r"\b(sufficient(?:ly)?\s+[a-z]+)\b", re.IGNORECASE),
        "Replace vague qualifier 'sufficiently' with an explicit quantitative metric or tolerance.",
    ),
    (
        re.compile(r"\b(approximately(?:\s+[a-z]+)?)\b", re.IGNORECASE),
        "Replace 'approximately' with an explicit numerical range or allowable tolerance.",
    ),
    (
        re.compile(
            r"\b(as\s+appropriate|as\s+applicable|as\s+deemed\s+necessary)\b", re.IGNORECASE
        ),
        "Specify the exact conditions or engineering standards governing this action.",
    ),
    (
        re.compile(
            r"\b(periodic(?:ally)?\s+(?:inspection|inspected|tested|testing|monitored|monitoring|checked|checking))\b",
            re.IGNORECASE,
        ),
        "Define an explicit inspection interval (e.g. daily, monthly, or after every N cycles).",
    ),
    (
        re.compile(r"\b(clean(?:ed)?\s+thoroughly)\b", re.IGNORECASE),
        "Specify surface cleanliness criteria (e.g. SSPC-SP 10 / NACE No. 2).",
    ),
    (
        re.compile(r"\b(adequate(?:\s+[a-z]+)?)\b", re.IGNORECASE),
        "Replace vague adjective 'adequate' with an objective measurable acceptance threshold.",
    ),
]

# Passive voice constructions with optional agent ("by the ...")
PASSIVE_AGENT_PATTERN = re.compile(
    r"\b(?:shall\s+be|must\s+be|is|are|was|were|has\s+been|have\s+been)\s+"
    r"([a-z]+(?:ed|en|t))\s+by\s+(the\s+[a-z\s]+?)(?=[.,;\n]|$)",
    re.IGNORECASE,
)

PASSIVE_NO_AGENT_PATTERN = re.compile(
    r"\b(shall\s+be|must\s+be|has\s+been|have\s+been)\s+(inspected|tested|performed|examined|calibrated|reviewed|approved|welded)\b",
    re.IGNORECASE,
)


def _sub_bounding_box(
    span_bbox: CoordinateContract,
    span_text: str,
    start_char: int,
    end_char: int,
) -> BoundingBox:
    """Linearly interpolate bounding box coordinates for a sub-string word."""
    total_len = max(len(span_text), 1)
    span_width = span_bbox.x1 - span_bbox.x0
    x0 = span_bbox.x0 + (start_char / total_len) * span_width
    x1 = span_bbox.x0 + (end_char / total_len) * span_width
    return BoundingBox(
        page_index=span_bbox.page_index,
        x0=round(max(0.0, x0), 1),
        y0=round(max(0.0, span_bbox.y0), 1),
        x1=round(max(0.0, x1), 1),
        y1=round(max(0.0, span_bbox.y1), 1),
        page_width=span_bbox.page_width,
        page_height=span_bbox.page_height,
    )


def analyze_ambiguity(artifact: ExtractionArtifact) -> AmbiguityAnalysis:
    """Detect vague directives, inconsistent material grades, and passive voice."""
    findings: list[LinguisticFinding] = []

    # 1. Track material grade occurrences across all spans
    # family -> list of (raw_token, span, start_char, end_char)
    family_occurrences: dict[str, list[tuple[str, CoordinateContract, str, int, int]]] = (
        defaultdict(list)
    )

    for span in artifact.spans:
        text = span.text
        if not text:
            continue

        # Check material grades
        for match in MATERIAL_GRADE_PATTERN.finditer(text):
            token = match.group(0).strip()
            norm = re.sub(
                r"^(?:AISI|UNS|ASTM|ASME|SA|A|SS)[- ]?", "", token, flags=re.IGNORECASE
            ).lower()
            if norm in GRADE_FAMILIES:
                family = GRADE_FAMILIES[norm]
                family_occurrences[family].append(
                    (token, span.bbox, text, match.start(), match.end())
                )

        # Check vague directives
        for pattern, sug in VAGUE_DIRECTIVE_PATTERNS:
            for match in pattern.finditer(text):
                matched_str = match.group(0)
                bbox = _sub_bounding_box(span.bbox, text, match.start(), match.end())
                findings.append(
                    LinguisticFinding(
                        type="VAGUE_DIRECTIVE",
                        message=f"Ambiguous, non-quantifiable directive '{matched_str}'.",
                        severity=Severity.LOW,
                        confidence=0.88,
                        original_text=matched_str,
                        suggestion=sug,
                        location=bbox,
                        rule_id="RULE_AMBIGUITY_VAGUE_DIRECTIVE",
                    )
                )

        # Check passive voice with agent: "shall be inspected by the contractor"
        for match in PASSIVE_AGENT_PATTERN.finditer(text):
            verb, agent = match.group(1), match.group(2).strip()
            matched_str = match.group(0)
            bbox = _sub_bounding_box(span.bbox, text, match.start(), match.end())

            # Generate active voice suggestion
            active_sug = f"{agent.capitalize()} shall {verb}"
            # normalize verb ending (e.g. inspected -> inspect, performed -> perform)
            if verb.endswith("ed") and not verb.endswith("eed"):
                active_sug = f"{agent.capitalize()} shall {verb[:-2]}"

            findings.append(
                LinguisticFinding(
                    type="PASSIVE_VOICE",
                    message=f"Passive voice with specified agent: '{matched_str}'.",
                    severity=Severity.LOW,
                    confidence=0.85,
                    original_text=matched_str,
                    suggestion=active_sug,
                    location=bbox,
                    rule_id="RULE_STYLE_PASSIVE_VOICE",
                )
            )

    # Check for inconsistent material grades across families
    for _family, items in family_occurrences.items():
        distinct_tokens = {item[0].upper() for item in items}
        # If multiple variants of the same grade family exist in the document (e.g. 316 and 316L)
        if len(distinct_tokens) > 1:
            variants_str = ", ".join(sorted(distinct_tokens))
            for token, bbox_contract, text_span, start_ch, end_ch in items:
                bbox = _sub_bounding_box(bbox_contract, text_span, start_ch, end_ch)
                findings.append(
                    LinguisticFinding(
                        type="AMBIGUOUS_SPECIFICATION",
                        message=(
                            f"Inconsistent material grade reference '{token}'. Document references "
                            f"multiple variant designations: {variants_str}."
                        ),
                        severity=Severity.MEDIUM,
                        confidence=0.92,
                        original_text=token,
                        suggestion=(
                            f"Harmonize specification to a single uniform grade designation "
                            f"({variants_str})."
                        ),
                        location=bbox,
                        rule_id="RULE_AMBIGUITY_MATERIAL_GRADE",
                    )
                )

    return AmbiguityAnalysis(
        schema_version=AMBIGUITY_SCHEMA_VERSION,
        rule_version=AMBIGUITY_RULE_VERSION,
        findings=findings,
    )
