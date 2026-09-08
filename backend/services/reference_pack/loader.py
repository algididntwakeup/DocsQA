"""Reference Pack Loader, Registry, and Active Pack Resolver."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from schemas.reference_pack import (
    BenchmarkCase,
    ReferencePackManifest,
    ReferenceRule,
)
from services.standard_traceability import normalize_standard_code


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

        # Resolve whether source PDF exists in reference-library
        ref_lib_dir = Path(__file__).resolve().parents[3] / "reference-library"
        source_pdf_name = manifest_raw.get("source_pdf")
        source_available = bool(source_pdf_name and (ref_lib_dir / source_pdf_name).is_file())

        rules = [ReferenceRule.model_validate(r) for r in rules_raw]
        benchmarks = [BenchmarkCase.model_validate(b) for b in benchmarks_raw]

        manifest_data = dict(manifest_raw)
        manifest_data["rules_count"] = len(rules)
        manifest_data["benchmarks_count"] = len(benchmarks)
        manifest_data["source_available"] = source_available
        manifest = ReferencePackManifest.model_validate(manifest_data)

        # Configured packs require at least one rule and benchmark
        if manifest.status == "CONFIGURED" and not rules:
            raise ValueError(
                f"Configured reference pack '{manifest.pack_id}' must have at least one rule."
            )

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
        """Return all unique discovered reference packs (configured and unconfigured)."""
        return self.list_all_packs()

    def list_all_packs(self) -> list[ReferencePack]:
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

    def list_configured_packs(self) -> list[ReferencePack]:
        """Return only packs that are marked CONFIGURED with active rules."""
        return [p for p in self.list_all_packs() if p.manifest.status == "CONFIGURED"]


def get_default_registry() -> ReferencePackRegistry:
    """Return the global ReferencePackRegistry singleton."""
    if ReferencePackRegistry._instance is None:
        ReferencePackRegistry._instance = ReferencePackRegistry()
    return ReferencePackRegistry._instance


# ── Pack Resolver ─────────────────────────────────────────────────────

# Directory holding shipped built-in packs (see README in reference-library/).
BUILTIN_PACKS_DIR = Path(__file__).resolve().parents[2] / "reference_packs"

# Skipped pack statuses: they carry no trustworthy rules yet.
_INACTIVE_STATUSES = {"UNCONFIGURED", "VALIDATION_FAILED"}

# Simple normalizer used when matching detected citations to packs: strips
# common qualifiers (STD/RP/SPEC/SECTION/DIVISION) and punctuation so
# "API RP 580" matches pack standard_code "API RP 580" and "API 510"
# matches "API 510", but distinct numbers never cross-match.
_QUALIFIER_RE = re.compile(
    r"\b(?:STD|SPEC|RP|TR|REC|SEC(?:TION)?|DIV(?:ISION)?)\b\.?", re.IGNORECASE
)
_SLASH_TAIL_RE = re.compile(r"/.*$")


def _match_key(value: str) -> str:
    """Reduce a standard code or citation to its comparable numeric-ish core.

    ``"API RP 580"``, ``"API 580"`` → ``API580``;
    ``"ASME BPVC.VIII.1"``, ``"ASME Section VIII Division 1"`` → ``ASMEVIII1``.
    Distinct standard numbers never collapse to the same key.
    """
    normalized = _SLASH_TAIL_RE.sub("", normalize_standard_code(value))
    normalized = _QUALIFIER_RE.sub(" ", normalized)
    normalized = re.sub(r"[^A-Z0-9]+", "", normalized)
    # Drop the BPVC marker so "ASME BPVC.VIII.1" matches "ASME Section VIII 1".
    return normalized.replace("BPVC", "")


class PackResolutionError(ValueError):
    """Raised when an explicitly requested pack cannot be activated."""


class PackResolver:
    """Resolves the set of packs active for one evaluation run.

    A pack becomes active when (a) the user explicitly selected it, or
    (b) its standard is cited in the document body (auto-detection).
    Packs whose manifest status is UNCONFIGURED or VALIDATION_FAILED are
    skipped: they carry no trustworthy deterministic rules yet.
    """

    def __init__(self, builtin_dir: Path | str | None = None) -> None:
        self._builtin_dir = Path(builtin_dir) if builtin_dir else BUILTIN_PACKS_DIR

    def _tenant_packs_dir(self, tenant_id: str) -> Path:
        """``storage/uploads/tenants/{tenant_id}/packs`` — the per-tenant pack store."""
        backend_root = Path(__file__).resolve().parents[2]
        return (
            backend_root
            / "storage"
            / "uploads"
            / "tenants"
            / str(tenant_id)
            / "packs"
        )

    def _load_custom_pack(self, pack_dir: Path, tenant_id: str) -> ReferencePack | None:
        """Load a tenant custom pack; a broken bundle is skipped, never fatal."""
        try:
            return ReferencePackLoader.load_pack(pack_dir)
        except (OSError, ValueError, KeyError):
            return None

    def available_packs(self, tenant_id: str | None = None) -> list[ReferencePack]:
        """List every loadable pack visible to this tenant (built-in + custom)."""
        registry = get_default_registry()
        packs = list(registry.list_all_packs())
        if tenant_id:
            tenant_dir = self._tenant_packs_dir(tenant_id)
            if tenant_dir.is_dir():
                for child in sorted(tenant_dir.iterdir()):
                    if child.is_dir() and (child / "manifest.json").is_file():
                        pack = self._load_custom_pack(child, tenant_id)
                        if pack is not None:
                            packs.append(pack)
        return packs

    def _by_match_key(self, packs: list[ReferencePack]) -> dict[str, ReferencePack]:
        index: dict[str, ReferencePack] = {}
        for pack in packs:
            key = _match_key(pack.manifest.standard_code)
            if key:
                index.setdefault(key, pack)
        return index

    def resolve_active_packs(
        self,
        detected_citations: list[str],
        explicit_pack_ids: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[ReferencePack]:
        """Return the deduplicated active packs for one evaluation run.

        Selection = explicit user packs ∪ packs whose standard_code matches a
        detected citation. UNCONFIGURED / VALIDATION_FAILED packs are skipped.
        """
        available = self.available_packs(tenant_id)
        by_id: dict[str, ReferencePack] = {}
        for pack in available:
            by_id.setdefault(pack.manifest.pack_id, pack)

        selected: dict[str, ReferencePack] = {}

        # 1) Explicit user selection (always wins, even overriding status checks
        # is NOT allowed — an explicitly selected but UNCONFIGURED pack is still
        # skipped because it has no trustworthy rules to run).
        for pack_id in explicit_pack_ids or []:
            requested = by_id.get(pack_id)
            if requested is None:
                raise PackResolutionError(
                    f"Requested reference pack '{pack_id}' is not available."
                )
            if requested.manifest.status not in _INACTIVE_STATUSES:
                selected[requested.manifest.pack_id] = requested

        # 2) Auto-detection from document citations.
        index = self._by_match_key(available)
        for citation in detected_citations:
            matched = index.get(_match_key(citation))
            if matched is not None and matched.manifest.status not in _INACTIVE_STATUSES:
                selected[matched.manifest.pack_id] = matched

        return list(selected.values())


def resolve_active_packs(
    detected_citations: list[str],
    explicit_pack_ids: list[str] | None = None,
    tenant_id: str | None = None,
) -> list[ReferencePack]:
    """Module-level convenience wrapper around the default :class:`PackResolver`."""
    return PackResolver().resolve_active_packs(
        detected_citations, explicit_pack_ids=explicit_pack_ids, tenant_id=tenant_id
    )


def prefix_rule_ids(
    pack: ReferencePack,
    tenant_id: str | None = None,
) -> list[tuple[str, ReferenceRule]]:
    """Return the pack's rules keyed by globally unique prefixed IDs.

    System packs use ``sys:{pack_id}:{rule_id}``; tenant custom packs use
    ``usr:{tenant_id}:{pack_id}:{rule_id}`` so rule IDs from different packs
    (or duplicate uploads from different tenants) can never collide.
    """
    prefix = (
        f"usr:{tenant_id}:{pack.manifest.pack_id}"
        if tenant_id
        else f"sys:{pack.manifest.pack_id}"
    )
    return [(f"{prefix}:{rule.rule_id}", rule) for rule in pack.rules]
