"""Fixed renderer copy for deterministic bilingual review reports."""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ReportLanguage


@dataclass(frozen=True, slots=True)
class ReportStrings:
    header_title: str
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
    # New additions for strict anti-bahasa belang:
    executive_summary: str
    verdict_label: str
    verdict_rejected: str
    verdict_rework: str
    verdict_approved: str
    doc_title_label: str
    doc_id_label: str
    review_date_label: str
    reviewer_pic_label: str
    key_recommendations: str
    measure_header: str
    result_header: str
    reason_header: str
    evidence_header: str
    outcome_pass: str
    outcome_fail: str
    measure_purpose_name: str
    measure_procedure_name: str
    measure_conclusions_name: str
    measure_recommendations_name: str
    measure_purpose_detail: str
    measure_procedure_detail: str
    measure_conclusions_detail: str
    measure_recommendations_detail: str
    baseline_reason_no_assessment: str
    baseline_reason_no_procedure: str
    category_blockers: str
    category_findings: str
    category_action_items: str
    rec_uncontrolled_page: str
    rec_cross_page_break: str
    rec_reference_drift: str
    rec_default: str
    rec_fallback_closing: str
    action_default: str
    not_located: str
    page_prefix: str
    review_wording: str
    blocker_title_instances: str
    blocker_consolidated_where: str
    blocker_why_it_matters_default: str
    blocker_no_source_excerpt: str
    report_subtitle: str
    appendix_a_title: str
    appendix_a_intro: str
    fix_reissue_default: str
    score_summary_callout: str
    next_revision_findings: str


