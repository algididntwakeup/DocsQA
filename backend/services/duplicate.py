"""Near-Duplicate Content Detection Service (M4.3).

Identifies near-duplicate paragraphs and clauses across multi-page documents
using token sort fuzzy matching (threshold >= 85%) while suppressing boilerplate
headers and footers. Emits findings with dual-location bounding boxes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from math import ceil
from typing import Final

from thefuzz import fuzz  # type: ignore[import-untyped]

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.issues import BoundingBox
from schemas.linguistic import DuplicateAnalysis, LinguisticFinding

DUPLICATE_SCHEMA_VERSION = "1.0"
DUPLICATE_RULE_VERSION = "duplicate/1.0.0"

DEFAULT_SIMILARITY_THRESHOLD: Final[int] = 85
MIN_BLOCK_LENGTH: Final[int] = 30
MAX_LENGTH_DIFF_RATIO: Final[float] = 0.35
MIN_TOKEN_LENGTH: Final[int] = 4
MIN_SHARED_TOKEN_RATIO: Final[float] = 0.2
MAX_TOKEN_POSTINGS: Final[int] = 128
MAX_FUZZY_COMPARISONS: Final[int] = 100_000

PAGE_NUMBER_PATTERN = re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class CandidateBlock:
    """A substantive text block candidate for duplicate comparison."""

    index: int
    text: str
    cleaned_text: str
    bbox: BoundingBox
    page_index: int


def _is_header_or_footer(bbox: CoordinateContract) -> bool:
    """Detect if bounding box resides within header or footer margins."""
    if bbox.page_height <= 0:
        return False
    top_margin = bbox.page_height * 0.08
    bottom_margin = bbox.page_height * 0.92
    return bbox.y1 <= top_margin or bbox.y0 >= bottom_margin


def _clean_text(text: str) -> str:
    """Normalize whitespace and punctuation for comparison."""
    return re.sub(r"\s+", " ", text).strip()


def _substantive_tokens(text: str) -> set[str]:
    """Return normalized tokens useful for cheap duplicate candidate pruning."""
    return {
        token
        for token in re.findall(rf"[a-z0-9]{{{MIN_TOKEN_LENGTH},}}", text.lower())
    }


def _is_boilerplate(text: str) -> bool:
    """Filter out standard document boilerplate like page numbers or simple disclaimers."""
    cleaned = text.strip()
    if PAGE_NUMBER_PATTERN.match(cleaned):
        return True
    return cleaned.lower() in {"confidential", "proprietary", "all rights reserved"}


def _to_bounding_box(contract: CoordinateContract) -> BoundingBox:
    """Convert CoordinateContract to BoundingBox."""
    return BoundingBox(
        page_index=contract.page_index,
        x0=round(contract.x0, 1),
        y0=round(contract.y0, 1),
        x1=round(contract.x1, 1),
        y1=round(contract.y1, 1),
        page_width=contract.page_width,
        page_height=contract.page_height,
    )


def analyze_duplicates(
    artifact: ExtractionArtifact,
    threshold: int = DEFAULT_SIMILARITY_THRESHOLD,
) -> DuplicateAnalysis:
    """Scan document spans for near-duplicate text blocks across pages/sections."""
    candidates: list[CandidateBlock] = []

    for idx, span in enumerate(artifact.spans):
        raw_text = span.text
        if not raw_text or len(raw_text.strip()) < MIN_BLOCK_LENGTH:
            continue

        if _is_header_or_footer(span.bbox):
            continue

        cleaned = _clean_text(raw_text)
        if _is_boilerplate(cleaned):
            continue

        candidates.append(
            CandidateBlock(
                index=idx,
                text=raw_text,
                cleaned_text=cleaned,
                bbox=_to_bounding_box(span.bbox),
                page_index=span.bbox.page_index,
            )
        )

    findings: list[LinguisticFinding] = []
    matched_indices: set[int] = set()

    # Build an inverted index first. The previous implementation compared every
    # block with every later block, which made fuzzy matching O(N^2) for long PDFs.
    token_sets = [_substantive_tokens(block.cleaned_text) for block in candidates]
    postings: dict[str, list[int]] = defaultdict(list)
    for index, tokens in enumerate(token_sets):
        for token in tokens:
            bucket = postings[token]
            if len(bucket) < MAX_TOKEN_POSTINGS:
                bucket.append(index)

    fuzzy_comparisons = 0
    for i, block_a in enumerate(candidates):
        if fuzzy_comparisons >= MAX_FUZZY_COMPARISONS:
            break
        tokens_a = token_sets[i]
        if not tokens_a:
            continue

        # Count shared tokens rather than fuzzy-comparing unrelated paragraphs.
        overlap_counts: dict[int, int] = defaultdict(int)
        for token in tokens_a:
            for j in postings.get(token, []):
                if j > i and j not in matched_indices:
                    overlap_counts[j] += 1

        min_shared = max(2, ceil(min(len(tokens_a), 12) * MIN_SHARED_TOKEN_RATIO))
        candidate_indices = sorted(
            j for j, shared in overlap_counts.items() if shared >= min_shared
        )
        len_a = len(block_a.cleaned_text)
        for j in candidate_indices:
            if fuzzy_comparisons >= MAX_FUZZY_COMPARISONS:
                break
            block_b = candidates[j]
            len_b = len(block_b.cleaned_text)
            max_len = max(len_a, len_b)
            if abs(len_a - len_b) / max_len > MAX_LENGTH_DIFF_RATIO:
                continue

            fuzzy_comparisons += 1
            score = fuzz.token_sort_ratio(block_a.cleaned_text, block_b.cleaned_text)
            if score >= threshold:
                matched_indices.add(j)
                orig_page = block_a.page_index + 1

                findings.append(
                    LinguisticFinding(
                        type="DUPLICATE_CONTENT",
                        message=(
                            f"Near-duplicate content detected ({score}% similarity with passage "
                            f"on Page {orig_page})."
                        ),
                        severity=Severity.LOW,
                        confidence=round(score / 100.0, 2),
                        original_text=block_b.text,
                        suggestion=f"Review redundancy against original text on Page {orig_page}.",
                        location=block_b.bbox,
                        original_location=block_a.bbox,
                        rule_id="RULE_DUPLICATE_CONTENT",
                    )
                )

    return DuplicateAnalysis(
        schema_version=DUPLICATE_SCHEMA_VERSION,
        rule_version=DUPLICATE_RULE_VERSION,
        findings=findings,
    )
