"""Fixed renderer copy for deterministic bilingual review reports."""
from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ReportLanguage


@dataclass(frozen=True, slots=True)
class ReportStrings:
    title_prefix: str
    document_reviewed: str
    summary_judgement: str
    bottom_line: str
    baseline_measures: str
    baseline_intro: str
    baseline_score: str
    passing: str
    scorecard: str
    scorecard_intro: str
    blockers: str
    blockers_intro: str
    no_blockers: str
    blocker: str
    where: str
    what_it_says: str
    what_body_has: str
    why_it_matters: str
    what_would_fix_it: str
    next_revision: str
    next_revision_intro: str
    no_major_findings: str
    no: str
    finding: str
    language_mechanics: str
    language_intro: str
    no_language_findings: str
    page: str
    as_written: str
    suggested: str
    demonstration_rewrite: str
    faults_against_rules: str
    scorecard_detail: str
    scorecard_detail_intro: str
    group: str
    focus_area: str
    items: str
    group_average: str
    overall_average: str
    all_checklist_items: str
    item: str
    checklist_parameter: str
    score: str
    reviewer_note: str
    rework: str
    what_document_does_well: str
    strengths_intro: str
    limits_of_review: str
    page_of: str
    generated_review: str
    not_supplied: str
    pending_verification: str
    type_of_review: str
    basis: str
    scoring: str
    note: str
    not_covered: str
    prepared_by: str
    checked_by: str
    status: str
    doc_no: str
    revision: str
    pages: str
    file_date: str
    originator: str
    review_score_fallback: str
    no_conclusion_text: str
    demo_intro: str
    demo_as_written: str
    demo_demonstration: str
    demo_conclusion: str
    group_i: str
    group_ii: str
    group_iii: str
    group_iv: str
    group_i_desc: str
    group_ii_desc: str
    group_iii_desc: str
    group_iv_desc: str
    default_measure_purpose: str
    default_measure_procedure: str
    default_measure_conclusions: str
    default_measure_recommendations: str


_EN = ReportStrings(
    title_prefix="DOCUMENT REVIEW ENGINEERING - ", document_reviewed="Document reviewed",
    summary_judgement="Summary judgement", bottom_line="BOTTOM LINE",
    baseline_measures="The four baseline measures",
    baseline_intro="Standing baseline measures evaluated on every engineering document review per Budinski Chapters 9–11:",
    baseline_score="Baseline score", passing="of 4 passing", scorecard="Scorecard",
    scorecard_intro="The Budinski scorecard is presented first so the overall writing assessment is not buried beneath repeated document-control findings.",
    blockers="Blockers", blockers_intro="Blocking findings that prevent the document from being relied upon as issued:", no_blockers="No blocking findings identified.", blocker="Blocker",
    where="Where", what_it_says="What it says", what_body_has="What the body has", why_it_matters="Why it matters", what_would_fix_it="What would fix it",
    next_revision="Should fix in the next revision", next_revision_intro="Findings that should be resolved in the next scheduled revision:", no_major_findings="No major findings identified.", no="No.", finding="Finding",
    language_mechanics="Language and mechanics, by page", language_intro="Language, phrasing, typographical, and grammatical findings by page:", no_language_findings="No language or mechanics findings identified.", page="Page", as_written="As Written", suggested="Suggested",
    demonstration_rewrite="Demonstration rewrite", faults_against_rules="Faults against Budinski rules: ", scorecard_detail="Scorecard detail",
    scorecard_detail_intro="Scored against the 41 items of the Appendix 12 review checklist from Budinski, Engineers' Guide to Technical Writing (2001). Scores: 1 = disagree, 5 = agree. Any item scoring 2 or below is treated as requiring rework.",
    group="Group", focus_area="Focus Area", items="Items", group_average="Group Average", overall_average="Overall Average", all_checklist_items="All {count} Checklist Items (Appendix 12)", item="Item", checklist_parameter="Checklist Parameter", score="Score", reviewer_note="Reviewer Note", rework="Rework",
    what_document_does_well="What this document does well", strengths_intro="Positive engineering writing practices and structural strengths observed:", limits_of_review="Limits of this review", page_of="Page", generated_review="Generated from persisted document findings and scorecard artifacts.", not_supplied="Not supplied", pending_verification="Pending Verification", type_of_review="Deterministic engineering document review", basis="Budinski Appendix 12, internal consistency, layout, traceability, and language findings.", scoring="Budinski Appendix 12 scores 1-5; scores of 2 or below require rework.", note="Generated from persisted document findings and scorecard artifacts.", not_covered="Engineering adequacy, operational safety, and external standards certification.", prepared_by="Prepared by", checked_by="Checked / Verified by", status="Status", doc_no="Doc No", revision="Rev", pages="Pages", file_date="File Date", originator="Originator", review_score_fallback="REVIEWSCORE | generated deterministically from persisted findings", no_conclusion_text="No conclusion text was extracted.", demo_intro="Demonstration of a clearer conclusion structure:", demo_as_written="As Written", demo_demonstration="Demonstration", demo_conclusion="This demonstration separates the conclusion statements from supporting detail.", group_i="GROUP I: TECHNICAL CONTENT", group_ii="GROUP II: STYLE", group_iii="GROUP III: REPORT MECHANICS", group_iv="GROUP IV: CONCLUSIONS & CRAFT", group_i_desc="Does the document have substance?", group_ii_desc="Is it written appropriately for the application?", group_iii_desc="Introduction and Procedure", group_iv_desc="Results, Discussion, Conclusions, Craft", default_measure_purpose="State the report purpose separately from the work objective.", default_measure_procedure="Provide enough method detail for another competent party to repeat the work.", default_measure_conclusions="Separate conclusions from results and discussion.", default_measure_recommendations="Name an owner and due date for each recommendation.",
)

