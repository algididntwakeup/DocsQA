"""Deterministic narrative synthesis for executive review reports."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from domain.enums import ReportLanguage
from services.report_locale import (
    get_report_strings,
    humanize_finding_message,
    humanize_finding_type,
)


def _value(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _excerpt(item: Any, language: ReportLanguage = ReportLanguage.ENGLISH) -> str:
    evidence = _value(item, "evidence", {}) or {}
    if isinstance(evidence, dict):
        for key in ("original_text", "excerpt", "what_it_says", "text", "label"):
            if evidence.get(key):
                return str(evidence[key]).strip()
    return _display_message(item, language)


def _display_message(item: Any, language: ReportLanguage) -> str:
    """Remove machine-code prefixes without altering ordinary source evidence."""
    return humanize_finding_message(
        str(_value(item, "message", "") or ""),
        str(_value(item, "type", "") or ""),
        language,
    )


def _natural_list(items: list[str], conjunction: str = "and") -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"


def _category_phrase(category: str, language: ReportLanguage) -> str:
    key = category.strip().upper()
    english = {
        "TRACEABILITY": "document-control",
        "DOCUMENT_CONTROL": "document-control",
        "LAYOUT": "layout",
        "CONSISTENCY": "consistency",
        "LINGUISTIC": "language and mechanics",
        "SPELLING": "language and mechanics",
        "GRAMMAR": "language and mechanics",
        "DICTIONARY": "language and mechanics",
        "BUDINSKI": "writing-quality",
        "STRUCTURAL": "structural",
    }
    indonesian = {
        "TRACEABILITY": "kendali dokumen",
        "DOCUMENT_CONTROL": "kendali dokumen",
        "LAYOUT": "tata letak",
        "CONSISTENCY": "konsistensi",
        "LINGUISTIC": "bahasa dan mekanika",
        "SPELLING": "bahasa dan mekanika",
        "GRAMMAR": "bahasa dan mekanika",
        "DICTIONARY": "bahasa dan mekanika",
        "BUDINSKI": "mutu penulisan",
        "STRUCTURAL": "struktur",
    }
    mapping = indonesian if language == ReportLanguage.INDONESIAN else english
    return mapping.get(key, humanize_finding_type(key, language=language).lower())


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
            _display_message(item, self.language)
            for item in findings_list
            if _display_message(item, self.language)
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
                        f"The review of {title} identified {total} normalized "
                        f"finding{'s' if total != 1 else ''}. "
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
        blockers_list = list(blockers)
        if not blockers_list:
            return (
                "No blocking finding was identified; close the remaining findings in the "
                "next controlled review."
                if self.is_english
                else (
                    "Tidak ada temuan penghalang; tutup temuan yang tersisa pada tinjauan "
                    "terkendali berikutnya."
                )
            )
        count = 0
        descriptions: list[str] = []
        for blocker in blockers_list:
            title = str(_value(blocker, "title", _value(blocker, "finding", "")))
            narrative = str(_value(blocker, "what_it_says", ""))
            descriptions.extend((title, narrative))
            count_match = re.search(r"\((\d+)\s+instances?\)", title, re.IGNORECASE)
            if not count_match:
                count_match = re.search(r"identified\s+(\d+)\b", narrative, re.IGNORECASE)
            count += int(count_match.group(1)) if count_match else 1

        description_text = " ".join(descriptions).casefold()
        if re.search(r"traceability|document[- ]control|uncontrolled|reference", description_text):
            issue_family = (
                "Critical Traceability and Control Discrepancies"
                if self.is_english
                else "Diskrepansi Kritis Ketertelusuran dan Kendali Dokumen"
            )
        elif re.search(r"arithmetic|summation|table math|rounding", description_text):
            issue_family = (
                "Critical Table Arithmetic Discrepancies"
                if self.is_english
                else "Diskrepansi Aritmetika Tabel yang Kritis"
            )
        else:
            issue_family = (
                "Critical Document Quality Discrepancies"
                if self.is_english
                else "Diskrepansi Mutu Dokumen yang Kritis"
            )
        if self.is_english:
            return f"Resolve {count} {issue_family} before document reissue."
        return f"Selesaikan {count} {issue_family} sebelum dokumen diterbitkan ulang."

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

            tally = [
                f"{count} {humanize_finding_type(typ, count=count, language=self.language)}"
                for typ, count in types.items()
            ]
            breakdown = _natural_list(tally, "and" if self.is_english else "dan")
            finding_labels = _natural_list(
                [humanize_finding_type(typ, language=self.language) for typ in types],
                "and" if self.is_english else "dan",
            )
            pages = sorted(
                {
                    str(_value(i, "page_number", ""))
                    for i in items
                    if _value(i, "page_number", None) is not None
                },
                key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else v),
            )
            page_text = (
                _natural_list(pages)
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
            examples = [_excerpt(i, self.language) for i in items if _excerpt(i, self.language)]
            example = (
                f" Examples include {', '.join(labels[:5])}."
                if labels and self.is_english
                else (f" Contoh meliputi {', '.join(labels[:5])}." if labels else "")
            )
            if self.is_english:
                message = (
                    f"The assessment identified {len(items)} "
                    f"{_category_phrase(category, self.language)} "
                    f"finding{'s' if len(items) != 1 else ''} encompassing {breakdown} "
                    f"across printed page{'s' if len(pages) != 1 else ''} {page_text}.{example}"
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
                    f"Asesmen mengidentifikasi {len(items)} temuan "
                    f"{_category_phrase(category, self.language)} "
                    f"yang mencakup {breakdown} pada halaman cetak {page_text}.{example}"
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
                    "finding_codes": finding_labels,
                    "finding_label": finding_labels,
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
            excerpt = _excerpt(item, self.language)
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
                    "type": humanize_finding_type(issue_type, language=self.language),
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
        data = sections if isinstance(sections, dict) else vars(sections)

        def section_text(name: str) -> str:
            value = data.get(name, "")
            if isinstance(value, list):
                value = " ".join(
                    str(item.get("text", "")) if isinstance(item, dict) else str(item)
                    for item in value
                )
            return re.sub(r"\s+", " ", str(value)).strip()

        def sentences(name: str) -> list[str]:
            return [
                sentence.strip(" \t\n-•")
                for sentence in re.split(r"(?<=[.!?])\s+", section_text(name))
                if len(sentence.strip()) > 15
            ]

        raw = section_text("conclusions")
        conclusion_sentences = sentences("conclusions")
        result_sentences = sentences("results")
        summary_sentences = sentences("executive_summary")
        intro_sentences = sentences("introduction")
        recommendation_sentences = sentences("recommendations")

        # Use document statements as evidence anchors. The rewrite connects them
        # into a conclusion; it never invents a value, causal explanation, owner,
        # or commitment absent from the source.
        anchors = result_sentences[:2] or summary_sentences[:2]
        claim = next(
            (
                sentence
                for sentence in conclusion_sentences
                if not re.search(
                    r"\b(?:table|figure)\s+\d+|\b\d+(?:\.\d+)?\s*(?:%|years?|months?)\b",
                    sentence,
                    re.I,
                )
            ),
            conclusion_sentences[0] if conclusion_sentences else "",
        )
        objective = next(
            (
                sentence
                for sentence in intro_sentences
                if re.search(r"\b(?:purpose|objective|scope|aim)\b", sentence, re.I)
            ),
            "",
        )
        source_note = (
            (
                "No result statement was available in the extracted Results or Executive Summary "
                "sections; the rewrite therefore makes no technical inference."
                if self.is_english
                else (
                    "Tidak ada pernyataan hasil pada bagian Hasil atau Ringkasan Eksekutif "
                    "yang diekstrak; contoh ini tidak membuat inferensi teknis."
                )
            )
            if not anchors
            else ""
        )
        rewrite_items: list[str] = []
        if self.is_english:
            no_objective = (
                "This conclusion summarizes only the scope and evidence stated in the reviewed "
                "document."
            )
            result_bridge = (
                "These statements identify the principal results available to support the "
                "conclusion."
            )
            no_claim = (
                "The conclusion should state a direct answer to the stated objective and cite its "
                "supporting result."
            )
            no_recommendation = (
                "Any required follow-up should name an action, a responsible owner, and a target "
                "date."
            )
            no_inference = (
                "No result, limitation, or action beyond the extracted source text is inferred in "
                "this demonstration."
            )
            conclusion_filler = (
                "The conclusion should distinguish reported results from their interpretation and "
                "connect both to the stated scope."
            )
            scope_label = "The stated scope is: "
            result_label = "The reported evidence shows: "
            further_result_label = "A further reported result is: "
            claim_label = "The document's stated conclusion is: "
            follow_up_label = "The stated follow-up is: "
        else:
            no_objective = (
                "Kesimpulan ini hanya merangkum lingkup dan bukti yang dinyatakan dalam dokumen "
                "yang ditinjau."
            )
            result_bridge = (
                "Pernyataan tersebut merangkum hasil utama yang tersedia sebagai dasar kesimpulan."
            )
            no_claim = (
                "Kesimpulan perlu menjawab tujuan secara langsung dan mengutip hasil yang "
                "mendukungnya."
            )
            no_recommendation = (
                "Tindak lanjut yang diperlukan perlu menyebutkan tindakan, penanggung jawab, dan "
                "tanggal target."
            )
            no_inference = (
                "Contoh ini tidak menyimpulkan hasil, batasan, atau tindakan di luar teks sumber "
                "yang diekstrak."
            )
            conclusion_filler = (
                "Kesimpulan perlu membedakan hasil yang dilaporkan dari interpretasinya serta "
                "menghubungkan keduanya dengan lingkup yang dinyatakan."
            )
            scope_label = "Lingkup yang dinyatakan adalah: “"
            result_label = "Bukti yang dilaporkan menunjukkan: “"
            further_result_label = "Hasil lain yang dilaporkan adalah: “"
            claim_label = "Kesimpulan dokumen menyatakan: “"
            follow_up_label = "Tindak lanjut yang dinyatakan adalah: “"
        if objective:
            sentence = f"{scope_label}{objective.rstrip('.')}"
            rewrite_items.append(sentence + ("." if self.is_english else ".”"))
        else:
            rewrite_items.append(no_objective)
        if anchors:
            sentence = f"{result_label}{anchors[0].rstrip('.')}"
            rewrite_items.append(sentence + ("." if self.is_english else ".”"))
            if len(anchors) > 1:
                sentence = f"{further_result_label}{anchors[1].rstrip('.')}"
                rewrite_items.append(sentence + ("." if self.is_english else ".”"))
            rewrite_items.append(result_bridge)
        else:
            rewrite_items.append(source_note)
        if claim:
            sentence = f"{claim_label}{claim.rstrip('.')}"
            rewrite_items.append(sentence + ("." if self.is_english else ".”"))
        else:
            rewrite_items.append(no_claim)
        if recommendation_sentences:
            sentence = f"{follow_up_label}{recommendation_sentences[0].rstrip('.')}"
            rewrite_items.append(sentence + ("." if self.is_english else ".”"))
        else:
            rewrite_items.append(no_recommendation)
        rewrite_items.append(no_inference)
        rewrite_items = rewrite_items[:8]
        while len(rewrite_items) < 6:
            rewrite_items.insert(-1, conclusion_filler)

        issue_text = " ".join(
            str(_value(item, "message", "")).strip() for item in findings if _value(item, "message")
        )
        faults = (
            issue_text[:700]
            if issue_text
            else (
                "The source conclusion should synthesize the evidence and answer the stated "
                "objective rather than repeat result entries."
                if self.is_english
                else (
                    "Kesimpulan sumber perlu menyintesis bukti dan menjawab tujuan yang "
                    "dinyatakan, bukan mengulang entri hasil."
                )
            )
        )
        return {
            "section_title": "Conclusions" if self.is_english else "Kesimpulan",
            "intro_note": (
                "Illustrative deterministic rewrite using only statements extracted from this "
                "document. Verify the technical meaning before adoption."
                if self.is_english
                else (
                    "Contoh penulisan ulang deterministik yang hanya menggunakan pernyataan hasil "
                    "ekstraksi dokumen ini. Verifikasi makna teknis sebelum digunakan."
                )
            ),
            "as_written_title": "AS WRITTEN (EXTRACTED CONCLUSION)"
            if self.is_english
            else "TEKS ASLI (KESIMPULAN HASIL EKSTRAKSI)",
            "as_written_text": raw or self.s.no_conclusion_text,
            "faults_summary": faults,
            "demonstration_title": "DEMONSTRATION REWRITE (6-8 SENTENCES)"
            if self.is_english
            else "CONTOH PENULISAN ULANG (6-8 KALIMAT)",
            "demonstration_items": rewrite_items,
            "conclusion_summary": (
                "The example separates scope, reported evidence, conclusion, and follow-up; "
                "confirm "
                "every statement against the source before reusing it."
                if self.is_english
                else (
                    "Contoh ini memisahkan lingkup, bukti yang dilaporkan, kesimpulan, dan tindak "
                    "lanjut; cocokkan setiap pernyataan dengan sumber sebelum digunakan kembali."
                )
            ),
        }

    def generate_review_score_string(
        self, metadata: Any, scorecard: Any, *, blockers: int, majors: int, minors: int
    ) -> str:
        """Format the report banner from current document metadata and review data."""

        def clean(value: Any, fallback: str = "not supplied") -> str:
            return re.sub(r"\s*\|\s*", "/", str(value or fallback)).strip()

        def score(group: str) -> str:
            averages = _value(scorecard, "group_averages", {}) or {}
            value = averages.get(group) if isinstance(averages, dict) else None
            if value is None:
                legacy_key = {
                    "Group I": "group_i_average",
                    "Group II": "group_ii_average",
                    "Group III": "group_iii_average",
                    "Group IV": "group_iv_average",
                }[group]
                value = _value(scorecard, legacy_key)
            return "N/A" if value is None else f"{float(value):.2f}"

        baseline = int(float(_value(scorecard, "baseline_score", 0)))
        doc_no = _value(metadata, "document_number") or _value(metadata, "doc_no")
        revision = _value(metadata, "revision") or _value(metadata, "rev")
        date = _value(metadata, "document_date") or _value(metadata, "cover_date")
        return (
            f"REVIEWSCORE | doc={clean(doc_no)} | rev={clean(revision)} | date={clean(date)} | "
            f"I={score('Group I')} II={score('Group II')} III={score('Group III')} "
            f"IV={score('Group IV')} | baseline={baseline}/4 | blockers={blockers} "
            f"majors={majors} minors={minors}"
        )

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
                self.s.finding.upper(): (
                    humanize_finding_type(
                        _value(item, "type", "FINDING"), language=self.language
                    )
                    + ": "
                    + f"{_display_message(item, self.language) or _value(item, 'finding', '')}"
                ),
                self.s.what_would_fix_it.upper(): str(
                    _value(item, "suggestion", self.s.fix_reissue_default)
                ),
            }
            for i, item in enumerate(selected, 1)
        ]

    def synthesize_language_narrative(self, findings: Iterable[Any]) -> list[str]:
        """Group language findings by page and describe each with a readable label."""
        grouped: dict[str, list[str]] = {}
        for item in findings:
            evidence = _value(item, "evidence", {}) or {}
            page = str(
                _value(item, "page", "")
                or _value(item, "page_number", "")
                or _value(evidence, "page", "—")
            )
            finding_type = _value(item, "finding_type", "") or _value(item, "type", "")
            label = humanize_finding_type(finding_type, language=self.language)
            excerpt = str(
                _value(item, "as_written", "")
                or _value(evidence, "original_text", "")
                or _display_message(item, self.language)
            ).strip()
            if excerpt:
                quote = f"(‘{excerpt}’)"
                grouped.setdefault(page, []).append(f"{label} {quote}")
            else:
                grouped.setdefault(page, []).append(label)

        result = []
        for page in sorted(
            grouped,
            key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
        ):
            items = _natural_list(grouped[page], "and" if self.is_english else "dan")
            result.append(
                f"Page {page}: {items}." if self.is_english else f"Halaman {page}: {items}."
            )
        return result

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
                        (
                            "FINDING TYPE" if self.is_english else "JENIS TEMUAN"
                        ): humanize_finding_type(
                            _value(item, "finding_type", "") or _value(item, "type", ""),
                            language=self.language,
                        ),
                        self.s.as_written.upper(): original,
                        self.s.suggested.upper(): suggested,
                    }
                )
        return rows
