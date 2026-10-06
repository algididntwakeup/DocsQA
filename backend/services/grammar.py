"""Grammar and Style Analysis Service (M4.1b).

Provides grammar and style analysis for engineering and QC documents.
Includes LanguageTool integration with circuit-breaker protection, technical writing
suppression filters, and deterministic offline rule fallback.
"""

from __future__ import annotations

import logging
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Final

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.issues import BoundingBox
from schemas.linguistic import GrammarAnalysis, LinguisticFinding

logger = logging.getLogger(__name__)

GRAMMAR_SCHEMA_VERSION = "1.0"
GRAMMAR_RULE_VERSION = "grammar/1.1.0"

# Rules suppressed from LanguageTool to prevent false positives in technical engineering writing
SUPPRESSED_LT_RULES: Final[set[str]] = {
    "MORFOLOGIK_RULE_EN_US",  # Handled by custom spellchecker
    "EN_SPECIFIC_CASE",
    # Table cells and fragments don't require full capitalized sentences:
    "UPPERCASE_SENTENCE_START",
    "WHITESPACE_RULE",
    "COMMA_PARENTHESIS_WHITESPACE",
    "SENTENCE_FRAGMENT",
    "PASSIVE_VOICE",  # Handled separately in M4.4
}

# Deterministic patterns for offline fallback
REPEATED_WORD_PATTERN = re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.IGNORECASE)
REPEATED_PHRASE_PATTERN = re.compile(
    r"\b([A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){1,2})\s+\1\b", re.IGNORECASE
)
SPLIT_YEAR_PATTERN = re.compile(r"\b(20\d)\s+(\d)\b")
SPLIT_WORD_CORRECTIONS: Final[dict[str, str]] = {"nine-teen": "nineteen"}
SPLIT_WORD_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = tuple(
    (re.compile(rf"\b{re.escape(misspelling)}\b", re.IGNORECASE), correction)
    for misspelling, correction in SPLIT_WORD_CORRECTIONS.items()
)
COMPOSING_BY_PATTERN = re.compile(r"\bcomprising\s+by\b", re.IGNORECASE)
PRECISION_PAIR_PATTERN = re.compile(
    r"(?P<first>\d+\.\d+)\s*(?:vs\.?|versus|compared\s+(?:with|to))\s*"
    r"(?P<second>\d+\.\d+)",
    re.IGNORECASE,
)
FRAGMENT_RECOMMENDATION_PATTERN = re.compile(
    r"^(?:classified|completed|implemented|reinspected|reassessed|reviewed|inspected|"
    r"replaced|repaired|maintained)\b.*\bby\s+(?:the\s+)?(?:end[- ]?)?20\d{2}\b[.!?]?$",
    re.IGNORECASE,
)

HOMOPHONE_PATTERNS: Final[list[tuple[re.Pattern[str], str, str, str]]] = [
    # (pattern, original_word, suggested_replacement, explanation)
    (
        re.compile(
            r"\bits\s+(?:is|was|are|were|has|have|cannot|should|must|will)\b", re.IGNORECASE
        ),
        "its",
        "it's",
        "Use 'it's' (contraction of 'it is') instead of possessive 'its'.",
    ),
    (
        re.compile(
            r"\bit's\s+(?:thickness|value|diameter|length|weight|pressure|temperature|surface|tolerance|grade)\b",
            re.IGNORECASE,
        ),
        "it's",
        "its",
        "Use possessive 'its' instead of contraction 'it's'.",
    ),
    (
        re.compile(r"\btheir\s+(?:is|are|was|were)\b", re.IGNORECASE),
        "their",
        "there",
        "Use 'there' instead of possessive 'their'.",
    ),
    (
        re.compile(r"\bthe\s+affect\s+of\b", re.IGNORECASE),
        "affect",
        "effect",
        "Use noun 'effect' rather than verb 'affect'.",
    ),
    (
        re.compile(
            r"\bto\s+loose\s+(?:pressure|vacuum|compliance|weight|hardness)\b", re.IGNORECASE
        ),
        "loose",
        "lose",
        "Use 'lose' (verb) rather than 'loose' (adjective).",
    ),
]

SUBJECT_VERB_PATTERNS: Final[list[tuple[re.Pattern[str], str, str, str]]] = [
    (
        re.compile(
            r"\b(specimens|results|tests|measurements|readings|calculations)\s+(?:was|is)\b",
            re.IGNORECASE,
        ),
        "was/is",
        "were/are",
        "Subject-verb disagreement: plural noun with singular verb.",
    ),
    (
        re.compile(
            r"\b(specimen|result|test|measurement|reading|calculation)\s+(?:were|are)\b",
            re.IGNORECASE,
        ),
        "were/are",
        "was/is",
        "Subject-verb disagreement: singular noun with plural verb.",
    ),
]