_EN = ReportStrings(
    header_title="ENGINEERING DOCUMENT QUALITY REVIEW",
    title_prefix="DOCUMENT REVIEW ENGINEERING - ",
    document_reviewed="Document reviewed",
    summary_judgement="Summary judgement",
    bottom_line="BOTTOM LINE",
    baseline_measures="The four baseline measures",
    baseline_intro=(
        "Standing baseline measures evaluated on every engineering document review "
        "per Budinski Chapters 9–11:"
    ),
    baseline_score="Baseline score",
    passing="of 4 passing",
    scorecard="Scorecard",
    scorecard_intro=(
        "The Budinski scorecard is presented first so the overall writing assessment is "
        "not buried beneath repeated document-control findings."
    ),
    blockers="Blockers",
    blockers_intro="Blocking findings that prevent the document from being relied upon as issued:",
    no_blockers="No blocking findings identified.",
    blocker="Blocker",
    where="Where",
    what_it_says="What it says",
    what_body_has="What the body has",
    why_it_matters="Why it matters",
    what_would_fix_it="What would fix it",
    next_revision="Should fix in the next revision",
    next_revision_intro="Findings that should be resolved in the next scheduled revision:",
    no_major_findings="No major findings identified.",
    no="No.",
    finding="Finding",
    language_mechanics="Language and mechanics, by page",
    language_intro="Language, phrasing, typographical, and grammatical findings by page:",
    no_language_findings="No language or mechanics findings identified.",
    page="Page",
    as_written="As Written",
    suggested="Suggested",
    demonstration_rewrite="Demonstration rewrite",
    faults_against_rules="Faults against Budinski rules: ",
    scorecard_detail="Scorecard detail",
    scorecard_detail_intro=(
        "Scored against the 41 items of the Appendix 12 review checklist from Budinski, "
        "Engineers' Guide to Technical Writing (2001). Scores: 1 = disagree, 5 = agree. "
        "Any item scoring 2 or below is treated as requiring rework."
    ),
    group="Group",
    focus_area="Focus Area",
    items="Items",
    group_average="Group Average",
    overall_average="Overall Average",
    all_checklist_items="All {count} Checklist Items (Appendix 12)",
    item="Item",
    checklist_parameter="Checklist Parameter",
    score="Score",
    reviewer_note="Reviewer Note",
    rework="Rework",
    what_document_does_well="What this document does well",
    strengths_intro="Positive engineering writing practices and structural strengths observed:",
    limits_of_review="Limits of this review",
    page_of="Page",
    generated_review="Generated from persisted document findings and scorecard artifacts.",
    not_supplied="Not supplied",
    pending_verification="Pending Verification",
    type_of_review="Type of review",
    basis="Basis",
    scoring="Scoring",
    note="Note",
    not_covered="Not covered",
    prepared_by="Prepared by",
    checked_by="Checked / Verified by",
    status="Status",
    doc_no="Doc No",
    revision="Rev",
    pages="Pages",
    file_date="File Date",
    originator="Originator",
    review_score_fallback="REVIEWSCORE | generated deterministically from persisted findings",
    no_conclusion_text="No conclusion text was extracted.",
    demo_intro="Demonstration of a clearer conclusion structure:",
    demo_as_written="As Written",
    demo_demonstration="Demonstration",
    demo_conclusion=(
        "This demonstration separates the conclusion statements from supporting detail."
    ),
    group_i="Group I: Technical Content",
    group_ii="Group II: Style",
    group_iii="Group III: Report Mechanics",
    group_iv="Group IV: Conclusions & Craft",
    group_i_desc="Does the document have substance?",
    group_ii_desc="Is it written appropriately for the application?",
    group_iii_desc="Introduction and Procedure",
    group_iv_desc="Results, Discussion, Conclusions, Craft",
    default_measure_purpose="State the report purpose separately from the work objective.",
    default_measure_procedure=(
        "Provide enough method detail for another competent party to repeat the work."
    ),
    default_measure_conclusions="Separate conclusions from results and discussion.",
    default_measure_recommendations="Name an owner and due date for each recommendation.",
    # Strict anti-bahasa belang additions:
    executive_summary="Executive summary",
    verdict_label="VERDICT / STATUS",
    verdict_rejected="REJECTED",
    verdict_rework="NEEDS REWORK",
    verdict_approved="APPROVED FOR ISSUE",
    doc_title_label="Document Title",
    doc_id_label="Document ID",
    review_date_label="Review Date",
    reviewer_pic_label="Reviewer PIC",
    key_recommendations="Key Recommendations",
    measure_header="Measure",
    result_header="Result",
    reason_header="Reason",
    evidence_header="Evidence",
    outcome_pass="PASS",
    outcome_fail="FAIL",
    measure_purpose_name="Purpose distinct from objective",
    measure_procedure_name="Procedure repeatable",
    measure_conclusions_name="Conclusions are conclusions",
    measure_recommendations_name="Recommendations actionable",
    measure_purpose_detail=(
        "States the purpose of the report explicitly, distinct from the objective of the work"
    ),
    measure_procedure_detail=(
        "Procedure detailed enough for another competent party to repeat the work"
    ),
    measure_conclusions_detail="Conclusions are conclusions, not results and not discussion",
    measure_recommendations_detail="Recommendations name an owner and a date",
    baseline_reason_no_assessment="No persisted baseline assessment was available.",
    baseline_reason_no_procedure="Procedure evidence was not reconstructed in the export adapter.",
    category_blockers="Blockers",
    category_findings="Findings",
    category_action_items="Action Items",
    rec_uncontrolled_page="Apply controlled document template to all affected pages.",
    rec_cross_page_break=(
        "Correct pagination so sentences and paragraphs do not break across pages."
    ),
    rec_reference_drift="Update page references and re-verify table of contents.",
    rec_default="Correct findings, verify source evidence, and issue controlled revision.",
    rec_fallback_closing=(
        "Maintain evidence base and perform final verification before controlled release."
    ),
    action_default="Correct the identified issue and verify the revised section.",
    not_located="Not located",
    page_prefix="Page",
    review_wording="Review wording.",
    blocker_title_instances="{count} instances",
    blocker_consolidated_where="Consolidated across the affected printed pages",
    blocker_why_it_matters_default=(
        "The repeated findings indicate one unresolved control weakness across the document."
    ),
    blocker_no_source_excerpt="No source excerpt was persisted for this finding.",
    report_subtitle="Executive engineering-document review report",
    appendix_a_title="Appendix A - Budinski Appendix 12 checklist",
    appendix_a_intro="Detailed 41-item evaluation across all four Appendix 12 checklist groups:",
    fix_reissue_default="Correct, verify, and reissue the affected section.",
    score_summary_callout=(
        "Overall average: {overall} / 5.00. Group averages: I {g1}, II {g2}, "
        "III {g3}, IV {g4}. Items requiring rework: {rework}."
    ),
    next_revision_findings="Next revision findings",
)

