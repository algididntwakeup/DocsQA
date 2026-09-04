# Product Requirements Document: Document QC & Traceability Audit Web Application
**Version:** 2.0 (Phase 1 — Non-LLM Architecture, incl. CTO Audit Requirements)
**Owner:** Product Management
**Status:** Approved for Phase 1 Implementation (acceptance defaults approved 2026-09-04)
**Target Users:** Material Engineering Services Division

---

## 1. Executive Summary & Objective

### 1.1 Problem Statement
Material engineering deliverables — Material Test Reports (MTRs), Inspection Reports, Welding Procedure Specifications (WPS), Quality Control (QC) certificates — are currently reviewed manually before client submission. Manual QC is slow, inconsistent across reviewers, and prone to missing typos, duplicated data blocks, and contextual inconsistencies. Beyond language-level errors, an internal engineering audit identified a more severe class of risk: **structural and numerical integrity failures** — tables whose totals don't mathematically reconcile, Table-of-Contents page references that drift from actual content, filenames whose revision letter disagrees with the document's own revision sheet, and technical standards cited in the body that are never formally logged in the Reference section (or logged with the wrong edition year). These are exactly the defects that trigger client non-conformance reports (NCRs) and audit findings in regulated engineering deliverables.

### 1.2 Objective
Build a **Document QC & Traceability Audit Web Application** that automates first-pass quality review of engineering documents (PDF/DOCX) using deterministic, non-LLM NLP and structural-extraction techniques. The system flags both **linguistic issues** (typos, grammar, duplication, ambiguity) and **traceability/audit issues** (table math, pagination drift, revision sync, standards traceability), surfacing all findings through a structured split-screen review-and-export workflow.

### 1.3 Why Non-LLM for Phase 1
- **Data Privacy:** Engineering documents often contain client-confidential specifications and cannot be sent to third-party LLM APIs.
- **Cost Predictability:** Rule-based/statistical NLP and deterministic table/regex validation have fixed compute cost; no per-token billing at scale.
- **Determinism & Auditability:** The new CTO-mandated checks (table math, reference drift, revision sync, standard traceability) are inherently deterministic problems — they require exact arithmetic and pattern matching, not probabilistic language generation. An LLM would be slower, more expensive, and *less* trustworthy here than a calculator and a regex.
- **Latency:** Local pipelines process documents in seconds without external API round-trips.

### 1.4 Success Metrics (Phase 1)
| Metric | Target |
|---|---|
| False positive rate on domain terms (post-dictionary tuning) | < 5% |
| Table math validation accuracy (native-text PDFs/DOCX) | ≥ 98% |
| Reference drift detection recall (ToC/LoF/LoT vs actual page) | ≥ 95% |
| Revision mismatch detection (filename vs cover/rev sheet) | 100% (deterministic string match) |
| Standard traceability check coverage (body-cited codes resolved to bibliography) | ≥ 95% |
| Avg. document processing time (20-page PDF) | < 20 sec |
| Reviewer time saved per document (vs. fully manual QC) | ≥ 50% |

---

## 2. User Personas

### 2.1 Primary Persona — QA Engineer ("Priya")
- **Role:** Owns first-pass QC review and remediation before a document is escalated for final sign-off.
- **Goals:** Fast, reliable scan covering both language and structural/audit issues; ability to triage by severity; clean audit trail.
- **Pain Points:** Manually re-checking ToC page numbers after every last-minute page insertion; manually re-adding a row of numbers to confirm a table total; alert fatigue from generic spellcheckers flagging valid engineering terms.
- **Key Interactions:** Reviews flagged issues (linguistic + traceability), accepts/rejects/edits inline, manages document approval status.

### 2.2 Secondary Persona — Material Inspector ("Rahul")
- **Role:** Drafts raw inspection/test reports in the field or lab, often under time pressure, populating data tables (heat numbers, dimensional results, chemical composition).
- **Goals:** Quick self-check before submitting to QA; confidence that table totals and revision metadata are internally consistent before handoff.
- **Pain Points:** Manual arithmetic errors in summary rows; forgetting to update the revision sheet when renaming a file after a client comment cycle.
- **Key Interactions:** Uploads documents, manages/contributes to the Custom Engineering Dictionary.

