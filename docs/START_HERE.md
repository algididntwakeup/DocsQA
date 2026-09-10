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
- **Latest validation**: Docker worker is running LibreOffice 25.2.3.2. Canonical executive
  DOCX converted to a 16-page Letter PDF and all 16 pages rendered to PNG successfully.
- **Current next ticket**: Finish the release hardening queue below: regenerate the frontend
  OpenAPI contract, add project/workflow UI coverage, replace browser token storage with a
  production session cookie, then complete manual visual review of rendered PNG
  pagination/margins and rerun the full quality gates.
- **Latest implementation checkpoint**: Budinski now has a flat deterministic 41-item rule
  contract (`items`, `baseline_score`, `group_averages`) with Group III/IV rules. DOCX
  scorecard rendering prefers that flat contract and retains legacy grouped-field
  compatibility. The review workspace loads all finding pages, follows SSE completion
  events, and reflects current severity behavior.
- **Latest export checkpoint**: Production DOCX export now uses the ten-section executive
  report through `assessment_from_document_findings()` and `generate_ale_review_docx()`.
  `ReportSynthesizer` and `docx_styler` provide deterministic narrative and XML styling;
  the older `services/report.py` builder remains compatibility-only.
- **Latest multi-user checkpoint**: Added JWT login, engineer/lead user roles, project-scoped
  document listing/upload, owner and lead workflow transitions, project dashboard cards,
  project document tables, and review-workspace workflow status/actions. Existing review viewer
  and issue-panel internals remain protected.
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
  - Frontend checkpoint: **42 passed, typecheck passed, lint passed**.
  - Focused backend checkpoint: Budinski evaluator, rule engine, schema, pipeline, and export tests pass.
  - Latest export/reference regression: **55 passed**, Ruff passed, and `git diff --check` passed.
  - Docker visual smoke: DOCX conversion passed, 16 PDF pages produced, 16 PNG pages rendered, and all pages contain text.
- **Remaining Work**:
  - Regenerate `frontend/src/lib/api-schema.d.ts` from the current backend OpenAPI contract and
    remove any temporary local type extensions that become redundant.
  - Add frontend tests for login, project cards, project document filtering/upload, and review
    workflow action visibility and state transitions.
  - Add backend/API integration coverage for project visibility, lead filters, project-scoped
    upload, and JWT-protected workflow transitions.
  - Replace `localStorage` JWT persistence with a secure, HttpOnly, SameSite session cookie before
    production deployment; define logout, expiry, and unauthorized-request behavior.
  - Complete manual visual inspection of the 16 rendered report PNGs for pagination and margins,
    then rerun the backend and frontend quality gates after any changes.
- **Never push to GitHub**; the owner pushes. Local commits are allowed only after quality gates pass.

## Source precedence

1. `docs/PRODUCT_SPEC.md` — product behavior, scope, and non-goals.
2. `docs/REPORT_SPEC.md` — deterministic DOCX review report structure.
3. `docs/UI_SPEC.md` — review workspace, curation UI, and export panels.
4. `docs/ARCHITECTURE.md` — extraction, evidence, and report generators.
5. `docs/DELIVERY_PLAN.md` — active delivery roadmap.
6. `docs/TEST_CORPUS.md` — synthetic and de-identified fixture policies.
7. `backend/openapi.json` — frontend/backend wire contract.
8. `docs/AGENT_HANDOFF.md` — implementation decisions and protected contracts from recent work.

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
