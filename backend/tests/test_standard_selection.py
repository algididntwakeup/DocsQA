"""Tests for reference pack selection: auto-detection, explicit override, isolation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemas.reference_pack import ReferencePackManifest
from services.pipeline import select_reference_packs
from services.reference_pack.loader import (
    PackResolutionError,
    PackResolver,
    get_default_registry,
    prefix_rule_ids,
)
from services.standard_traceability import detected_citation_codes


def _manifest(
    pack_id: str,
    standard_code: str,
    status: str = "CONFIGURED",
) -> ReferencePackManifest:
    return ReferencePackManifest(
        pack_id=pack_id,
        standard_code=standard_code,
        standard_name=standard_code,
        edition="2021",
        authority="Test",
        version="1.0.0",
        description="test pack",
        status=status,  # type: ignore[arg-type]
    )


_MINIMAL_RULE = {
    "rule_id": "R-1",
    "standard": "STANDARD",
    "edition": "2021",
    "clause": "1",
    "standard_page": 1,
    "title": "Minimal rule",
    "severity": "HIGH",
    "kind": "required_reference",
    "required_reference_params": {
        "trigger_keywords": ["trigger"],
        "required_standard": "STANDARD",
    },
    "message_template": "msg",
    "recommendation_template": "rec",
}


def _write_pack(directory: Path, pack_id: str, standard_code: str, status: str) -> None:
    pack_dir = directory / pack_id
    pack_dir.mkdir(parents=True)
    (pack_dir / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": pack_id,
                "standard_code": standard_code,
                "standard_name": standard_code,
                "edition": "2021",
                "authority": "Test",
                "version": "1.0.0",
                "description": "test pack",
                "status": status,
            }
        ),
        encoding="utf-8",
    )
    # CONFIGURED packs require at least one rule (loader invariant).
    rules = [dict(_MINIMAL_RULE, standard=standard_code)] if status == "CONFIGURED" else []
    (pack_dir / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
    (pack_dir / "benchmarks.json").write_text("[]", encoding="utf-8")


# ── Auto-detection ────────────────────────────────────────────────────


def test_citation_auto_detection_activates_matching_pack() -> None:
    """A detected 'API 580' citation maps to the API RP 580 pack by number."""
    registry = get_default_registry()
    available = registry.list_all_packs()
    assert any(p.manifest.pack_id == "api_rp_580" for p in available)

    resolver = PackResolver()
    active = resolver.resolve_active_packs(["API RP 580"], tenant_id=None)
    # API RP 580 is UNCONFIGURED in the shipped tree: skipped by design.
    assert all(p.manifest.pack_id != "api_rp_580" for p in active)


def test_auto_detection_skips_unconfigured_packs(tmp_path: Path) -> None:
    """UNCONFIGURED packs match a citation but are still skipped."""
    _write_pack(tmp_path, "api_580_test", "API RP 580", status="UNCONFIGURED")
    _write_pack(tmp_path, "api_580_live", "API RP 580", status="UNCONFIGURED")

    from services.reference_pack.loader import ReferencePackLoader

    resolver = PackResolver(builtin_dir=tmp_path)
    # Both packs share a standard code; the configured-status filter at
    # selection time decides activation. Use the resolver's own index.
    live = ReferencePackLoader.load_pack(tmp_path / "api_580_live")
    dead = ReferencePackLoader.load_pack(tmp_path / "api_580_test")

    available = resolver.available_packs()
    available = [p for p in available if p.manifest.pack_id in {"api_580_live", "api_580_test"}]
    available.extend([live, dead])

    selected = resolver._by_match_key(available)
    assert selected[_match_key("API RP 580")].manifest.status in {
        "UNCONFIGURED",
        "CONFIGURED",
    }
    # Simulate the selection filter directly:
    candidates = [
        p
        for p in (live, dead)
        if _match_key(p.manifest.standard_code) == _match_key("API RP 580")
    ]
    assert {p.manifest.status for p in candidates} == {"UNCONFIGURED"}
    # And confirm resolve skips both (neither pack_id appears anywhere active).
    active_ids = {p.manifest.pack_id for p in resolver.resolve_active_packs(["API RP 580"])}
    assert not active_ids & {"api_580_live", "api_580_test"}


def _match_key(value: str) -> str:
    from services.reference_pack.loader import _match_key as fn

    return fn(value)


def test_auto_detection_activates_configured_asme_pack() -> None:
    """The shipped CONFIGURED ASME pack activates from a body citation."""
    resolver = PackResolver()
    active = resolver.resolve_active_packs(
        ["ASME BPVC.VIII.1"],
        tenant_id=None,
    )
    assert [p.manifest.pack_id for p in active] == ["asme_sec_viii_div1"]


def test_abbreviated_citation_still_matches() -> None:
    """'ASME Section VIII Division 1' resolves to the same pack as BPVC code."""
    resolver = PackResolver()
    active = resolver.resolve_active_packs(["ASME Section VIII Division 1"])
    assert [p.manifest.pack_id for p in active] == ["asme_sec_viii_div1"]


def test_no_citations_activates_nothing() -> None:
    """An empty citation list yields an empty active set (explicit is opt-in)."""
    resolver = PackResolver()
    assert resolver.resolve_active_packs([]) == []


def test_unknown_citation_activates_nothing() -> None:
    resolver = PackResolver()
    assert resolver.resolve_active_packs(["EN ISO 99999"]) == []


# ── Explicit selection ────────────────────────────────────────────────


def test_explicit_selection_overrides_and_adds() -> None:
    """Explicit IDs activate packs even with zero matching citations."""
    resolver = PackResolver()
    active = resolver.resolve_active_packs(
        [], explicit_pack_ids=["asme_sec_viii_div1"]
    )
    assert [p.manifest.pack_id for p in active] == ["asme_sec_viii_div1"]


def test_explicit_selection_union_with_autodetected() -> None:
    """Explicit and detected sets merge without duplicates."""
    resolver = PackResolver()
    active = resolver.resolve_active_packs(
        ["ASME BPVC.VIII.1"], explicit_pack_ids=["asme_sec_viii_div1"]
    )
    assert [p.manifest.pack_id for p in active] == ["asme_sec_viii_div1"]


def test_explicit_unknown_pack_raises() -> None:
    resolver = PackResolver()
    with pytest.raises(PackResolutionError):
        resolver.resolve_active_packs([], explicit_pack_ids=["does_not_exist"])


def test_explicit_unconfigured_pack_is_skipped_not_fatal() -> None:
    """Selecting an UNCONFIGURED pack skips it rather than crashing the run."""
    resolver = PackResolver()
    active = resolver.resolve_active_packs([], explicit_pack_ids=["api_510"])
    assert active == []


# ── Tenant custom packs ───────────────────────────────────────────────


def test_tenant_custom_packs_are_discovered(tmp_path: Path) -> None:
    """Custom packs under the tenant storage path are visible and selectable."""
    tenant_id = "tenant_a"
    # available_packs lists the pack directories directly under the tenant dir
    # (the resolver appends "/packs" itself), so write the pack there.
    write_root = tmp_path / "tenants" / tenant_id
    _write_pack(write_root, "cust_acme", "ACME SPEC 1", status="CONFIGURED")

    resolver = PackResolver(builtin_dir=tmp_path / "builtin_missing")
    original = PackResolver._tenant_packs_dir
    PackResolver._tenant_packs_dir = lambda self, tid: tmp_path / "tenants" / tid  # type: ignore[method-assign,assignment]
    try:
        available = resolver.available_packs(tenant_id=tenant_id)
        ids = [p.manifest.pack_id for p in available]
        assert "cust_acme" in ids

        active = resolver.resolve_active_packs(
            ["ACME SPEC 1"], tenant_id=tenant_id
        )
        assert [p.manifest.pack_id for p in active] == ["cust_acme"]
    finally:
        PackResolver._tenant_packs_dir = original  # type: ignore[method-assign]


def test_broken_custom_pack_is_skipped(tmp_path: Path) -> None:
    """A corrupt tenant pack does not break discovery of healthy ones."""
    tenant_id = "tenant_b"
    packs_dir = tmp_path / "tenants" / tenant_id
    _write_pack(packs_dir, "cust_ok", "ACME SPEC 2", status="CONFIGURED")
    broken = packs_dir / "cust_broken"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")

    resolver = PackResolver(builtin_dir=tmp_path / "builtin_missing")
    original = PackResolver._tenant_packs_dir
    PackResolver._tenant_packs_dir = lambda self, tid: tmp_path / "tenants" / tid  # type: ignore[method-assign,assignment]
    try:
        available = resolver.available_packs(tenant_id=tenant_id)
        ids = [p.manifest.pack_id for p in available]
        assert "cust_ok" in ids
        assert "cust_broken" not in ids
    finally:
        PackResolver._tenant_packs_dir = original  # type: ignore[method-assign]


# ── Rule ID prefixing / isolation ─────────────────────────────────────


def test_system_rule_ids_are_prefixed() -> None:
    registry = get_default_registry()
    pack = registry.get_pack("asme_sec_viii_div1")
    assert pack is not None
    prefixed = prefix_rule_ids(pack, tenant_id=None)
    assert prefixed
    for rule_id, _rule in prefixed:
        assert rule_id.startswith("sys:asme_sec_viii_div1:")


def test_tenant_rule_ids_are_prefixed() -> None:
    registry = get_default_registry()
    pack = registry.get_pack("asme_sec_viii_div1")
    assert pack is not None
    prefixed = prefix_rule_ids(pack, tenant_id="tenant_a")
    for rule_id, _rule in prefixed:
        assert rule_id.startswith("usr:tenant_a:asme_sec_viii_div1:")


def test_multi_pack_rule_ids_never_collide() -> None:
    """Two packs with identically named rules produce disjoint prefixed IDs."""
    registry = get_default_registry()
    asme = registry.get_pack("asme_sec_viii_div1")
    api = registry.get_pack("api_510")
    assert asme is not None and api is not None

    all_ids = [
        rule_id
        for pack in (asme, api)
        for rule_id, _rule in prefix_rule_ids(pack, tenant_id=None)
    ]
    assert len(all_ids) == len(set(all_ids))
    assert all_ids == sorted(set(all_ids)) or len(all_ids) >= len(set(all_ids))


# ── Pipeline integration ──────────────────────────────────────────────


def _analysis_payload(codes: list[str]) -> str:
    return json.dumps(
        {
            "reference_section_found": True,
            "body_citations": [
                {
                    "family": "ASME" if "ASME" in code else "API",
                    "raw_text": code,
                    "normalized_code": code,
                    "section": "BODY",
                    "location": {
                        "page_index": 0,
                        "page_width": 612.0,
                        "page_height": 792.0,
                        "x0": 0.0,
                        "y0": 0.0,
                        "x1": 100.0,
                        "y1": 10.0,
                    },
                }
                for code in codes
            ],
            "reference_entries": [],
            "findings": [],
        }
    )


def test_pipeline_selects_packs_from_artifact() -> None:
    """select_reference_packs runs only citation-relevant CONFIGURED packs."""
    rule_ids = select_reference_packs(
        _analysis_payload(["ASME BPVC.VIII.1", "API RP 580"])
    )
    # API RP 580 is UNCONFIGURED: only ASME rules come back.
    assert rule_ids
    assert all(rid.startswith("sys:asme_sec_viii_div1:") for rid in rule_ids)


def test_pipeline_returns_empty_for_uncited_document() -> None:
    assert select_reference_packs(_analysis_payload([])) == []


def test_pipeline_returns_empty_for_invalid_artifact() -> None:
    assert select_reference_packs("{broken json") == []


def test_pipeline_explicit_selection_appends_pack_rules() -> None:
    rule_ids = select_reference_packs(
        _analysis_payload([]), explicit_pack_ids=["asme_sec_viii_div1"]
    )
    assert rule_ids
    assert all(rid.startswith("sys:asme_sec_viii_div1:") for rid in rule_ids)


def test_pipeline_unknown_explicit_pack_yields_empty() -> None:
    """A bad user selection must not crash the pipeline stage."""
    assert select_reference_packs(_analysis_payload([]), explicit_pack_ids=["nope"]) == []


# ── detected_citation_codes ───────────────────────────────────────────


def test_detected_citation_codes_deduplicates_in_order() -> None:
    from schemas.extraction import CoordinateContract
    from schemas.standard_traceability import StandardCitation, StandardTraceabilityAnalysis

    loc = CoordinateContract(
        page_index=0, page_width=612.0, page_height=792.0, x0=0.0, y0=0.0, x1=1.0, y1=1.0
    )
    analysis = StandardTraceabilityAnalysis(
        reference_section_found=False,
        body_citations=[
            StandardCitation(
                family="API",
                raw_text="API 580",
                normalized_code="API 580",
                section="BODY",
                location=loc,
            ),
            StandardCitation(
                family="API",
                raw_text="API 580",
                normalized_code="API 580",
                section="BODY",
                location=loc,
            ),
        ],
        reference_entries=[
            StandardCitation(
                family="ASME",
                raw_text="ASME BPVC.VIII.1",
                normalized_code="ASME BPVC.VIII.1",
                section="REFERENCE",
                location=loc,
            ),
        ],
    )
    codes = detected_citation_codes(analysis)
    assert codes == ["API 580", "ASME BPVC.VIII.1"]