class GrammarAnalyzer:
    """Grammar and style analyzer with circuit-breaker protection and offline fallback."""

    def __init__(self, enable_remote_lt: bool = False) -> None:
        self.enable_remote_lt = enable_remote_lt
        self._lt_instance: Any = None
        self._circuit_breaker_tripped: bool = False

    def _get_lt(self) -> Any:
        """Lazily initialize LanguageTool with safe fallback on Java or network failure."""
        if self._circuit_breaker_tripped or not self.enable_remote_lt:
            return None

        if self._lt_instance is not None:
            return self._lt_instance

        try:
            import language_tool_python

            # Try initializing local or API tool
            self._lt_instance = language_tool_python.LanguageTool("en-US")
            return self._lt_instance
        except Exception as exc:
            logger.warning(
                "LanguageTool initialization failed, engaging offline fallback circuit breaker: %s",
                exc,
            )
            self._circuit_breaker_tripped = True
            self._lt_instance = None
            return None

    def analyze(self, artifact: ExtractionArtifact) -> GrammarAnalysis:
        """Analyze text spans for grammar errors using LT or deterministic fallback."""
        findings: list[LinguisticFinding] = []
        lt = self._get_lt()

        for span in [*artifact.spans, *_join_adjacent_line_spans(artifact)]:
            text = span.text
            if not text or len(text.strip()) < 4:
                continue

            if lt is not None:
                try:
                    matches = lt.check(text)
                    for m in matches:
                        rule_id = getattr(m, "ruleId", "")
                        if rule_id in SUPPRESSED_LT_RULES:
                            continue

                        offset = getattr(m, "offset", 0)
                        error_len = getattr(m, "errorLength", len(text))
                        replacements = getattr(m, "replacements", [])
                        sug = replacements[0] if replacements else None
                        orig_text = text[offset : offset + error_len]

                        bbox = _sub_bounding_box(span.bbox, text, offset, offset + error_len)
                        findings.append(
                            LinguisticFinding(
                                type="grammar_error",
                                message=getattr(m, "message", "Grammar or style issue detected."),
                                severity=Severity.LOW,
                                confidence=0.88,
                                original_text=orig_text,
                                suggestion=sug,
                                location=bbox,
                                rule_id=f"LT_{rule_id}" if rule_id else "RULE_GRAMMAR_LT",
                            )
                        )
                    continue
                except Exception as exc:
                    logger.warning(
                        "LanguageTool check failed mid-stream, tripping circuit breaker: %s", exc
                    )
                    self._circuit_breaker_tripped = True
                    lt = None

            # Deterministic offline grammar rules
            findings.extend(self._run_offline_rules(span.bbox, text))

        findings.extend(_detect_unclosed_key_section(artifact))
        unique_findings: dict[tuple[str, int, str, int], LinguisticFinding] = {}
        for finding in findings:
            key = (
                finding.rule_id or finding.type,
                finding.location.page_index,
                finding.original_text.casefold(),
                round(finding.location.y0),
            )
            unique_findings.setdefault(key, finding)

        return GrammarAnalysis(
            schema_version=GRAMMAR_SCHEMA_VERSION,
            rule_version=GRAMMAR_RULE_VERSION,
            findings=list(unique_findings.values()),
        )

    def _run_offline_rules(
        self, span_bbox: CoordinateContract, text: str
    ) -> list[LinguisticFinding]:
        """Apply deterministic grammar checks: repeated words, homophones, agreement."""
        local_findings: list[LinguisticFinding] = []

        # Mechanical errors that a general spellchecker often accepts as tokens.
        for match in COMPOSING_BY_PATTERN.finditer(text):
            bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
            local_findings.append(
                LinguisticFinding(
                    type="repeated_phrase",
                    message=(
                        "Use ‘comprising’ without ‘by’, or rewrite the phrase as "
                        "‘consisting of’."
                    ),
                    severity=Severity.LOW,
                    confidence=0.98,
                    original_text=match.group(0),
                    suggestion="comprising",
                    location=bbox,
                    rule_id="RULE_GRAMMAR_COMPRISING_BY",
                )
            )

        for match in REPEATED_PHRASE_PATTERN.finditer(text):
            phrase = match.group(1)
            bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
            local_findings.append(
                LinguisticFinding(
                    type="repeated_phrase",
                    message="Repeated phrase; remove the duplicated words.",
                    severity=Severity.LOW,
                    confidence=0.96,
                    original_text=match.group(0),
                    suggestion=phrase,
                    location=bbox,
                    rule_id="RULE_GRAMMAR_REPEATED_PHRASE",
                )
            )

        for match in SPLIT_YEAR_PATTERN.finditer(text):
            original = match.group(0)
            suggestion = f"{match.group(1)}{match.group(2)}"
            bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
            local_findings.append(
                LinguisticFinding(
                    type="spelling_split",
                    message="Year digits are split by whitespace.",
                    severity=Severity.LOW,
                    confidence=0.98,
                    original_text=original,
                    suggestion=suggestion,
                    location=bbox,
                    rule_id="RULE_GRAMMAR_SPLIT_YEAR",
                )
            )

        for pattern, correction in SPLIT_WORD_PATTERNS:
            for match in pattern.finditer(text):
                bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
                local_findings.append(
                    LinguisticFinding(
                        type="spelling_split",
                        message="A word has been incorrectly split with a hyphen.",
                        severity=Severity.LOW,
                        confidence=0.98,
                        original_text=match.group(0),
                        suggestion=correction,
                        location=bbox,
                        rule_id="RULE_GRAMMAR_SPLIT_WORD",
                    )
                )

        for match in PRECISION_PAIR_PATTERN.finditer(text):
            first_text, second_text = match.group("first", "second")
            first_places = len(first_text.partition(".")[2])
            second_places = len(second_text.partition(".")[2])
            if abs(first_places - second_places) < 3:
                continue
            short_text, long_text = (
                (first_text, second_text)
                if first_places < second_places
                else (second_text, first_text)
            )
            try:
                short_value = Decimal(short_text)
                long_value = Decimal(long_text)
                quantum = Decimal(1).scaleb(-min(first_places, second_places))
                rounded_long = long_value.quantize(quantum, rounding=ROUND_HALF_UP)
                rounded_short = short_value.quantize(quantum, rounding=ROUND_HALF_UP)
            except InvalidOperation:
                continue
            if rounded_long == rounded_short:
                continue
            bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
            local_findings.append(
                LinguisticFinding(
                    type="sigfig_inconsistency",
                    message=(
                        f"Values {first_text} and {second_text} differ at the precision "
                        "shown; state a consistent rounding convention."
                    ),
                    severity=Severity.LOW,
                    confidence=0.92,
                    original_text=match.group(0),
                    suggestion=f"{short_text} (or rounded value {rounded_long})",
                    location=bbox,
                    rule_id="RULE_SIGFIG_INCONSISTENCY",
                )
            )

        # 1. Repeated words ("the the", "in in", "is is")
        for match in REPEATED_WORD_PATTERN.finditer(text):
            word = match.group(1)
            # Skip numbers or single-character repeated tokens (e.g. "AA")
            if len(word) < 2:
                continue
            matched_str = match.group(0)
            bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
            local_findings.append(
                LinguisticFinding(
                    type="repeated_phrase",
                    message=f"Possible repeated word '{word}'.",
                    severity=Severity.LOW,
                    confidence=0.92,
                    original_text=matched_str,
                    suggestion=word,
                    location=bbox,
                    rule_id="RULE_GRAMMAR_REPEATED_WORD",
                )
            )

        # 2. Homophone confusions
        for pattern, orig_kw, sug_kw, explanation in HOMOPHONE_PATTERNS:
            for match in pattern.finditer(text):
                bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
                matched_str = match.group(0)
                # Compute replacement string
                sug_str = re.sub(re.escape(orig_kw), sug_kw, matched_str, flags=re.IGNORECASE)
                local_findings.append(
                    LinguisticFinding(
                        type="grammar_error",
                        message=explanation,
                        severity=Severity.LOW,
                        confidence=0.90,
                        original_text=matched_str,
                        suggestion=sug_str,
                        location=bbox,
                        rule_id="RULE_GRAMMAR_HOMOPHONE",
                    )
                )

        # 3. Subject-verb disagreements
        for pattern, _orig_verb, _sug_verb, explanation in SUBJECT_VERB_PATTERNS:
            for match in pattern.finditer(text):
                bbox = _sub_bounding_box(span_bbox, text, match.start(), match.end())
                matched_str = match.group(0)
                words = matched_str.split()
                agr_sug: str | None = None
                if len(words) >= 2:
                    noun, verb = words[0], words[1]
                    # Compute appropriate singular/plural replacement verb
                    replacement_verb = (
                        "were"
                        if verb.lower() == "was"
                        else "are"
                        if verb.lower() == "is"
                        else "was"
                        if verb.lower() == "were"
                        else "is"
                    )
                    agr_sug = f"{noun} {replacement_verb}"

                local_findings.append(
                    LinguisticFinding(
                        type="grammatical_agreement",
                        message=explanation,
                        severity=Severity.LOW,
                        confidence=0.85,
                        original_text=matched_str,
                        suggestion=agr_sug,
                        location=bbox,
                        rule_id="RULE_GRAMMAR_AGREEMENT",
                    )
                )

        return local_findings


