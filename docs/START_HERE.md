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
- **Current next ticket**: Add HTTP/browser coverage for profile editing and project assignment,
  complete manual visual review of rendered PNG pagination/margins, then continue production
  release hardening and deployment validation.
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
- **Latest account-management checkpoint**: Added lead/superuser-protected user management
  endpoints for listing accounts with owned-document counts, creating engineer/lead accounts,
  enabling/disabling accounts, and resetting passwords. Added the `/admin/users` interface with
  role guard, user table, create-user modal, status actions, and password reset flow.
- **Latest identity/workspace checkpoint**: Added authenticated profile editing at
  `PATCH /api/v1/auth/me` and `/settings/profile`, self-service password management, and
  normal page scrolling in the application shell.
- **Latest project-assignment checkpoint**: Added nullable `projects.assigned_to_id`, migration
  `20260910_0009_project_assignment`, lead-only project assignment, user project filtering,
  engineer project creation, creator/assignee names, document counts, and assigned visibility.
- **Latest document-assignment checkpoint**: Added `documents.assigned_to_id`, migration
  `20260910_0010_document_assignment`, engineer claim with WIP=1 enforcement, lead assignment with
  override, assignment metadata in document responses, and assigned-task project inspection.
- **Latest admin UI checkpoint**: Added `Lihat Projects` to `/admin/users` with a project modal and
  direct links to assigned project registers and assigned document workflow/status details.
- **Latest review UI checkpoint**: Rebuilt `/documents/{id}/review` as an isolated three-zone
  workspace with fixed top navigation/footer and independent PDF/issue scrolling.
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
  - Frontend checkpoint: **50 passed, typecheck passed, lint passed, production build passed**.
  - Backend checkpoint: **400 passed, 1 skipped**; the skipped Redis vertical-slice test is opt-in
    via `RUN_REDIS_INTEGRATION=1`, not evidence that the Redis service is unavailable.
  - Local Docker checkpoint: PostgreSQL and Redis are both healthy. The database is currently at
    Alembic revision `20260910_0010 (head)`.
  - Latest export/reference regression: **55 passed**, Ruff passed, and `git diff --check` passed.
  - Docker visual smoke: DOCX conversion passed, 16 PDF pages produced, 16 PNG pages rendered, and all pages contain text.
- **Remaining Work**:
  - Apply `20260910_0009_project_assignment` to the local/disposable PostgreSQL database and verify
    the assignment schema.
  - Add HTTP coverage for profile update, email uniqueness, project assignment, assigned visibility,
    engineer project creation, and owner-name responses.
  - Add browser/e2e coverage for `/settings/profile`, the admin project modal, and assignment UI.
  - Regenerate `frontend/src/lib/api-schema.d.ts` from the finalized OpenAPI contract.
  - Decide and enforce self-disable, lead demotion, and last-active-admin protection policies.
  - Complete manual visual inspection of the 16 rendered report PNGs, then rerun all quality gates.
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

## Immediate Next Work

1. Apply `20260910_0009_project_assignment` to PostgreSQL; PostgreSQL and Redis are already healthy
   in the local Docker stack.
2. Run the opt-in Redis vertical-slice test with `RUN_REDIS_INTEGRATION=1` using Docker service
   networking or a configured local API/worker environment.
3. Add backend HTTP tests for profile update, duplicate email handling, project assignment,
   `user_id` filtering, and engineer/lead authorization boundaries.
4. Add frontend tests for profile save/error states and the `/admin/users` project modal.
5. Regenerate OpenAPI/TypeScript contracts and remove temporary handwritten API types where safe.
6. Run the full backend suite, frontend suite, production build, and Docker smoke deployment.
7. Perform manual UI review at desktop and mobile widths, especially long admin tables and modal scrolling.

## Commitments & Rules

- **Zero External AI / LLM APIs**: All analysis, reports, and evidence are 100% deterministic.
- **Confidentiality**: Never commit client or sample documents; commit only synthetic/de-identified fixtures.
- **Local Commits Only**: Do not execute `git push`.
