"""Reference Pack Loader and Registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from schemas.reference_pack import (
    BenchmarkCase,
    ReferencePackManifest,
    ReferenceRule,
)


@dataclass(frozen=True, slots=True)
class ReferencePack:
    """An immutable bundle of reference standard metadata, rules, and benchmarks."""

    manifest: ReferencePackManifest
    rules: list[ReferenceRule]
    benchmarks: list[BenchmarkCase]


class ReferencePackLoader:
    """Loads and validates reference packs from the filesystem."""

    @staticmethod
    def load_pack(pack_dir: Path | str) -> ReferencePack:
        """Load and strictly validate a single reference pack directory."""
        directory = Path(pack_dir)
        manifest_file = directory / "manifest.json"
        rules_file = directory / "rules.json"
        benchmarks_file = directory / "benchmarks.json"

        if not manifest_file.is_file():
            raise FileNotFoundError(f"Missing manifest.json in reference pack: {directory}")
        if not rules_file.is_file():
            raise FileNotFoundError(f"Missing rules.json in reference pack: {directory}")
        if not benchmarks_file.is_file():
            raise FileNotFoundError(f"Missing benchmarks.json in reference pack: {directory}")

        manifest_raw = json.loads(manifest_file.read_text(encoding="utf-8"))
        rules_raw = json.loads(rules_file.read_text(encoding="utf-8"))
        benchmarks_raw = json.loads(benchmarks_file.read_text(encoding="utf-8"))

        rules = [ReferenceRule.model_validate(r) for r in rules_raw]
        benchmarks = [BenchmarkCase.model_validate(b) for b in benchmarks_raw]

        manifest_data = dict(manifest_raw)
        manifest_data["rules_count"] = len(rules)
        manifest_data["benchmarks_count"] = len(benchmarks)
        manifest = ReferencePackManifest.model_validate(manifest_data)

        # Validate that each rule has parameters appropriate for its kind
        for rule in rules:
            if rule.kind == "range" and rule.range_params is None:
                raise ValueError(f"Rule {rule.rule_id} missing range_params")
            if rule.kind == "unit" and rule.unit_params is None:
                raise ValueError(f"Rule {rule.rule_id} missing unit_params")
            if rule.kind == "numeric_limit" and rule.numeric_limit_params is None:
                raise ValueError(f"Rule {rule.rule_id} missing numeric_limit_params")
            if rule.kind == "terminology" and rule.terminology_params is None:
                raise ValueError(f"Rule {rule.rule_id} missing terminology_params")
            if rule.kind == "required_reference" and rule.required_reference_params is None:
                raise ValueError(f"Rule {rule.rule_id} missing required_reference_params")

        return ReferencePack(
            manifest=manifest,
            rules=rules,
            benchmarks=benchmarks,
        )


class ReferencePackRegistry:
    """Registry discovering and caching loaded reference packs."""

    _instance: ClassVar[ReferencePackRegistry | None] = None

    def __init__(self, root_dir: Path | str | None = None) -> None:
        if root_dir is not None:
            self._root_dir = Path(root_dir)
        else:
            # Default to backend/reference_packs
            self._root_dir = Path(__file__).resolve().parents[2] / "reference_packs"
        self._packs: dict[str, ReferencePack] = {}
        self._loaded = False

    def reload(self) -> None:
        """Scan root directory and reload all reference packs."""
        self._packs.clear()
        if self._root_dir.is_dir():
            for child in sorted(self._root_dir.iterdir()):
                if child.is_dir() and (child / "manifest.json").is_file():
                    pack = ReferencePackLoader.load_pack(child)
                    self._packs[pack.manifest.pack_id] = pack
                    self._packs[pack.manifest.standard_code] = pack
        self._loaded = True

    def get_pack(self, identifier: str) -> ReferencePack | None:
        """Look up reference pack by pack_id or standard_code."""
        if not self._loaded:
            self.reload()
        return self._packs.get(identifier)

    def list_packs(self) -> list[ReferencePack]:
        """Return all unique discovered reference packs."""
        if not self._loaded:
            self.reload()
        # Filter duplicate mappings (by pack_id vs standard_code)
        seen: set[str] = set()
        result: list[ReferencePack] = []
        for pack in self._packs.values():
            if pack.manifest.pack_id not in seen:
                seen.add(pack.manifest.pack_id)
                result.append(pack)
        return result


def get_default_registry() -> ReferencePackRegistry:
    """Return the global ReferencePackRegistry singleton."""
    if ReferencePackRegistry._instance is None:
        ReferencePackRegistry._instance = ReferencePackRegistry()
    return ReferencePackRegistry._instance