### 2.3 New Persona — Lead Reviewer ("Arjun")
- **Role:** Final technical authority for audit-critical, client-facing deliverables; accountable to the CTO's engineering audit standards. Typically reviews only *escalated* findings, not every raw issue.
- **Goals:** A single, trustworthy view of every traceability/compliance risk in a document — table math mismatches, pagination drift, revision inconsistencies, uncited or mis-dated standards — without re-deriving them by hand.
- **Pain Points:** Under the current manual process, standards traceability checks (confirming every ASME/API code cited in the body appears in the bibliography with the correct edition year) are the single most time-consuming and error-prone audit step.
- **Key Interactions:** Reviews the "Traceability & Compliance" issue category specifically, overrides/annotates automated findings with audit justification, provides final `APPROVED` / `REVISION_REQUIRED` disposition on audit-critical documents.

### 2.4 Tertiary Persona — QC Administrator ("Admin")
- **Role:** Manages system configuration, dictionary governance, standards-code registry, and user access.
- **Goals:** Ensure dictionary and standards-registry consistency across projects; audit usage; manage retention/compliance settings.
- **Key Interactions:** Approves dictionary/standards-code submissions, configures tolerance thresholds (e.g., rounding tolerance for table math, acceptable page-drift range), views usage analytics.

---

## 3. Core Features & User Flows

### 3.1 Feature Set Overview
| # | Feature | Priority |
|---|---|---|
| F1 | Document Upload (PDF/DOCX, single & batch) | P0 |
| F2 | QC Scan Engine — linguistic (spelling, grammar, duplication, ambiguity) | P0 |
| F3 | Custom Engineering Dictionary (CRUD + governance) | P0 |
| F4 | Split-Screen Review UI (inline annotations, accept/reject) | P0 |
| F5 | Severity Classification & Filtering | P1 |
| F6 | Export (Annotated PDF, Issue Log CSV/XLSX) | P0 |
| **F10** | **Table Math & Traceability Validation (Trace Numbers)** | **P0 — CRITICAL** |
| **F11** | **Reference Drift Detection (ToC/LoF/LoT vs. Pagination)** | **P0 — CRITICAL** |
| **F12** | **Metadata & Revision Sync (Filename vs. Cover/Rev Sheet)** | **P0 — CRITICAL** |
| **F13** | **Standard & Code Traceability (Body Citation vs. Bibliography)** | **P0 — CRITICAL** |
| F7 | Document History & Version Comparison | P1 |
| F8 | Role-Based Access Control | P1 |
| F9 | Analytics Dashboard (org-level QC/audit trends) | P2 |

> F10–F13 are elevated to P0/MVP per the CTO's engineering audit directive — these are the highest-risk defect classes for client NCRs and are treated as **blocking** issues by default (see §3.4 severity model), distinct from the lower-stakes linguistic issue classes.

### 3.2 End-to-End User Flow: Upload → Scan → Review (Split-Screen) → Export

**Step 1 — Upload**
- User uploads a PDF or DOCX (drag-drop or batch); system validates type/size and extracts raw text, layout metadata, **and table structures** (bounding boxes, cell grid, page anchors), preserving position for later annotation overlay.
- Document enters `QUEUED` state.

**Step 2 — Scan (Asynchronous Processing)**
- Backend job orchestrator (Celery/RQ + Redis) runs the full pipeline: linguistic stages (§4.3.1) followed by the four new audit/traceability stages (§4.3.2).
- Each stage emits structured findings to a unified `issues` table, tagged by category (`LINGUISTIC` vs `TRACEABILITY`) and type.
- Document transitions `QUEUED` → `PROCESSING` → `COMPLETED` (or `FAILED`, with per-stage error detail — a failure in `trace_numbers.py` should not block linguistic results from surfacing).