def _join_adjacent_line_spans(artifact: ExtractionArtifact) -> list[Any]:
    """Join nearby same-line text spans so mechanics rules can cross font runs."""
    from types import SimpleNamespace

    grouped: dict[int, list[Any]] = {}
    for span in artifact.spans:
        grouped.setdefault(span.bbox.page_index, []).append(span)
    joined: list[Any] = []
    for page_spans in grouped.values():
        ordered = sorted(page_spans, key=lambda span: (span.bbox.y0, span.bbox.x0))
        line: list[Any] = []
        for span in ordered:
            if line:
                prev = line[-1].bbox
                same_line = abs(span.bbox.y0 - prev.y0) <= 2.5
                close = span.bbox.x0 - prev.x1 <= 18
                if not (same_line and close):
                    joined.append(_merge_line(line, SimpleNamespace))
                    line = []
            line.append(span)
        if line:
            joined.append(_merge_line(line, SimpleNamespace))
    return [line for line in joined if len(line.text.split()) > 1]


def _merge_line(spans: list[Any], namespace: Any) -> Any:
    first = spans[0].bbox
    merged_bbox = CoordinateContract(
        page_index=first.page_index,
        x0=min(span.bbox.x0 for span in spans),
        y0=min(span.bbox.y0 for span in spans),
        x1=max(span.bbox.x1 for span in spans),
        y1=max(span.bbox.y1 for span in spans),
        page_width=first.page_width,
        page_height=first.page_height,
    )
    return namespace(text=" ".join(span.text.strip() for span in spans), bbox=merged_bbox)


