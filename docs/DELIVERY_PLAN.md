# Delivery Plan & Milestone Tracking

## Phase 1: Core Foundation & Rules Codification (Completed)
- [x] **Milestone 1: Report Curation & Schema Migration**
  - Replaced approval/audit workflow with Report Curation model.
  - Implemented Reference Pack, Rule Pack, and Standards Traceability models.
- [x] **Milestone 2: Kenneth G. Budinski Grading Engine (Appendix 12)**
  - Codified Budinski's 4 standing baseline measures (purpose/objective distinction, repeatable procedure, valid conclusions, actionable recommendations).
  - Codified 41 scoring criteria across Group I (Technical Content), Group II (Style), Group III (Report Mechanics), and Group IV (Conclusions & Craft).
  - Automated detection of critical blockers (definition contradictions, unrecorded document revisions).
- [x] **Milestone 3: Document Layout & Typography Diagnostics**
  - Built `DocumentLayoutInspector` utilizing PyMuPDF block/span geometry.
  - Detected cross-page sentence fragmentation (`"Table 6-3 and"` split across page boundaries).
  - Detected narrative text misclassified as bold headings (`"Based on..."`).
  - Audited uncontrolled document pages lacking running header/footer document numbers (21 landscape appendix pages).
- [x] **Milestone 4: Review-ALE DOCX Report Export Engine**
  - Generated complete 10-section report matching "Review of Asset Life Extension Study" (Review-ALE-Grissik).
  - Implemented callout boxes with thick accent borders, XML table styling (`cantSplit`, `tblHeader`), dynamic page numbers, and custom scoring tables.

## Phase 2: Pipeline Integration & Real-Fixture Validation (Completed)
- [x] **Milestone 5: Real-World E2E Test Suite (`test_e2e_mepg_review.py`)**
  - Automated full scan of `docs/testcase/05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf` (56 pages).
  - Verified detection of Blocker 1 (Criticality 2 band contradiction: 6–14 yrs vs 0–6 yrs).
  - Verified detection of Blocker 2 (Revision mismatch: Rev A on cover vs Rev B in filename).
  - Verified 1 of 4 baseline pass (`1/4`) and scorecard group averages.
  - Verified 10-section DOCX export integrity and REVIEWSCORE machine-readable summary.
- [x] **Milestone 6: Issue Schemas, Severity Levels, Pipeline & Contract Synchronization**
  - Expanded `IssueCategory` to include `LAYOUT` and `BUDINSKI` alongside legacy categories.
  - Added `BLOCKER` as topmost severity level with backward-compatible aliases.
  - Migrated `Issue` model `category` and `severity` to `String(50)` for migration safety.
  - Codified 6 canonical pipeline stages (`EXTRACTING`, `LAYOUT_INSPECTION`, `BUDINSKI_AUDIT`, `STANDARDS_CHECK`, `LINGUISTIC_CHECK`, `AGGREGATING`) with uniform SSE stage tracking. `STANDARDS_CHECK` is explicitly skipped until a licensed, governed rulebook exists; internal citation/bibliography checks remain enabled.
  - De-prioritized linguistic findings to cap severity at `MINOR`.
  - Synchronized OpenAPI 3.1 specification (`openapi.json`) and TypeScript contracts (`api-schema.d.ts`).

## Phase 3: Deployment & Hardening (Upcoming)
- [ ] **Milestone 7: Docker Headless Visual Validation**
  - [x] Compose and backend image now verify that `soffice --headless --version` is available in the worker.
  - [x] Added `backend/scripts/verify_libreoffice.py` for deterministic DOCX-to-PDF smoke validation.
  - [x] Run the LibreOffice smoke command on Docker Desktop; worker reports LibreOffice 25.2.3.2.
  - [ ] Render the generated PDF to page PNGs and inspect pagination/margins.
  - [ ] Test pagination fidelity and margin alignment across platforms.
