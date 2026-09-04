"""Versioned evidence emitted by the deterministic revision-sync analyzer."""

from typing import Literal

from pydantic import Field

from schemas.base import ApiModel
from schemas.extraction import CoordinateContract

RevisionSourceName = Literal["FILENAME", "COVER", "REVISION_SHEET"]


class RevisionSource(ApiModel):
    """One raw and normalized revision value with optional source location."""

    source: RevisionSourceName
    raw_value: str | None = None
    normalized_value: str | None = None
    location: CoordinateContract | None = None


class RevisionAnalysis(ApiModel):
    """Three-way revision comparison ready for later issue aggregation."""

    schema_version: str = "1.0"
    rule_version: str = "revision-sync/1.0.0"
    outcome: Literal["MATCH", "MISMATCH", "INCOMPLETE"]
    sources: list[RevisionSource] = Field(min_length=3, max_length=3)
    sources_disagreeing: list[RevisionSourceName] = Field(default_factory=list)
    missing_sources: list[RevisionSourceName] = Field(default_factory=list)