def _detect_unclosed_key_section(artifact: ExtractionArtifact) -> list[LinguisticFinding]:
    """Flag an unfinished terminal sentence in summary, conclusion, or recommendation text."""
    target = re.compile(r"\b(?:executive\s+summary|abstract|conclusions?|recommendations?)\b", re.I)
    headings = sorted(
        (heading for heading in artifact.headings if heading.text.strip()),
        key=lambda heading: (heading.bbox.page_index, heading.bbox.y0),
    )
    spans = sorted(artifact.spans, key=lambda span: (span.bbox.page_index, span.bbox.y0))
    active_target = False
    target_section_id = 0
    heading_index = 0
    last_by_section: dict[int, Any] = {}
    for span in spans:
        position = (span.bbox.page_index, span.bbox.y0)
        while (
            heading_index < len(headings)
            and (
                headings[heading_index].bbox.page_index,
                headings[heading_index].bbox.y0,
            )
            <= position
        ):
            active_target = bool(target.search(headings[heading_index].text))
            if active_target:
                target_section_id += 1
            heading_index += 1
        if active_target and span.text.strip():
            last_by_section[target_section_id] = span

    findings: list[LinguisticFinding] = []
    continuation = re.compile(r"\b(?:and|or|because|which|that|to|of|with|by|for|in)$", re.I)
    for span in last_by_section.values():
        text = span.text.strip()
        if len(text.split()) < 3 or re.search(r"[.!?:;][\"')\]]?$", text):
            continue
        if not continuation.search(text) and not FRAGMENT_RECOMMENDATION_PATTERN.search(text):
            continue
        bbox = _sub_bounding_box(span.bbox, text, 0, len(text))
        findings.append(
            LinguisticFinding(
                type="unclosed_sentence",
                message="Section ends with an unfinished sentence or continuation phrase.",
                severity=Severity.LOW,
                confidence=0.9,
                original_text=text,
                suggestion=None,
                location=bbox,
                rule_id="RULE_GRAMMAR_UNCLOSED_SENTENCE",
            )
        )
    return findings


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


def analyze_grammar(
    artifact: ExtractionArtifact,
    enable_remote_lt: bool = False,
) -> GrammarAnalysis:
    """Analyze grammar in document text with circuit-breaker protection."""
    analyzer = GrammarAnalyzer(enable_remote_lt=enable_remote_lt)
    return analyzer.analyze(artifact)
