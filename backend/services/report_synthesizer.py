"""Deterministic narrative synthesis for executive review reports."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from domain.enums import ReportLanguage
from services.report_locale import get_report_strings

TYPE_TRANSLATIONS_ID: dict[str, str] = {
    "UNCONTROLLED_PAGE": "halaman tidak terkendali",
    "RUNNING_FOOTER": "header/footer dokumen",
    "MISSING_DOCUMENT_NUMBER": "nomor dokumen hilang",
    "DOCUMENT_NUMBER_MISSING": "nomor dokumen tidak tercantum",
    "TOC_DRIFT": "pergeseran daftar isi",
    "REFERENCE_DRIFT": "pergeseran referensi",
    "CROSS_PAGE_BREAK": "pemotongan lintas halaman",
    "TABLE_MATH_MISMATCH": "ketidaksesuaian hitungan tabel",
    "SPELLING_ERROR": "kesalahan ejaan",
    "TYPO": "salah ketik",
    "GRAMMAR": "tata bahasa",
}


def _value(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _excerpt(item: Any) -> str:
    evidence = _value(item, "evidence", {}) or {}
    if isinstance(evidence, dict):
        for key in ("original_text", "excerpt", "what_it_says", "text", "label"):
            if evidence.get(key):
                return str(evidence[key]).strip()
    return str(_value(item, "message", "")).strip()


def _page_range(pages: list[str]) -> str:
    numbers = sorted({int(page) for page in pages if page.isdigit()})
    if not numbers:
        return ", ".join(pages[:12])
    ranges: list[str] = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number != previous + 1:
            ranges.append(str(start) if start == previous else f"{start}-{previous}")
            start = number
        previous = number
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


class ReportSynthesizer:
    """Turn normalized findings into concise, repeatable report prose and tables."""

    def __init__(self, language: ReportLanguage = ReportLanguage.ENGLISH) -> None:
        self.language = language
        self.s = get_report_strings(language)

    @property
    def is_english(self) -> bool:
        return self.language == ReportLanguage.ENGLISH

    def generate_summary_judgement(
        self, findings: Iterable[Any], scorecard: Any, metadata: Any
    ) -> str:
        findings_list = list(findings)
        arithmetic = sum(
            "MATH" in str(_value(i, "type")).upper() or "ARITH" in str(_value(i, "type")).upper()
            for i in findings_list
        )
        structural = sum(
            any(
                t in (str(_value(i, "type")) + " " + str(_value(i, "message"))).upper()
                for t in ("TOC", "NAVIGATION", "UNCONTROLLED", "REFERENCE")
            )
            for i in findings_list
        )
        total = len(findings_list)
        fallback_title = "the reviewed document" if self.is_english else "dokumen yang ditinjau"
        title = _value(metadata, "document_reviewed", fallback_title) or fallback_title
        headings = _value(metadata, "section_headings", []) or []
        heading_text = (
            ", ".join(str(item) for item in headings[:4])
            if isinstance(headings, list)
            else str(headings)
        )
        evidence = [
            str(_value(item, "message")) for item in findings_list if _value(item, "message")
        ]
        fallback_evidence = (
            "no finding message was persisted"
            if self.is_english
            else "tidak ada pesan temuan yang tersimpan"
        )
        evidence_text = evidence[0] if evidence else fallback_evidence
        baseline = _value(scorecard, "baseline_score", "")
        if self.is_english:
            context = f" Extracted sections include {heading_text}." if heading_text else ""
            return "\n\n".join(
                [
                    (
                        f"The review of {title} identified {total} normalized finding(s). "
                        f"Arithmetic and count integrity signals: {arithmetic}; the report "
                        "should preserve any reconciled totals while correcting confirmed "
                        f"exceptions.{context}"
                    ),
                    (
                        f"Structural and navigation signals: {structural}, including "
                        "table-of-contents, uncontrolled-page, or reference closure issues "
                        f"where detected. The Budinski baseline score is {baseline} where "
                        f"available. Extracted evidence begins: {evidence_text}."
                    ),
                    (
                        "Closure status is determined by the blocking findings and the "
                        "reviewer’s inclusion choices; a reissue should not proceed until "
                        "critical blockers are resolved."
                    ),
                ]
            )
        context = f" Bagian yang diekstrak meliputi {heading_text}." if heading_text else ""
        return "\n\n".join(
            [
                (
                    f"Tinjauan atas {title} mengidentifikasi {total} temuan ternormalisasi. "
                    f"Sinyal integritas aritmetika dan jumlah: {arithmetic}; laporan harus "
                    "mempertahankan total yang telah direkonsiliasi sambil memperbaiki "
                    f"pengecualian yang terkonfirmasi.{context}"
                ),
                (
                    f"Sinyal struktur dan navigasi: {structural}, termasuk masalah daftar "
                    "isi, halaman tidak terkendali, atau penutupan referensi jika terdeteksi. "
                    f"Nilai dasar Budinski adalah {baseline} jika tersedia. Bukti ekstraksi "
                    f"dimulai: {evidence_text}."
                ),
                (
                    "Status penutupan ditentukan oleh temuan penghalang dan pilihan "
                    "penyertaan peninjau; penerbitan ulang tidak boleh dilakukan sebelum "
                    "penghalang kritis diselesaikan."
                ),
            ]
        )

    def generate_bottom_line(self, blockers: Iterable[Any]) -> str:
        first = next(iter(blockers), None)
        if first is None:
            return (
                "No blocking finding was identified; close the remaining findings in the "
                "next controlled review."
                if self.is_english
                else (
                    "Tidak ada temuan penghalang; tutup temuan yang tersisa pada tinjauan "
                    "terkendali berikutnya."
                )
            )
        fallback_title = "the critical blocker" if self.is_english else "penghalang kritis"
        fallback_fix = (
            "resolve the finding and verify the evidence"
            if self.is_english
            else "selesaikan temuan dan verifikasi bukti"
        )
        title = _value(first, "title", _value(first, "finding", fallback_title))
        fix = _value(first, "what_would_fix_it", fallback_fix)
        return (
            f"Resolve {title} before reissue: {fix}."
            if self.is_english
            else f"Selesaikan {title} sebelum penerbitan ulang: {fix}."
        )

    def synthesize_blocker_groups(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        groups: dict[str, list[Any]] = {}
        for finding in findings:
            groups.setdefault(str(_value(finding, "category", "FINDING")).upper(), []).append(
                finding
            )
        summaries = []
        for category, items in groups.items():
            types: dict[str, int] = {}
            for item in items:
                typ = str(_value(item, "type", "FINDING")).upper()
                types[typ] = types.get(typ, 0) + 1

            if self.is_english:
                breakdown = ", ".join(
                    f"{n} {typ.replace('_', ' ').lower()}" for typ, n in sorted(types.items())
                )
            else:
                breakdown = ", ".join(
                    f"{n} {TYPE_TRANSLATIONS_ID.get(typ, typ.replace('_', ' ').lower())}"
                    for typ, n in sorted(types.items())
                )

            codes = ", ".join(sorted(types))
            pages = sorted(
                {
                    str(_value(i, "page_number", ""))
                    for i in items
                    if _value(i, "page_number", None) is not None
                },
                key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else v),
            )
            page_text = (
                _page_range(pages)
                if pages
                else (
                    "the affected document locations"
                    if self.is_english
                    else "lokasi dokumen terdampak"
                )
            )
            if len(pages) > 12:
                page_text += (
                    f", and {len(pages) - 12} more pages"
                    if self.is_english
                    else f", dan {len(pages) - 12} halaman lainnya"
                )
            labels = [
                str((_value(i, "evidence", {}) or {}).get("label"))
                for i in items
                if (_value(i, "evidence", {}) or {}).get("label")
            ]
            examples = [_excerpt(i) for i in items if _excerpt(i)]
            example = (
                f" Examples include {', '.join(labels[:5])}."
                if labels and self.is_english
                else (f" Contoh meliputi {', '.join(labels[:5])}." if labels else "")
            )
            if self.is_english:
                message = (
                    f"The review identified {len(items)} related finding(s) ({breakdown}) "
                    f"on printed page(s) {page_text}. Finding code(s): {codes}.{example} "
                    "These findings represent one recurring control issue, not separate "
                    "independent blockers."
                )
                suggestion = str(
                    _value(
                        items[0],
                        "suggestion",
                        "Correct the underlying control and verify all affected pages.",
                    )
                )
            else:
                message = (
                    f"Tinjauan mengidentifikasi {len(items)} temuan terkait ({breakdown}) "
                    f"pada halaman cetak {page_text}. Kode temuan: {codes}.{example} "
                    "Temuan ini merupakan satu masalah pengendalian berulang, bukan "
                    "penghalang independen."
                )
                suggestion = str(
                    _value(
                        items[0],
                        "suggestion",
                        "Perbaiki pengendalian dan verifikasi semua halaman terdampak.",
                    )
                )
            summaries.append(
                {
                    "type": category or ("FINDINGS" if self.is_english else "TEMUAN"),
                    "finding_codes": codes,
                    "category": category,
                    "count": str(len(items)),
                    "message": message,
                    "suggestion": suggestion,
                    "excerpt": examples[0] if examples else "",
                }
            )
        return summaries

    def generate_recommendations(self, findings: Iterable[Any], limit: int = 5) -> list[str]:
        """Return unique, concrete correction actions for the executive summary."""
        recommendations: list[str] = []
        seen: set[str] = set()
        for item in findings:
            issue_type = str(_value(item, "type", "finding")).upper()
            default = {
                "UNCONTROLLED_PAGE": self.s.rec_uncontrolled_page,
                "CROSS_PAGE_BREAK": self.s.rec_cross_page_break,
                "REFERENCE_DRIFT": self.s.rec_reference_drift,
            }.get(
                issue_type,
                self.s.rec_default,
            )
            # Use a persisted suggestion only when it matches the target language;
            # otherwise fall back to the clean localized default to avoid mixed language.
            persisted_suggestion = str(_value(item, "suggestion", "")).strip()
            if persisted_suggestion:
                # Check if persisted suggestion has obvious other-language keywords
                if (
                    self.is_english
                    and any(
                        w in persisted_suggestion.lower()
                        for w in ("perbaiki", "terapkan", "perbarui", "halaman")
                    )
                    or not self.is_english
                    and any(
                        w in persisted_suggestion.lower()
                        for w in ("apply", "correct", "verify", "update")
                    )
                ):
                    action = default
                else:
                    action = persisted_suggestion
            else:
                action = default

            if action and action not in seen:
                seen.add(action)
                recommendations.append(action)
            if len(recommendations) >= limit:
                break
        return recommendations

    def synthesize_actionable_findings(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        """Create compact rows with source excerpt and a concrete correction."""
        rows: list[dict[str, str]] = []
        for item in findings:
            issue_type = str(_value(item, "type", "FINDING")).upper()
            excerpt = _excerpt(item)
            suggestion = str(
                _value(
                    item,
                    "suggestion",
                    self.s.action_default,
                )
            )
            page = str(
                _value(item, "page_number", "")
                or (_value(item, "evidence", {}) or {}).get("page", "—")
            )
            location = (
                f"{self.s.page_prefix} {page}"
                if page not in {"", "None", "—"}
                else self.s.not_located
            )
            rows.append(
                {
                    "location": location,
                    "type": issue_type,
                    "excerpt": excerpt,
                    "action": suggestion,
                }
            )
        return rows

    def synthesize_praise(self, doc_sections: Any, findings: Iterable[Any]) -> list[str]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        praise = []
        if sections.get("arithmetic_reconciles"):
            praise.append(
                "Arithmetic and count totals reconcile across the checked tables."
                if self.is_english
                else "Total aritmetika dan jumlah selaras di seluruh tabel yang diperiksa."
            )
        if sections.get("priority_rules_explicit"):
            praise.append(
                "Priority rules are explicit and can be audited independently."
                if self.is_english
                else "Aturan prioritas dinyatakan jelas dan dapat diaudit secara independen."
            )
        if sections.get("assumptions"):
            praise.append(
                "Assumptions are recorded explicitly for review and reuse."
                if self.is_english
                else "Asumsi dicatat secara eksplisit untuk tinjauan dan penggunaan ulang."
            )
        return praise or (
            ["The report provides a traceable basis for the findings and requested corrections."]
            if self.is_english
            else [
                "Laporan menyediakan dasar yang dapat dilacak untuk temuan dan "
                "perbaikan yang diminta."
            ]
        )

    def generate_demonstration_rewrite(
        self, sections: Any, findings: Iterable[Any]
    ) -> dict[str, Any]:
        raw = (
            sections.get("conclusions", "")
            if isinstance(sections, dict)
            else getattr(sections, "conclusions", "")
        )
        text = " ".join(raw) if isinstance(raw, list) else str(raw)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        return {
            "section_title": "Conclusions" if self.is_english else "Kesimpulan",
            "as_written": text or self.s.no_conclusion_text,
            "demonstration": [sentence.rstrip(".") + "." for sentence in sentences[:8]],
        }

    def synthesize_baseline_measures(
        self, doc_sections: Any, findings: Iterable[Any]
    ) -> list[dict[str, str]]:
        sections = doc_sections if isinstance(doc_sections, dict) else vars(doc_sections)
        checks = [
            (
                self.s.measure_purpose_name,
                bool(sections.get("purpose_of_report_stated")),
                self.s.default_measure_purpose,
            ),
            (
                self.s.measure_procedure_name,
                bool(sections.get("procedure_repeatable", True)),
                self.s.default_measure_procedure,
            ),
            (
                self.s.measure_conclusions_name,
                bool(sections.get("conclusions_valid", True)),
                self.s.default_measure_conclusions,
            ),
            (
                self.s.measure_recommendations_name,
                bool(sections.get("recommendations_actionable", True)),
                self.s.default_measure_recommendations,
            ),
        ]
        return [
            {
                "measure": n,
                "result": self.s.outcome_pass if ok else self.s.outcome_fail,
                "reason": reason,
            }
            for n, ok, reason in checks
        ]

    def synthesize_blockers(self, blockers: Iterable[Any]) -> list[dict[str, str]]:
        field_keys = [
            ("where_location", self.s.where),
            ("what_it_says", self.s.what_it_says),
            ("what_body_has", self.s.what_body_has),
            ("why_it_matters", self.s.why_it_matters),
            ("what_would_fix_it", self.s.what_would_fix_it),
        ]
        return [{label: str(_value(item, attr)) for attr, label in field_keys} for item in blockers]

    def synthesize_major_findings(self, findings: Iterable[Any]) -> list[dict[str, str]]:
        selected = []
        for item in findings:
            text = (str(_value(item, "type")) + " " + str(_value(item, "message"))).upper()
            if any(
                token in text
                for token in (
                    "TOC",
                    "NAVIGATION",
                    "UNCONTROLLED",
                    "BIBLIO",
                    "DUPLICATE",
                    "DEFINITION",
                )
            ):
                selected.append(item)
        return [
            {
                self.s.no: str(i),
                self.s.finding.upper(): str(_value(item, "message", _value(item, "finding"))),
                self.s.what_would_fix_it.upper(): str(
                    _value(item, "suggestion", self.s.fix_reissue_default)
                ),
            }
            for i, item in enumerate(selected, 1)
        ]

    def synthesize_language_mechanics(self, minor_findings: Iterable[Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in minor_findings:
            evidence = _value(item, "evidence", {}) or {}
            page = str(_value(evidence, "page", _value(item, "page", "—")))
            original = str(_value(evidence, "original_text", _value(item, "message", "")))
            suggested = str(
                _value(evidence, "suggestion", _value(item, "suggested", self.s.review_wording))
            )
            key = (page, original, suggested)
            if key not in seen:
                seen.add(key)
                rows.append(
                    {
                        self.s.page.upper(): page,
                        self.s.as_written.upper(): original,
                        self.s.suggested.upper(): suggested,
                    }
                )
        return rows
