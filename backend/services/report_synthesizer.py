"""Deterministic narrative synthesis for executive review reports."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from domain.enums import ReportLanguage
from services.report_locale import get_report_strings


def _value(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


class ReportSynthesizer:
    """Turn normalized findings into concise, repeatable report prose and tables."""

    def __init__(self, language: ReportLanguage = ReportLanguage.ENGLISH) -> None:
        self.s = get_report_strings(language)

    def generate_summary_judgement(self, findings: Iterable[Any], scorecard: Any, metadata: Any) -> str:
        findings_list = list(findings)
        arithmetic = sum("MATH" in str(_value(i, "type")).upper() or "ARITH" in str(_value(i, "type")).upper() for i in findings_list)
        structural = sum(any(t in (str(_value(i, "type")) + " " + str(_value(i, "message"))).upper() for t in ("TOC", "NAVIGATION", "UNCONTROLLED", "REFERENCE")) for i in findings_list)
        total = len(findings_list)
        title = _value(metadata, "document_reviewed", "the reviewed document")
        baseline = _value(scorecard, "baseline_score", "")
        if self.s is get_report_strings(ReportLanguage.ENGLISH):
            return "\n\n".join([f"The review of {title} identified {total} normalized finding(s). Arithmetic and count integrity signals: {arithmetic}; the report should preserve any reconciled totals while correcting confirmed exceptions.", f"Structural and navigation signals: {structural}, including table-of-contents, uncontrolled-page, or reference closure issues where detected. The Budinski baseline score is {baseline} where available.", "Closure status is determined by the blocking findings and the reviewer’s inclusion choices; a reissue should not proceed until critical blockers are resolved."])
        return "\n\n".join([f"Tinjauan atas {title} mengidentifikasi {total} temuan ternormalisasi. Sinyal integritas aritmetika dan jumlah: {arithmetic}; laporan harus mempertahankan total yang telah direkonsiliasi sambil memperbaiki pengecualian yang terkonfirmasi.", f"Sinyal struktur dan navigasi: {structural}, termasuk masalah daftar isi, halaman tidak terkendali, atau penutupan referensi jika terdeteksi. Nilai dasar Budinski adalah {baseline} jika tersedia.", "Status penutupan ditentukan oleh temuan penghalang dan pilihan penyertaan peninjau; penerbitan ulang tidak boleh dilakukan sebelum penghalang kritis diselesaikan."])

    def generate_bottom_line(self, blockers: Iterable[Any]) -> str:
        first = next(iter(blockers), None)
        if first is None:
            return "Tidak ada temuan penghalang; tutup temuan yang tersisa pada tinjauan terkendali berikutnya." if self.s.bottom_line != "BOTTOM LINE" else "No blocking finding was identified; close the remaining findings in the next controlled review."
        title = _value(first, "title", _value(first, "finding", "the critical blocker"))
        fix = _value(first, "what_would_fix_it", "resolve the finding and verify the evidence")
        return f"Selesaikan {title} sebelum penerbitan ulang: {fix}." if self.s.bottom_line != "BOTTOM LINE" else f"Resolve {title} before reissue: {fix}."

    def synthesize_blocker_groups(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        groups: dict[str, list[Any]] = {}
        for finding in findings:
            groups.setdefault(str(_value(finding, "category", "FINDING")).upper(), []).append(finding)
        summaries = []
        for category, items in groups.items():
            types: dict[str, int] = {}
            for item in items:
                typ = str(_value(item, "type", "FINDING")).upper(); types[typ] = types.get(typ, 0) + 1
            breakdown = ", ".join(f"{n} {typ.replace('_', ' ').lower()}" for typ, n in sorted(types.items()))
            codes = ", ".join(sorted(types)); pages = sorted({str(_value(i, "page_number", "")) for i in items if _value(i, "page_number", None) is not None}, key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else v))
            page_text = ", ".join(pages[:12]) if pages else ("the affected document locations" if self.s.bottom_line == "BOTTOM LINE" else "lokasi dokumen terdampak")
            if len(pages) > 12: page_text += f", and {len(pages)-12} more pages" if self.s.bottom_line == "BOTTOM LINE" else f", dan {len(pages)-12} halaman lainnya"
            labels = [str((_value(i, "evidence", {}) or {}).get("label")) for i in items if (_value(i, "evidence", {}) or {}).get("label")]
            example = f" Examples include {', '.join(labels[:5])}." if labels and self.s.bottom_line == "BOTTOM LINE" else (f" Contoh meliputi {', '.join(labels[:5])}." if labels else "")
            if self.s.bottom_line == "BOTTOM LINE":
                message = f"The review identified {len(items)} related finding(s) ({breakdown}) on printed page(s) {page_text}. Finding code(s): {codes}.{example} These findings represent one recurring control issue, not separate independent blockers; correct the underlying document-control mechanism and verify the complete set before reissue."
                suggestion = str(_value(items[0], "suggestion", "Correct the underlying control and verify all affected pages."))
            else:
                message = f"Tinjauan mengidentifikasi {len(items)} temuan terkait ({breakdown}) pada halaman cetak {page_text}. Kode temuan: {codes}.{example} Temuan ini merupakan satu masalah pengendalian berulang, bukan penghalang independen; perbaiki mekanisme pengendalian dokumen dan verifikasi seluruh set sebelum penerbitan ulang."
                suggestion = str(_value(items[0], "suggestion", "Perbaiki pengendalian dan verifikasi semua halaman terdampak."))
            summaries.append({"type": category or "FINDINGS", "finding_codes": codes, "category": category, "count": str(len(items)), "message": message, "suggestion": suggestion})
        return summaries

    def synthesize_praise(self, doc_sections: Any, findings: Iterable[Any]) -> list[str]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        praise = []
        if sections.get("arithmetic_reconciles"): praise.append("Arithmetic and count totals reconcile across the checked tables." if self.s.bottom_line == "BOTTOM LINE" else "Total aritmetika dan jumlah selaras di seluruh tabel yang diperiksa.")
        if sections.get("priority_rules_explicit"): praise.append("Priority rules are explicit and can be audited independently." if self.s.bottom_line == "BOTTOM LINE" else "Aturan prioritas dinyatakan jelas dan dapat diaudit secara independen.")
        if sections.get("assumptions"): praise.append("Assumptions are recorded explicitly for review and reuse." if self.s.bottom_line == "BOTTOM LINE" else "Asumsi dicatat secara eksplisit untuk tinjauan dan penggunaan ulang.")
        return praise or (["The report provides a traceable basis for the findings and requested corrections."] if self.s.bottom_line == "BOTTOM LINE" else ["Laporan menyediakan dasar yang dapat dilacak untuk temuan dan perbaikan yang diminta."])

    def generate_demonstration_rewrite(self, sections: Any, findings: Iterable[Any]) -> dict[str, Any]:
        raw = sections.get("conclusions", "") if isinstance(sections, dict) else getattr(sections, "conclusions", "")
        text = " ".join(raw) if isinstance(raw, list) else str(raw)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        return {"section_title": "Conclusions" if self.s.bottom_line == "BOTTOM LINE" else "Kesimpulan", "as_written": text or self.s.no_conclusion_text, "demonstration": [sentence.rstrip(".") + "." for sentence in sentences[:8]]}

    def synthesize_baseline_measures(self, doc_sections: Any, findings: Iterable[Any]) -> list[dict[str, str]]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        checks = [("Purpose distinct from objective", bool(sections.get("purpose_of_report_stated")), self.s.default_measure_purpose), ("Procedure repeatable", bool(sections.get("procedure_repeatable", True)), self.s.default_measure_procedure), ("Conclusions are conclusions", bool(sections.get("conclusions_valid", True)), self.s.default_measure_conclusions), ("Recommendations actionable", bool(sections.get("recommendations_actionable", True)), self.s.default_measure_recommendations)]
        return [{"measure": n, "result": "PASS" if ok else "FAIL", "reason": reason} for n, ok, reason in checks]

    def synthesize_blockers(self, blockers: Iterable[Any]) -> list[dict[str, str]]:
        fields = ("where_location", "what_it_says", "what_body_has", "why_it_matters", "what_would_fix_it")
        return [{label.replace("_", " ").title(): str(_value(item, label)) for label in fields} for item in blockers]

    def synthesize_major_findings(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        selected = []
        for item in findings:
            text = (str(_value(item, "type")) + " " + str(_value(item, "message"))).upper()
            if any(token in text for token in ("TOC", "NAVIGATION", "UNCONTROLLED", "BIBLIO", "DUPLICATE", "DEFINITION")): selected.append(item)
        return [{"#": str(i), "FINDING": str(_value(item, "message", _value(item, "finding"))), "WHAT WOULD FIX IT": str(_value(item, "suggestion", "Correct, verify, and reissue the affected section."))} for i, item in enumerate(selected, 1)]

    def synthesize_language_mechanics(self, minor_findings: Iterable[Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []; seen: set[tuple[str, str, str]] = set()
        for item in minor_findings:
            evidence = _value(item, "evidence", {}) or {}; page = str(_value(evidence, "page", _value(item, "page", "—"))); original = str(_value(evidence, "original_text", _value(item, "message", ""))); suggested = str(_value(evidence, "suggestion", _value(item, "suggested", "Review wording."))); key = (page, original, suggested)
            if key not in seen: seen.add(key); rows.append({"PAGE": page, "AS WRITTEN": original, "SUGGESTED": suggested})
        return rows