_ID = ReportStrings(
    header_title="REKAYASA TINJAUAN KUALITAS DOKUMEN",
    title_prefix="REKAYASA TINJAUAN DOKUMEN - ",
    document_reviewed="Dokumen yang ditinjau",
    summary_judgement="Penilaian ringkasan",
    bottom_line="KESIMPULAN UTAMA",
    baseline_measures="Empat ukuran dasar",
    baseline_intro=(
        "Ukuran dasar yang dievaluasi pada setiap tinjauan dokumen rekayasa sesuai "
        "Bab 9–11 Budinski:"
    ),
    baseline_score="Nilai dasar",
    passing="dari 4 lulus",
    scorecard="Kartu nilai",
    scorecard_intro=(
        "Kartu nilai Budinski disajikan terlebih dahulu agar penilaian penulisan "
        "keseluruhan tidak tertutup oleh temuan pengendalian dokumen yang berulang."
    ),
    blockers="Penghalang",
    blockers_intro=(
        "Temuan penghalang yang membuat dokumen tidak dapat diandalkan sebagaimana diterbitkan:"
    ),
    no_blockers="Tidak ada temuan penghalang.",
    blocker="Penghalang",
    where="Lokasi",
    what_it_says="Isi temuan",
    what_body_has="Isi dokumen",
    why_it_matters="Mengapa penting",
    what_would_fix_it="Perbaikan yang diperlukan",
    next_revision="Perbaiki pada revisi berikutnya",
    next_revision_intro="Temuan yang harus diselesaikan pada revisi terjadwal berikutnya:",
    no_major_findings="Tidak ada temuan utama.",
    no="No.",
    finding="Temuan",
    language_mechanics="Bahasa dan mekanika, menurut halaman",
    language_intro="Temuan bahasa, frasa, tipografi, dan tata bahasa menurut halaman:",
    no_language_findings="Tidak ada temuan bahasa atau mekanika.",
    page="Halaman",
    as_written="Teks asli",
    suggested="Saran",
    demonstration_rewrite="Contoh penulisan ulang",
    faults_against_rules="Pelanggaran terhadap aturan Budinski: ",
    scorecard_detail="Rincian kartu nilai",
    scorecard_detail_intro=(
        "Dinilai berdasarkan 41 item daftar periksa tinjauan Lampiran 12 dari Budinski, "
        "Engineers' Guide to Technical Writing (2001). Nilai: 1 = tidak setuju, "
        "5 = setuju. Item dengan nilai 2 atau kurang memerlukan pengerjaan ulang."
    ),
    group="Grup",
    focus_area="Fokus",
    items="Item",
    group_average="Rata-rata Grup",
    overall_average="Rata-rata Keseluruhan",
    all_checklist_items="Semua {count} Item Daftar Periksa (Lampiran 12)",
    item="Item",
    checklist_parameter="Parameter Daftar Periksa",
    score="Nilai",
    reviewer_note="Catatan Peninjau",
    rework="Pengerjaan ulang",
    what_document_does_well="Keunggulan dokumen ini",
    strengths_intro="Praktik penulisan rekayasa dan kekuatan struktur yang diamati:",
    limits_of_review="Batasan tinjauan ini",
    page_of="Halaman",
    generated_review="Dibuat dari temuan dokumen dan artefak kartu nilai yang tersimpan.",
    not_supplied="Tidak tersedia",
    pending_verification="Menunggu verifikasi",
    type_of_review="Jenis tinjauan",
    basis="Dasar",
    scoring="Sistem penilaian",
    note="Catatan",
    not_covered="Tidak dicakup",
    prepared_by="Disiapkan oleh",
    checked_by="Diperiksa / Diverifikasi oleh",
    status="Status",
    doc_no="No. Dokumen",
    revision="Revisi",
    pages="Halaman",
    file_date="Tanggal File",
    originator="Pembuat",
    review_score_fallback="NILAI TINJAUAN | dibuat secara deterministik dari temuan tersimpan",
    no_conclusion_text="Tidak ada teks kesimpulan yang diekstrak.",
    demo_intro="Contoh struktur kesimpulan yang lebih jelas:",
    demo_as_written="Teks Asli",
    demo_demonstration="Contoh",
    demo_conclusion="Contoh ini memisahkan pernyataan kesimpulan dari rincian pendukung.",
    group_i="Grup I: Konten Teknis",
    group_ii="Grup II: Gaya",
    group_iii="Grup III: Mekanika Laporan",
    group_iv="Grup IV: Kesimpulan & Keterampilan",
    group_i_desc="Apakah dokumen memiliki substansi?",
    group_ii_desc="Apakah penulisannya sesuai untuk penerapan?",
    group_iii_desc="Pendahuluan dan Prosedur",
    group_iv_desc="Hasil, Pembahasan, Kesimpulan, Keterampilan",
    default_measure_purpose="Nyatakan tujuan laporan secara terpisah dari tujuan pekerjaan.",
    default_measure_procedure=(
        "Berikan rincian metode yang cukup agar pihak kompeten lain dapat mengulangi pekerjaan."
    ),
    default_measure_conclusions="Pisahkan kesimpulan dari hasil dan pembahasan.",
    default_measure_recommendations=(
        "Sebutkan pemilik dan tanggal jatuh tempo untuk setiap rekomendasi."
    ),
    # Strict anti-bahasa belang additions:
    executive_summary="Ringkasan eksekutif",
    verdict_label="STATUS / PUTUSAN",
    verdict_rejected="DITOLAK",
    verdict_rework="PERLU PERBAIKAN (REWORK)",
    verdict_approved="LAYAK TERBIT",
    doc_title_label="Judul Dokumen",
    doc_id_label="ID Dokumen",
    review_date_label="Tanggal Tinjauan",
    reviewer_pic_label="PIC Peninjau",
    key_recommendations="Rekomendasi Utama",
    measure_header="Ukuran",
    result_header="Hasil",
    reason_header="Alasan",
    evidence_header="Bukti",
    outcome_pass="LULUS",
    outcome_fail="PERBAIKAN",
    measure_purpose_name="Tujuan laporan terpisah dari tujuan pekerjaan",
    measure_procedure_name="Prosedur dapat diulangi",
    measure_conclusions_name="Kesimpulan adalah kesimpulan",
    measure_recommendations_name="Rekomendasi dapat ditindaklanjuti",
    measure_purpose_detail=(
        "Menyatakan tujuan laporan secara eksplisit, terpisah dari tujuan pekerjaan"
    ),
    measure_procedure_detail=(
        "Prosedur cukup rinci agar pihak kompeten lain dapat mengulangi pekerjaan"
    ),
    measure_conclusions_detail="Kesimpulan murni kesimpulan, bukan hasil dan bukan pembahasan",
    measure_recommendations_detail="Rekomendasi mencantumkan pemilik dan tenggat waktu",
    baseline_reason_no_assessment="Tidak ada penilaian dasar tersimpan yang tersedia.",
    baseline_reason_no_procedure="Bukti prosedur tidak direkonstruksi dalam adaptor ekspor.",
    category_blockers="Penghalang",
    category_findings="Temuan",
    category_action_items="Rencana Tindakan",
    rec_uncontrolled_page="Terapkan template dokumen terkendali pada seluruh halaman terdampak.",
    rec_cross_page_break=(
        "Perbaiki penomoran halaman agar kalimat dan paragraf tidak terputus lintas halaman."
    ),
    rec_reference_drift="Perbarui referensi halaman dan verifikasi ulang daftar isi.",
    rec_default="Perbaiki temuan, verifikasi bukti sumber, dan terbitkan revisi terkendali.",
    rec_fallback_closing=(
        "Pertahankan basis bukti dan lakukan verifikasi akhir sebelum penerbitan terkendali."
    ),
    action_default="Perbaiki masalah yang teridentifikasi dan verifikasi bagian yang direvisi.",
    not_located="Lokasi tidak ditemukan",
    page_prefix="Halaman",
    review_wording="Periksa pilihan kata.",
    blocker_title_instances="{count} kejadian",
    blocker_consolidated_where="Dikosolidasikan di seluruh halaman cetak terdampak",
    blocker_why_it_matters_default=(
        "Temuan berulang menunjukkan satu kelemahan pengendalian yang belum "
        "terselesaikan di seluruh dokumen."
    ),
    blocker_no_source_excerpt="Tidak ada kutipan sumber yang tersimpan untuk temuan ini.",
    report_subtitle="Laporan tinjauan dokumen rekayasa eksekutif",
    appendix_a_title="Lampiran A - Daftar Periksa Lampiran 12 Budinski",
    appendix_a_intro=(
        "Evaluasi terperinci 41 item di seluruh empat grup daftar periksa Lampiran 12:"
    ),
    fix_reissue_default="Perbaiki, verifikasi, dan terbitkan ulang bagian terdampak.",
    score_summary_callout=(
        "Rata-rata keseluruhan: {overall} / 5.00. Rata-rata grup: I {g1}, II {g2}, "
        "III {g3}, IV {g4}. Item yang memerlukan perbaikan: {rework}."
    ),
    next_revision_findings="Temuan revisi berikutnya",
)