**Step 3 — Review (Split-Screen UI)**
- **Left pane:** rendered document (`pdf.js` / DOCX-to-HTML), with in-place highlights: yellow for linguistic issues, red for traceability/compliance issues.
- **Right pane:** tabbed issue list — **"Language"** tab (Typos, Grammar, Duplicates, Ambiguity) and **"Traceability & Compliance"** tab (Table Math, Reference Drift, Revision Sync, Standards Traceability), each independently filterable/sortable by severity.
- Selecting an issue scrolls and highlights its exact location(s) in the left pane. For **Table Math** findings, both the offending row/column *and* the stated total cell are highlighted simultaneously with the computed vs. stated delta shown inline. For **Reference Drift**, the ToC/LoF/LoT entry and the actual target page are both highlighted with a jump-to-either control.
- Per-issue actions: **Accept Suggestion**, **Reject/Dismiss**, **Edit Manually**, **Add to Dictionary** (linguistic only), **Add to Standards Registry** (traceability only), **Flag for Discussion** (comment thread, visible to Lead Reviewer).
- Bulk actions supported per tab (e.g., "Accept all spelling suggestions above 90% confidence"); traceability issues are **not** eligible for bulk-accept by default (require individual sign-off given audit weight).
- Lead Reviewer role sees the Traceability & Compliance tab pinned first by default and can apply a final disposition per finding (`Justified Exception` / `Requires Correction`).

**Step 4 — Export**
- **Annotated PDF/DOCX**: corrections applied for accepted linguistic issues (tracked-change style for DOCX via `python-docx`); traceability findings rendered as **audit-log comments/callouts** rather than silent edits (these require human correction of source data, not text substitution).
- **Issue Log (CSV/XLSX):** two sheets — `Language_Issues` and `Traceability_Compliance_Issues` — the latter including computed values, stated values, deltas, page references, and Lead Reviewer disposition, structured to serve directly as an audit-trail record.
- Document status updates to `APPROVED` / `REVISION_REQUIRED`.

### 3.3 New Critical Feature Detail

**F10 — Table Math & Traceability Validation (Trace Numbers)**
- Extract every table (native tables via structural parsing; scanned/image tables via OCR + layout heuristics as a degraded-accuracy fallback).
- Parse numeric cells (handling units, thousands separators, and precision) and identify candidate "total" rows/columns via header keyword matching (`Total`, `Sum`, `Subtotal`, `Grand Total`) and positional heuristics (last row/column of a numeric block).
- Recompute row/column sums and compare against the stated total with a **configurable rounding tolerance** (default: ±0.5% or ±1 unit, admin-configurable per project).
- Also cross-checks **narrative-text totals** (e.g., "a total of 42 samples were tested") against the corresponding table's row count using `spaCy` number-entity extraction.
- Flags: `TABLE_MATH_MISMATCH` (computed ≠ stated beyond tolerance), `TOTAL_NOT_FOUND` (informational).

**F11 — Reference Drift Detection (Ref Drift)**
- Parses the Table of Contents, List of Figures, and List of Tables into structured entries: `{label, referenced_page}`.
- Independently determines each entry's **actual** page location via heading/caption detection (font-size and style heuristics from PDF span metadata, or Word style names — `Heading 1/2`, `Caption` — for DOCX).
- Resolves front-matter vs. body page-numbering offsets (roman numeral preliminary pages vs. arabic body pages) before diffing.
- Flags: `REF_DRIFT` where `referenced_page != actual_page`, with the delta reported (helps reviewers spot systemic drift from a single inserted page vs. isolated errors).

**F12 — Metadata & Revision Sync**
- Extracts the revision token from the filename via regex (`Rev[\s\-_]?[A-Z0-9]+`, configurable pattern library for org-specific naming conventions).
- Extracts the document's internal revision status from the cover page and the Revision/Amendment History table (structural table parse + regex on the "Rev" column, taking the latest row).
- Flags `REVISION_MISMATCH` if filename revision ≠ cover page revision ≠ latest revision-sheet entry (three-way check, reported individually so partial mismatches are distinguishable).

