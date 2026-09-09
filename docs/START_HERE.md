# START HERE — DocsQA Execution Index

This is the central index every new agent must read in full. Repository state always overrides stale prose.

## Current checkpoint

- **Product Orientation**: Reoriented from an approval/audit system to a deterministic engineering-document review report generator.
- **Core Deliverables**:
  1. Formal DOCX review report (`python-docx`).
  2. Annotated source PDF with highlight bounding boxes and notes (`pypdf`).
- **Standards-pack boundary**: External API/ASME/ISO packs are intentionally disabled. The
  `STANDARDS_CHECK` stage emits `SKIPPED`; only document-internal citation and bibliography
  consistency checks remain in scope until a licensed, governed rulebook is supplied.
- **Latest validation**: Docker worker is running LibreOffice 25.2.3.2 and the DOCX-to-PDF
  smoke path is available. The remaining gate is PNG inspection plus the deferred full test suite.
- **Current next ticket**: Render the generated review PDF to page PNGs, inspect pagination and
  margins, then run the backend and frontend quality suites.
- **Curation Workflow**:
  - Finding curation is strictly binary inclusion (`included_in_report: bool`, default `True`) and an optional engineering clarification (`reviewer_note: str | None`).
  - Completely removed: issue decisions (`ACCEPTED`/`REJECTED`), lead dispositions, audit trail events, and bulk decision workflows.
- **Delivery Plan Progress**:
  - **Item 1 (Complete)**: Replaced approval and audit workflow with report curation across database models, Alembic migration `20260907_0006_report_curation`, FastAPI endpoints, and UI.
  - **Item 2 (Complete)**: Added deterministic DOCX report builder (`backend/services/report.py`), report preview endpoint/modal, and restricted export panel to DOCX and annotated PDF.
  - **Item 3 / Layout Diagnostics (Complete)**: Added `DocumentLayoutInspector` (`backend/services/layout_inspector.py`) and schemas in `backend/schemas/extraction.py` detecting cross-page sentence breaks, style/typography misclassification, void pages/unintended whitespace, uncontrolled pages, and front matter navigation drift.
  - **Item 4 / Budinski Evaluator (Complete)**: Codified Kenneth G. Budinski's *Engineers' Guide to Technical Writing* (Appendix 12) grading engine (`backend/services/budinski_evaluator.py`, `backend/schemas/budinski.py`) assessing 4 baseline measures, 41 scorecard items, definition contradiction blockers, and demonstration rewrites.
  - **Item 5 / Review-ALE DOCX Engine (Complete)**: Built 10-section Word review report generator matching *Review of Asset Life Extension Study* (Review-ALE-Grissik) in `backend/services/export.py`.
  - **Item 6 / Real-World E2E Test (Complete)**: Verified full scan and report generation for `docs/testcase/05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf` in `backend/tests/test_e2e_mepg_review.py`.
  - **Item 7 / Schema & Pipeline Synchronization (Complete)**: Synchronized `IssueCategory` (`LAYOUT`, `BUDINSKI`), `Severity` (`BLOCKER`), 6 canonical pipeline stages, SSE progress streaming, linguistic finding de-prioritization, OpenAPI 3.1 specification, and frontend TypeScript contracts.
- **Quality Status**:
  - Historical baseline before the latest pipeline/report changes: **349 passed, 1 skipped, 0 failed**.
  - Current Docker gate: LibreOffice is available in the worker; full backend/frontend rerun remains pending.
- **Never push to GitHub**; the owner pushes. Local commits are allowed only after quality gates pass.

## Source precedence

1. `docs/PRODUCT_SPEC.md` — product behavior, scope, and non-goals.
2. `docs/REPORT_SPEC.md` — deterministic DOCX review report structure.
3. `docs/UI_SPEC.md` — review workspace, curation UI, and export panels.
4. `docs/ARCHITECTURE.md` — extraction, evidence, and report generators.
5. `docs/DELIVERY_PLAN.md` — active delivery roadmap.
6. `docs/TEST_CORPUS.md` — synthetic and de-identified fixture policies.
7. `backend/openapi.json` — frontend/backend wire contract.

If these conflict, record the conflict. Do not silently blend them.

## Document map

| File | Use when |
|---|---|
| `docs/PRODUCT_SPEC.md` | Resolving product scope, rules, and boundaries |
| `docs/REPORT_SPEC.md` | Building or validating DOCX review report sections |
| `docs/UI_SPEC.md` | Updating review workspace, findings panel, or modals |
| `docs/ARCHITECTURE.md` | Pipeline, analyzer, evidence, or storage design |
| `docs/DELIVERY_PLAN.md` | Tracking milestones and roadmap execution |
| `docs/TEST_CORPUS.md` | Adding or managing test fixtures and documents |
| `docs/design_system.md` | Styling components according to design tokens |

## Required quality commands

```powershell
# Backend quality gate
Set-Location backend
.\scripts\quality.ps1

# Frontend quality gate
Set-Location ..\frontend
npm run generate:api
npm run typecheck
npm run lint
npm run test
npm run build
```

## Commitments & Rules

- **Zero External AI / LLM APIs**: All analysis, reports, and evidence are 100% deterministic.
- **Confidentiality**: Never commit client or sample documents; commit only synthetic/de-identified fixtures.
- **Local Commits Only**: Do not execute `git push`.