# Comprehensive Budinski Appendix 12 41 checklist items bilingual parameters
BUDINSKI_41_ITEMS: dict[str, dict[str, str]] = {
    # Group I: Technical Content
    "I.1": {
        "en": "The message to the reader is clear",
        "id": "Pesan kepada pembaca jelas",
        "guidance_en": "Clear technical substance and core takeaways.",
        "guidance_id": "Substansi teknis dan poin inti jelas.",
    },
    "I.2": {
        "en": "The engineering approach is logical",
        "id": "Pendekatan rekayasa logis",
        "guidance_en": "Sound engineering methodology and reasoning.",
        "guidance_id": "Metodologi dan penalaran rekayasa tepat.",
    },
    "I.3": {
        "en": "Adequate research of previous work",
        "id": "Penelitian memadai atas pekerjaan sebelumnya",
        "guidance_en": "Proper citation and review of prior work.",
        "guidance_id": "Sitasi dan tinjauan pekerjaan sebelumnya memadai.",
    },
    "I.4": {
        "en": "Adequate comparison with work of others",
        "id": "Perbandingan memadai dengan pekerjaan pihak lain",
        "guidance_en": "Contextual benchmark against industry findings.",
        "guidance_id": "Tolok ukur kontekstual terhadap temuan industri.",
    },
    "I.5": {
        "en": "Conclusions supported by the work",
        "id": "Kesimpulan didukung oleh hasil pekerjaan",
        "guidance_en": "Direct evidence for every drawn conclusion.",
        "guidance_id": "Bukti langsung untuk setiap kesimpulan yang ditarik.",
    },
    "I.6": {
        "en": "The value of the work is clearly stated",
        "id": "Nilai manfaat pekerjaan dinyatakan secara jelas",
        "guidance_en": "Practical utility or engineering value communicated.",
        "guidance_id": "Manfaat praktis atau nilai rekayasa tersampaikan.",
    },
    "I.7": {
        "en": "The work met the stated objective",
        "id": "Pekerjaan memenuhi sasaran yang dinyatakan",
        "guidance_en": "Scope fully accomplished without gaps.",
        "guidance_id": "Ruang lingkup terpenuhi sepenuhnya tanpa celah.",
    },
    "I.8": {
        "en": "Original and free of plagiarism",
        "id": "Orisinal dan bebas dari plagiarisme",
        "guidance_en": "Authentic content with attributed sources.",
        "guidance_id": "Konten autentik dengan sumber teratribusi.",
    },
    "I.9": {
        "en": "Timely",
        "id": "Tepat waktu",
        "guidance_en": "Delivered within expected engineering operational timeframe.",
        "guidance_id": "Diselesaikan dalam jangka waktu operasional rekayasa yang diharapkan.",
    },
    # Group II: Style
    "II.1": {
        "en": "Objective, neutral tone",
        "id": "Nada objektif dan netral",
        "guidance_en": "Impartial technical writing voice.",
        "guidance_id": "Gaya penulisan teknis netral dan tidak memihak.",
    },
    "II.2": {
        "en": "Sections are logical",
        "id": "Bagian-bagian dokumen logis",
        "guidance_en": "Coherent structural progression.",
        "guidance_id": "Urutan struktur dokumen runtut dan koheren.",
    },
    "II.3": {
        "en": "Writing level suits the readership",
        "id": "Tingkat penulisan sesuai dengan pembaca",
        "guidance_en": "Appropriate technical depth for the intended audience.",
        "guidance_id": "Kedalaman teknis sesuai untuk target pembaca.",
    },
    "II.4": {
        "en": "Free of jargon and commercialism",
        "id": "Bebas dari jargon dan komersialisme",
        "guidance_en": "Avoids proprietary marketing terms or buzzwords.",
        "guidance_id": "Menghindari istilah pemasaran atau bahasa klise dagang.",
    },
    "II.5": {
        "en": "Use of English is satisfactory",
        "id": "Penggunaan tata bahasa memuaskan",
        "guidance_en": "Grammatically sound with proper terminology.",
        "guidance_id": "Tata bahasa tertib dengan terminologi yang benar.",
    },
    "II.6": {
        "en": "Understandable and concise",
        "id": "Mudah dipahami dan ringkas",
        "guidance_en": "Clear communication without filler phrases.",
        "guidance_id": "Komunikasi lugas tanpa kalimat bertele-tele.",
    },
    "II.7": {
        "en": "Interesting",
        "id": "Menarik untuk dibaca",
        "guidance_en": "Engaging technical narrative.",
        "guidance_id": "Alur narasi teknis menarik.",
    },
    "II.8": {
        "en": "Free of personal opinion",
        "id": "Bebas dari opini pribadi dan kiasan",
        "guidance_en": "Fact-based claims without subjective speculation.",
        "guidance_id": "Klaim berbasis fakta tanpa spekulasi subjektif.",
    },
    "II.9": {
        "en": "Does not over-explain",
        "id": "Tidak menjelaskan secara berlebihan",
        "guidance_en": "Assumes standard foundational engineering knowledge.",
        "guidance_id": "Mengasumsikan pengetahuan dasar rekayasa standar.",
    },
    "II.10": {
        "en": "Conforms to writing practice",
        "id": "Sesuai dengan praktik penulisan standar",
        "guidance_en": "Follows established formal engineering format.",
        "guidance_id": "Mengikuti format rekayasa formal yang baku.",
    },
    "II.11": {
        "en": "Page layout and whitespace",
        "id": "Tata letak halaman dan ruang kosong memadai",
        "guidance_en": "Balanced margins, typography, and page utilization.",
        "guidance_id": "Margin, tipografi, dan pemanfaatan halaman seimbang.",
    },
    # Group III: Report Mechanics
    "III.1": {
        "en": "Sufficient background information",
        "id": "Informasi latar belakang memadai",
        "guidance_en": "Adequate context to understand why the work was performed.",
        "guidance_id": "Konteks memadai untuk memahami latar belakang pekerjaan.",
    },
    "III.2": {
        "en": "Purpose of the work is clear",
        "id": "Tujuan pekerjaan jelas",
        "guidance_en": "Defines what physical or engineering activity occurred.",
        "guidance_id": "Mendefinisikan aktivitas fisik atau rekayasa yang dilakukan.",
    },
    "III.3": {
        "en": "Objective of the work is clear",
        "id": "Sasaran pekerjaan jelas",
        "guidance_en": "Measurable goals of the technical task.",
        "guidance_id": "Target terukur dari tugas teknis.",
    },
    "III.4": {
        "en": "Purpose of the report is clear",
        "id": "Tujuan laporan jelas",
        "guidance_en": "States the communicative purpose of this written document.",
        "guidance_id": "Menyatakan tujuan komunikasi dokumen tertulis ini.",
    },
    "III.5": {
        "en": "Objective of the report is clear",
        "id": "Sasaran laporan jelas",
        "guidance_en": "What decisions the report is intended to enable.",
        "guidance_id": "Keputusan apa yang dituju oleh laporan ini.",
    },
    "III.6": {
        "en": "Format of the report is stated",
        "id": "Format laporan dinyatakan",
        "guidance_en": "Roadmap of document structure given in front matter.",
        "guidance_id": "Peta struktur dokumen dicantumkan di bagian pendahuluan.",
    },
    "III.7": {
        "en": "Work of others adequately referenced",
        "id": "Pekerjaan pihak lain dirujuk secara memadai",
        "guidance_en": "Standards, external data, and citations properly anchored.",
        "guidance_id": "Standar, data eksternal, dan sitasi dirujuk secara tepat.",
    },
    "III.8": {
        "en": "Experimental steps outlined",
        "id": "Langkah-langkah pengujian diuraikan",
        "guidance_en": "Sequential procedural breakdown.",
        "guidance_id": "Rincian prosedur bertahap dan teratur.",
    },
    "III.9": {
        "en": "Adequate detail to repeat",
        "id": "Rincian memadai untuk diulangi",
        "guidance_en": "Enables an independent engineer to reproduce the procedure.",
        "guidance_id": "Memungkinkan insinyur independen mengulangi prosedur.",
    },
    "III.10": {
        "en": "Free of unnecessary trade names",
        "id": "Bebas dari nama dagang yang tidak perlu",
        "guidance_en": "Generic material classifications used over brand names.",
        "guidance_id": "Klasifikasi material generik digunakan alih-alih merek dagang.",
    },
    "III.11": {
        "en": "Test standards properly cited",
        "id": "Standar pengujian dikutip dengan benar",
        "guidance_en": "Explicit standards organizations, editions, and clauses cited.",
        "guidance_id": "Organisasi standar, edisi, dan pasal dikutip secara eksplisit.",
    },
    # Group IV: Conclusions & Craft
    "IV.1": {
        "en": "Results clearly stated",
        "id": "Hasil dinyatakan secara jelas",
        "guidance_en": "Data and findings presented without ambiguity.",
        "guidance_id": "Data dan temuan disajikan tanpa keraguan.",
    },
    "IV.2": {
        "en": "Results free of discussion",
        "id": "Hasil bebas dari pembahasan dan prosedur",
        "guidance_en": "Raw results isolated from interpretations.",
        "guidance_id": "Hasil murni dipisahkan dari interpretasi dan spekulasi.",
    },
    "IV.3": {
        "en": "Graphs and tables proper",
        "id": "Grafik dan tabel tepat dan diperlukan",
        "guidance_en": "Self-contained figures with labels, units, and captions.",
        "guidance_id": "Gambar dan tabel lengkap dengan label, satuan, dan keterangan.",
    },
    "IV.4": {
        "en": "Sufficient results presented",
        "id": "Hasil yang disajikan mencukupi",
        "guidance_en": "Adequate data volume to justify findings.",
        "guidance_id": "Volume data cukup untuk mendukung temuan.",
    },
    "IV.5": {
        "en": "Discussion relates to others",
        "id": "Pembahasan menghubungkan hasil dengan pihak lain",
        "guidance_en": "Contextualized against industry literature and sister studies.",
        "guidance_id": "Dikontekstualisasikan terhadap literatur industri dan kajian sejenis.",
    },
    "IV.6": {
        "en": "Discussion length appropriate",
        "id": "Panjang pembahasan proporsional",
        "guidance_en": "Proportional analysis commensurate with data complexity.",
        "guidance_id": "Analisis proporsional sesuai kompleksitas data.",
    },
    "IV.7": {
        "en": "Conclusions follow from results",
        "id": "Kesimpulan mengikuti hasil dan pembahasan",
        "guidance_en": "Deductions trace directly to presented evidence.",
        "guidance_id": "Deduksi bersumber langsung dari bukti yang disajikan.",
    },
    "IV.8": {
        "en": "Conclusions clear and unambiguous",
        "id": "Kesimpulan jelas dan tidak ambigu",
        "guidance_en": "Explicit takeaway statements.",
        "guidance_id": "Pernyataan kesimpulan tegas dan tidak ambigu.",
    },
    "IV.9": {
        "en": "References properly attributed",
        "id": "Referensi diatribusikan dan dicatat dengan benar",
        "guidance_en": "Complete bibliography with traceable source metadata.",
        "guidance_id": "Bibliografi lengkap dengan metadata sumber yang dapat dilacak.",
    },
    "IV.10": {
        "en": "Sentence and paragraph length",
        "id": "Panjang kalimat dan paragraf proporsional",
        "guidance_en": "Controlled sentence length and focused paragraph blocks.",
        "guidance_id": "Panjang kalimat terkendali dan paragraf terfokus.",
    },
}