_ID = ReportStrings(
    title_prefix="REKAYASA TINJAUAN DOKUMEN - ", document_reviewed="Dokumen yang ditinjau", summary_judgement="Penilaian ringkasan", bottom_line="KESIMPULAN UTAMA", baseline_measures="Empat ukuran dasar", baseline_intro="Ukuran dasar yang dievaluasi pada setiap tinjauan dokumen rekayasa sesuai Bab 9–11 Budinski:", baseline_score="Nilai dasar", passing="dari 4 lulus", scorecard="Kartu nilai", scorecard_intro="Kartu nilai Budinski disajikan terlebih dahulu agar penilaian penulisan keseluruhan tidak tertutup oleh temuan pengendalian dokumen yang berulang.", blockers="Penghalang", blockers_intro="Temuan penghalang yang membuat dokumen tidak dapat diandalkan sebagaimana diterbitkan:", no_blockers="Tidak ada temuan penghalang.", blocker="Penghalang", where="Lokasi", what_it_says="Isi temuan", what_body_has="Isi dokumen", why_it_matters="Mengapa penting", what_would_fix_it="Perbaikan yang diperlukan", next_revision="Perbaiki pada revisi berikutnya", next_revision_intro="Temuan yang harus diselesaikan pada revisi terjadwal berikutnya:", no_major_findings="Tidak ada temuan utama.", no="No.", finding="Temuan", language_mechanics="Bahasa dan mekanika, menurut halaman", language_intro="Temuan bahasa, frasa, tipografi, dan tata bahasa menurut halaman:", no_language_findings="Tidak ada temuan bahasa atau mekanika.", page="Halaman", as_written="Teks asli", suggested="Saran", demonstration_rewrite="Contoh penulisan ulang", faults_against_rules="Pelanggaran terhadap aturan Budinski: ", scorecard_detail="Rincian kartu nilai", scorecard_detail_intro="Dinilai berdasarkan 41 item daftar periksa tinjauan Lampiran 12 dari Budinski, Engineers' Guide to Technical Writing (2001). Nilai: 1 = tidak setuju, 5 = setuju. Item dengan nilai 2 atau kurang memerlukan pengerjaan ulang.", group="Grup", focus_area="Fokus", items="Item", group_average="Rata-rata Grup", overall_average="Rata-rata Keseluruhan", all_checklist_items="Semua {count} Item Daftar Periksa (Lampiran 12)", item="Item", checklist_parameter="Parameter Daftar Periksa", score="Nilai", reviewer_note="Catatan Peninjau", rework="Pengerjaan ulang", what_document_does_well="Keunggulan dokumen ini", strengths_intro="Praktik penulisan rekayasa dan kekuatan struktur yang diamati:", limits_of_review="Batasan tinjauan ini", page_of="Halaman", generated_review="Dibuat dari temuan dokumen dan artefak kartu nilai yang tersimpan.", not_supplied="Tidak tersedia", pending_verification="Menunggu verifikasi", type_of_review="Tinjauan dokumen rekayasa deterministik", basis="Lampiran 12 Budinski, konsistensi internal, tata letak, keterlacakan, dan temuan bahasa.", scoring="Nilai Lampiran 12 Budinski 1-5; nilai 2 atau kurang memerlukan pengerjaan ulang.", note="Dibuat dari temuan dokumen dan artefak kartu nilai yang tersimpan.", not_covered="Kecukupan rekayasa, keselamatan operasional, dan sertifikasi standar eksternal.", prepared_by="Disiapkan oleh", checked_by="Diperiksa / Diverifikasi oleh", status="Status", doc_no="No. Dokumen", revision="Revisi", pages="Halaman", file_date="Tanggal File", originator="Pembuat", review_score_fallback="NILAI TINJAUAN | dibuat secara deterministik dari temuan tersimpan", no_conclusion_text="Tidak ada teks kesimpulan yang diekstrak.", demo_intro="Contoh struktur kesimpulan yang lebih jelas:", demo_as_written="Teks Asli", demo_demonstration="Contoh", demo_conclusion="Contoh ini memisahkan pernyataan kesimpulan dari rincian pendukung.", group_i="GRUP I: KONTEN TEKNIS", group_ii="GRUP II: GAYA", group_iii="GRUP III: MEKANIKA LAPORAN", group_iv="GRUP IV: KESIMPULAN & KETERAMPILAN", group_i_desc="Apakah dokumen memiliki substansi?", group_ii_desc="Apakah penulisannya sesuai untuk penerapan?", group_iii_desc="Pendahuluan dan Prosedur", group_iv_desc="Hasil, Pembahasan, Kesimpulan, Keterampilan", default_measure_purpose="Nyatakan tujuan laporan secara terpisah dari tujuan pekerjaan.", default_measure_procedure="Berikan rincian metode yang cukup agar pihak kompeten lain dapat mengulangi pekerjaan.", default_measure_conclusions="Pisahkan kesimpulan dari hasil dan pembahasan.", default_measure_recommendations="Sebutkan pemilik dan tanggal jatuh tempo untuk setiap rekomendasi.",
)


def get_report_strings(language: ReportLanguage = ReportLanguage.ENGLISH) -> ReportStrings:
    """Return immutable fixed copy for a validated report language."""
    return _ID if language == ReportLanguage.INDONESIAN else _EN
