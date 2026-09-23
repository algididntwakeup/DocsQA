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
- **Latest BIMA authentication checkpoint**: Added dual BIMA authentication with credential
  login (`/api/auth/login`) and one-click SSO (`/sso/authorize` -> `/api/sso/verify`). Both flows
  JIT-provision or synchronize PRISM users, map BIMA roles to PRISM roles, issue the internal
  JWT cookie session, and support local-password fallback for emergency accounts. Migration
  `20260916_0013_bima_identity` adds nullable SSO identity/profile fields. Docker verification:
  API, worker, frontend, PostgreSQL, and Redis healthy; BIMA login flow tested successfully.
- **Latest deployment/project-master checkpoint**: Browser API calls now use same-origin
  `/api/v1` through the Next.js rewrite proxy and no longer depend on a compiled public API host.
  Added environment-driven CORS and corporate-domain routing, BIMA project master synchronization
  (`POST /api/v1/projects/sync-bima`), project identity migration `20260916_0014_bima_projects`,
  and the lead/superuser `Tarik Proyek BIMA` action.
- **PRISM deployment identity**: Production configuration uses `APP_NAME=PRISM - Document
  Assurance Platform`, `https://prism.reksolindo.co.id`, and BIMA client ID `prism`. Compose keeps
  its existing internal project name to preserve PostgreSQL/Redis volume continuity.
- **Latest PRISM transition checkpoint**: Four pillars landed together — (1) BIMA master data now
  ingests `GET /api/projects` **and** `GET /api/users` through a strict adapter
  (`backend/services/bima_adapter.py`) that validates before any write and upserts matched solely
  on `projects.bima_project_id`; project membership persists in `project_members` (migration
  `20260923_0015_project_members`, the current database head) and grants **read-only** project and
  document visibility to member engineers. (2) Network sanitization: browser requests stay
  same-origin `/api/v1`, the SSR/rewrite default is `http://backend:8000` with a Compose `backend`
  network alias, corporate `CORS_ORIGIN_REGEX` and `frame-ancestors` cover `*.reksolindo.co.id`,
  and the BIMA SSO host comes from `NEXT_PUBLIC_BIMA_BASE_URL`. (3) The PDF.js viewer keeps
  continuous wheel/pinch zoom and gains left-button drag panning over one shared canvas/highlight
  coordinate surface. (4) UI revamp: Plus Jakarta Sans, shadcn semantic light/dark tokens with a
  working theme toggle, `Card`/`Table`/`Resizable` primitives, `h-16` app shell with `max-w-7xl`
  gutters, and a resizable review workspace inside the shared shell.
- **Latest project-assignment checkpoint**: Added nullable `projects.assigned_to_id`, migration
  `20260910_0009_project_assignment`, lead-only project assignment, user project filtering,
  engineer project creation, creator/assignee names, document counts, and assigned visibility.
- **Latest document-assignment checkpoint**: Added `documents.assigned_to_id`, migration
  `20260910_0010_document_assignment`, engineer claim with WIP=1 enforcement, lead assignment with
  override, assignment metadata in document responses, and assigned-task project inspection.
  Fixed HTTP 500 in project assignment relationship refresh (`session.refresh(project, attribute_names=...)`),
  resolved `mark_document_reviewed` test fixture permissions, and updated Kanban WIP=1 state machine (Cases A–E)
  with formal Indonesian tooltips and direct review links in `ProjectDocumentTable` (see `docs/ASSIGNMENT_WIP_FIX_PLAN.md`).