**F13 — Standard & Code Traceability**
- Extracts standard/code citations from the document body using a regex + `spaCy` EntityRuler pattern set (e.g., `ASME\s?(Sec\.?|Section)?\s?[IVXLCDM]+`, `API\s?\d{3}`, `ASTM\s?[A-Z]?\d+`, `ISO\s?\d+`).
- Parses the Reference/Bibliography section into structured entries `{code, edition_year}`.
- Cross-references each body citation against the bibliography: flags `STANDARD_NOT_IN_BIBLIOGRAPHY` (cited in body, absent from references) and `EDITION_YEAR_MISMATCH` (present, but the bibliography's edition year doesn't match a year explicitly stated near the body citation, when one is given).
- Maintains an **organization-level Standards Registry** (admin-managed) of known valid code formats to reduce false positives from ambiguous alphanumeric strings.

### 3.4 Severity Model
| Category | Default Severity | Bulk-Accept Eligible |
|---|---|---|
| Table Math Mismatch | Critical | No |
| Reference Drift | High | No |
| Revision Mismatch | Critical | No |
| Standard Traceability | High | No |
| Grammar/Style | Low–Medium | Yes |
| Spelling | Low | Yes |
| Duplicate Data | Medium | Partial |
| Contextual Ambiguity | Medium | No |

---

## 4. Technical Architecture

### 4.1 High-Level Architecture

```
┌─────────────────┐      HTTPS/REST + WebSocket      ┌──────────────────────┐
│   Next.js FE      │ ───────────────────────────────► │   FastAPI Backend      │
│  (Split-Screen     │ ◄─────────────────────────────── │   (API Gateway Layer) │
│   Review UI)        │                                   └──────────┬───────────┘
└─────────────────┘                                              │
                                                                    ▼
                                                        ┌───────────────────────┐
                                                        │  Job Queue (Redis +    │
                                                        │  Celery/RQ Workers)    │
                                                        └───────────┬───────────┘
                                                                    ▼
                          ┌───────────────────────────────────────────────────────────────┐
                          │                  NLP + Traceability Pipeline (Python)            │
                          │                                                                   │
                          │  Stage 0: extract.py  (text, layout, table-grid, font metadata)   │
                          │      ▼                                                            │
                          │  ── Linguistic Branch ──────────  ── Traceability Branch ───────  │
                          │  spellcheck.py (pyspellchecker    trace_numbers.py (table math)   │
                          │    + Custom Dictionary)            ref_drift.py (ToC/LoF/LoT diff) │
                          │  grammar.py (LanguageTool server)  revision_sync.py (filename vs   │
                          │  duplicate.py (RapidFuzz)            cover/rev sheet)              │
                          │  ambiguity.py (spaCy NER + rules)  standard_traceability.py         │
                          │                                      (code regex vs bibliography)  │
                          │                          ▼                                          │
                          │              aggregate.py → unified `issues` records                │
                          └───────────────────────────────────────────────────────────────┘
                                                                    │
                                                                    ▼
                          ┌──────────────────────────────────────────────────────────┐
                          │ PostgreSQL (documents, issues, dictionary, standards_       │
                          │ registry, audit_log)  +  S3/Blob Storage (raw files)         │
                          └──────────────────────────────────────────────────────────┘
```

### 4.2 Frontend (Next.js)
- **Framework:** Next.js 14+ (App Router), TypeScript.
- **Split-Screen Review UI:** resizable two-pane layout (`react-resizable-panels`); left pane renders the document via `pdf.js` (PDF) or server-rendered HTML from `mammoth.js` (DOCX) with coordinate-based highlight overlays keyed to `{page, bbox}` from the issue record; right pane is a tabbed issue browser (Language / Traceability & Compliance) built with `shadcn/ui` Tabs + virtualized list for large issue counts.
- **State:** React Query for server state (scan status polling, issue list); Zustand for in-session review decisions prior to commit.
- **Real-time updates:** WebSocket/SSE for scan progress, including **per-stage** progress (e.g., "Table math validation: 60%") so users see traceability checks running distinctly from linguistic checks.