def get_report_strings(language: ReportLanguage = ReportLanguage.ENGLISH) -> ReportStrings:
    """Return immutable fixed copy for a validated report language."""
    return _ID if language == ReportLanguage.INDONESIAN else _EN


def get_budinski_item_name(code: str, language: ReportLanguage = ReportLanguage.ENGLISH) -> str:
    """Return the localized name for a Budinski checklist item code."""
    lang_key = "id" if language == ReportLanguage.INDONESIAN else "en"
    item = BUDINSKI_41_ITEMS.get(code)
    if item:
        return item.get(lang_key, item["en"])
    return code


def get_budinski_guidance_note(
    code: str, score: int | None, language: ReportLanguage = ReportLanguage.ENGLISH
) -> str:
    """Return localized reviewer guidance or explanation for a checklist item."""
    lang_key = "id" if language == ReportLanguage.INDONESIAN else "en"
    item = BUDINSKI_41_ITEMS.get(code)
    if not item:
        if score is not None and score <= 2:
            return (
                "Perlu pengerjaan ulang."
                if language == ReportLanguage.INDONESIAN
                else "Requires rework."
            )
        return "Sesuai standar." if language == ReportLanguage.INDONESIAN else "Satisfactory."
    if score is not None and score <= 2:
        return item.get(f"guidance_{lang_key}", item.get("guidance_en", ""))
    return item.get(f"guidance_{lang_key}", item.get("guidance_en", ""))