- **Latest stabilization checkpoint**: Runtime ALE/sample report fallbacks are isolated to a test-only canonical fixture; assignment/claim rollback and nullable relationship serialization are hardened; PDF render cancellation and cleanup are explicit; project registers poll every 3 seconds and gate workspace access until terminal processing. Verification: frontend TypeScript, changed-file ESLint, 52 Vitest tests, and production build passed. Backend pytest remains blocked in the current environment because `pytest` is not installed.
- **Latest project lifecycle checkpoint**: Lead engineers and superusers can finish a project after all documents reach terminal processing, which disables assignment, upload, claim, review workflow transitions, and finding curation while preserving workspace viewing and DOCX/PDF export. Empty projects can be deleted safely; projects containing documents are protected from deletion. Lifecycle persistence uses migration `20260914_0012_project_lifecycle`.
- **Latest admin UI checkpoint**: Added `Lihat Projects` to `/admin/users` with a project modal and
  direct links to assigned project registers and assigned document workflow/status details.
- **Latest review UI checkpoint**: Rebuilt `/documents/{id}/review` as a workspace inside the
  shared `AppShell` (`h-[calc(100dvh-4rem)]`) with a document header card, a resizable
  document/findings body at desktop widths, and a mobile pane switcher.
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
  - Frontend checkpoint: **66 passed (17 test files), typecheck passed, lint passed (0 errors),
    production build passed** with all 14 routes compiled.
  - Backend checkpoint: **440 passed, 1 skipped**. The skipped Redis vertical-slice test is opt-in
    via `RUN_REDIS_INTEGRATION=1`, not evidence that the Redis service is unavailable.
  - Backend `mypy` is clean across `api`, `services`, `core`, and `models` (51 source files).
  - Known environment-only failure: `tests/test_contract.py::test_validation_error_uses_problem_details`
    fails when a foreign PostgreSQL occupies host port 5432 with different `docqc` credentials. It
    passes against a disposable migrated database; it is not a code regression.
  - `alembic check` reports pre-existing schema drift (`issues.category`/`severity` column widths,
    a missing `ix_issues_document_id`, and the `uq_users_email` constraint) that predates the PRISM
    work. Migration `20260923_0015_project_members` itself applies and reverses cleanly.
  - Local Docker checkpoint: PostgreSQL and Redis are both healthy. The database head is Alembic
    revision `20260923_0015_project_members`.
  - Latest export/reference regression: **55 passed**, Ruff passed, and `git diff --check` passed.
  - Docker visual smoke: DOCX conversion passed, 16 PDF pages produced, 16 PNG pages rendered, and all pages contain text.
  - BIMA auth focused tests: **2 passed**; production frontend build and lint passed after adding
    the SSO callback Suspense boundary; backend image includes `httpx`.
- **Remaining Work**:
  - Add HTTP coverage for profile update, email uniqueness, project assignment, assigned visibility,
    engineer project creation, document claim, and owner-name responses.
  - Add browser/e2e coverage for `/settings/profile`, the admin project/task modal, assignment UI,
    and the review workspace resize/theme behavior (a Playwright spec exists at
    `frontend/e2e/review-workspace.spec.ts` but has not been executed; it needs a running dev server).
  - Regenerate `frontend/src/lib/api-schema.d.ts` from the finalized OpenAPI contract.
  - Resolve the pre-existing `alembic check` drift so the migration chain is authoritative.
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

1. Run the opt-in Redis vertical-slice test with `RUN_REDIS_INTEGRATION=1` using Docker service
   networking or a configured local API/worker environment.
2. Add backend HTTP tests for profile update, duplicate email handling, project assignment,
   `user_id` filtering, and engineer/lead authorization boundaries.
3. Add frontend tests for profile save/error states, the `/admin/users` project/task modal, and
   review workspace layout behavior.
4. Regenerate OpenAPI/TypeScript contracts and remove temporary handwritten API types where safe.
5. Run the full backend suite, frontend suite, production build, and Docker smoke deployment.
7. Perform manual UI review at desktop and mobile widths, especially long admin tables and modal scrolling.

## Commitments & Rules

- **Zero External AI / LLM APIs**: All analysis, reports, and evidence are 100% deterministic.
- **Confidentiality**: Never commit client or sample documents; commit only synthetic/de-identified fixtures.
- **Local Commits Only**: Do not execute `git push`.