### 4.3 Backend (Python / FastAPI Microservice)

**4.3.1 Linguistic Pipeline (unchanged from Phase 1 baseline)**
1. `extract.py` — text/layout extraction (`PyMuPDF`/`python-docx`; `Tesseract` OCR fallback).
2. `spellcheck.py` — `pyspellchecker` cross-referenced against the Custom Engineering Dictionary.
3. `grammar.py` — self-hosted `LanguageTool` server via `language-tool-python`.
4. `duplicate.py` — `RapidFuzz` near-duplicate paragraph/table-row detection.
5. `ambiguity.py` — `spaCy` NER + custom EntityRuler for inconsistent terminology (e.g., "316" vs "316L").

**4.3.2 Traceability & Audit Pipeline (new, per CTO audit requirements)**
6. **`trace_numbers.py`** — table extraction (`pdfplumber`/`camelot-py` for native PDFs; DOCX table objects via `python-docx`) → numeric parsing → row/column sum recomputation → tolerance-based comparison against stated totals. Outputs `TABLE_MATH_MISMATCH` records with `computed_value`, `stated_value`, `delta`.
7. **`ref_drift.py`** — ToC/LoF/LoT structured parse → heading/caption/page-anchor detection (font-size hierarchy from `PyMuPDF` span metadata, or DOCX style names) → page-numbering offset resolution → diff. Outputs `REF_DRIFT` records with `referenced_page`, `actual_page`.
8. **`revision_sync.py`** — filename regex parse → cover page regex parse → revision-history table parse (via the same table extraction used in `trace_numbers.py`) → three-way comparison. Outputs `REVISION_MISMATCH` records identifying which of the three sources disagree.
9. **`standard_traceability.py`** — regex + `spaCy` EntityRuler extraction of cited standards/codes from body text → Bibliography/Reference section structured parse → cross-reference against extracted entries and the org `standards_registry` table. Outputs `STANDARD_NOT_IN_BIBLIOGRAPHY` / `EDITION_YEAR_MISMATCH` records.
10. **`aggregate.py`** — normalizes all linguistic + traceability findings into the unified `issues` schema: `{issue_id, doc_id, category [LINGUISTIC|TRACEABILITY], type, page, span_or_bbox, original_value, expected_value, delta, suggestion, confidence, severity}`.

- **Task Orchestration:** Celery chain/group — linguistic and traceability branches run as **parallel groups** (independent of each other) after the shared `extract.py` stage, then join at `aggregate.py`, minimizing total wall-clock time.
- **Fault isolation:** each script (`trace_numbers.py`, `ref_drift.py`, etc.) runs as an independent Celery subtask with its own try/except boundary — a parsing failure in one (e.g., a malformed table) is logged and surfaced as a `STAGE_FAILED` informational issue rather than failing the entire scan.
- **Database additions:** new `standards_registry` table (`code_pattern`, `description`, `org_scope`); `documents` table gains `filename_revision`, `detected_cover_revision` columns for quick-reference/reporting.

### 4.4 Key API Endpoints (Representative, additions in bold)
```
POST   /api/v1/documents/upload
GET    /api/v1/documents/{id}/status
GET    /api/v1/documents/{id}/issues?category=linguistic|traceability
PATCH  /api/v1/issues/{id}/decision
POST   /api/v1/dictionary/terms
GET    /api/v1/dictionary/terms?scope=project:{id}
PATCH  /api/v1/dictionary/terms/{id}/approve
GET    /api/v1/documents/{id}/export?format=pdf|xlsx
**GET    /api/v1/documents/{id}/traceability-summary**      # counts by type, for Lead Reviewer dashboard
**POST   /api/v1/standards-registry**                        # admin: register a valid code pattern
**PATCH  /api/v1/issues/{id}/disposition**                   # Lead Reviewer: Justified Exception / Requires Correction
```

