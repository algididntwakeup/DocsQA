"""Versioned evidence emitted by deterministic reference drift detection (F11)."""

from typing import Literal

from pydantic import Field

from schemas.base import ApiModel
from schemas.extraction import CoordinateContract


class TocEntry(ApiModel):
    """A structured entry extracted from a Table of Contents, Figures, or Tables."""

    source_list: Literal["TOC", "LOF", "LOT"]
    raw_text: str
    normalized_title: str
    referenced_page_label: str
    referenced_page_number: int | None = None
    location: CoordinateContract


class ActualTarget(ApiModel):
    """An actual heading or caption found in the document body."""

    title: str
    normalized_title: str
    actual_page_index: int = Field(ge=0)
    actual_page_label: str
    location: CoordinateContract


class RefDriftFinding(ApiModel):
    """Actionable reference drift finding ready for review or aggregation."""

    kind: Literal["REF_DRIFT", "MISSING_TARGET", "DUPLICATE_CAPTION"]
    label: str
    source_list: Literal["TOC", "LOF", "LOT"]
    referenced_page_label: str
    actual_page_label: str | None = None
    page_delta: int | None = None
    entry_location: CoordinateContract
    target_location: CoordinateContract | None = None
    message: str


class RefDriftAnalysis(ApiModel):
    """Complete versioned artifact persisted for the reference drift stage."""

    schema_version: str = "1.0"
    rule_version: str = "ref-drift/1.0.0"
    toc_entries_found: int = 0
    entries: list[TocEntry] = Field(default_factory=list)
    findings: list[RefDriftFinding] = Field(default_factory=list)
