"""Grammar and Style Analysis Service (M4.1b).

Provides grammar and style analysis for engineering and QC documents.
Includes LanguageTool integration with circuit-breaker protection, technical writing
suppression filters, and deterministic offline rule fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.issues import BoundingBox
from schemas.linguistic import GrammarAnalysis, LinguisticFinding

logger = logging.getLogger(__name__)

GRAMMAR_SCHEMA_VERSION = "1.0"
GRAMMAR_RULE_VERSION = "grammar/1.0.0"

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

        for span in artifact.spans:
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
                                type="GRAMMAR_ERROR",
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

        return GrammarAnalysis(
            schema_version=GRAMMAR_SCHEMA_VERSION,
            rule_version=GRAMMAR_RULE_VERSION,
            findings=findings,
        )

    def _run_offline_rules(
        self, span_bbox: CoordinateContract, text: str
    ) -> list[LinguisticFinding]:
        """Apply deterministic grammar checks: repeated words, homophones, agreement."""
        local_findings: list[LinguisticFinding] = []

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
                    type="GRAMMAR_ERROR",
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
                        type="GRAMMAR_ERROR",
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
                        type="GRAMMAR_ERROR",
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