### 4.5 Non-Functional Requirements
- **Data Privacy:** All processing on-premise/self-hosted; no document content transmitted to third-party APIs.
- **Accuracy Boundary (explicit):** Table math and reference-drift detection accuracy is materially lower on scanned/image-only PDFs (OCR-dependent) than on native-text PDFs/DOCX — this should be surfaced to users as a confidence indicator per document, not silently degraded.
- **Scalability:** Stateless FastAPI instances behind a load balancer; Celery worker pools scale independently per pipeline branch (traceability extraction is more CPU-intensive than linguistic checks and may warrant its own worker pool).
- **Observability:** Per-stage timing and failure-rate metrics (Prometheus/Grafana), with traceability stages tracked separately given their audit-criticality.
- **Security & Audit:** Encrypted storage at rest, RBAC, immutable audit trail of every traceability finding and its disposition (required for CTO audit compliance — dispositions should not be editable after document `APPROVED` status, only appendable).

---

## 5. MVP Scope & Phase 2 Roadmap

### 5.1 MVP Scope (Phase 1 — In Scope)
- Single/batch PDF & DOCX upload
- Full linguistic pipeline: spelling, grammar, duplicate detection, contextual ambiguity
- **Table Math & Traceability Validation (F10)** — native-text PDFs/DOCX
- **Reference Drift Detection (F11)** — ToC/LoF/LoT vs. actual pagination
- **Metadata & Revision Sync (F12)** — filename/cover/rev-sheet three-way check
- **Standard & Code Traceability (F13)** — body citation vs. bibliography, with org Standards Registry
- Custom Engineering Dictionary with propose/approve workflow
- Split-Screen Review UI with Language / Traceability & Compliance tabs
- Export: annotated document + two-sheet issue log (Language, Traceability & Compliance)
- RBAC covering Inspector, QA Engineer, Lead Reviewer, Admin
- Document status tracking incl. Lead Reviewer disposition on traceability findings

### 5.2 Explicitly Out of Scope for MVP
- LLM-based semantic analysis or generative rewriting
- Table math/reference-drift validation on scanned/image-only documents beyond best-effort OCR (flagged as low-confidence, not blocked)
- Cross-document traceability (e.g., verifying a standard cited in Document A against a project-wide standards log spanning multiple documents)
- Automated document generation/authoring
- Multi-language support (English-only for MVP)
- Mobile app (responsive web only)

### 5.3 Phase 2 — Future Enhancements (LLM-Readiness)
The architecture keeps LLM capability as an **optional, modular enhancement layer**, added without re-architecting the deterministic core:
- **Hybrid Ambiguity & Standards Review:** Route only low-confidence spans (ambiguous terminology, or a standard citation the regex/EntityRuler can't confidently parse) to a self-hosted or zero-data-retention-contracted LLM for deeper semantic review.
- **Complex Table Handling:** Extend `trace_numbers.py` to handle merged cells, multi-page tables, and nested subtotals — a Phase 2 investment given the structural complexity vs. Phase 1's flat-table baseline.
- **Cross-Document Traceability:** Extend `standard_traceability.py` and `ref_drift.py` logic across a full project's document set (e.g., confirming a grade/standard cited in an MTR matches its referencing inspection report).
- **OCR-Enhanced Table Math:** Improve scanned-document table extraction accuracy via layout-aware OCR models, closing the accuracy gap flagged in §4.5.
- **Feedback Loop / Active Learning:** Use Lead Reviewer disposition history (`Justified Exception` vs `Requires Correction`) to auto-tune tolerance thresholds and reduce false positives over time.
- **Natural-Language Standards Ingestion:** Auto-populate the Standards Registry by parsing newly published ISO/API/ASME standards documents.

**Architectural Note:** Because §4.3.2's four traceability scripts (`trace_numbers.py`, `ref_drift.py`, `revision_sync.py`, `standard_traceability.py`) are independent, deterministic Celery subtasks, any of them can later be *supplemented* — not replaced — by an LLM-assisted verification step for the ambiguous edge cases they can't resolve, while the audit-critical, explainable core (exact sums, exact page numbers, exact string matches) remains non-LLM by design.

---

*End of Document*
