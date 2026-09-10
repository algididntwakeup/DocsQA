# Agent Handoff

This file records implementation decisions that must not be reverted or duplicated by future agents. Read it after `docs/START_HERE.md` before changing the review pipeline or workspace.

## Current State

- The product is a deterministic engineering-document review tool. Do not introduce LLM, external AI, approval, disposition, or audit-trail workflows.
- Findings use binary report curation: `included_in_report` plus an optional `reviewer_note`.
- The canonical pipeline stages are `EXTRACTING`, `LAYOUT_INSPECTION`, `BUDINSKI_AUDIT`, `STANDARDS_CHECK`, `LINGUISTIC_CHECK`, and `AGGREGATING`.
- `STANDARDS_CHECK` is skipped for external standards packs until a licensed, governed rulebook exists. Internal citation and bibliography checks remain active.

## Budinski Contract

- `backend/services/budinski_evaluator.py` contains the deterministic 41-item evaluator.
- `backend/schemas/budinski.py` contains `EvaluationContext`, `ScorecardEntry`, `BudinskiScorecard.items`, `baseline_score`, and `group_averages`.
- The 41 canonical items are distributed as Group I (9), Group II (11), Group III (11), and Group IV (10).
- Group III rules include purpose, report format, referenced work, standards citations, and repeatable detail. Group IV rules include conclusion clarity, reference attribution, and sentence/paragraph length.
- Legacy grouped scorecard fields remain for compatibility. Do not remove them unless all persisted artifacts and export fixtures have migrated.
- Legacy aliases such as `format_stated`, `adequate_detail_to_repeat`, and `layout_and_whitespace` may be accepted by compatibility dispatch, but must not create duplicate canonical items.

## Export Contract

- `backend/services/export.py` must render scorecard details from `BudinskiScorecard.items` when flat items are present.
- Group averages and baseline values must come from the scorecard's computed data, not document-specific constants or sample-report prose.
- Legacy grouped scorecards are still supported for existing fixtures and persisted data.
- `backend/services/docx_styler.py` owns reusable XML styling primitives: cell shading,
  cell margins, full-width callouts, repeating table headers, and document defaults.
- `backend/services/report_synthesizer.py` owns deterministic executive narrative synthesis
  for summary judgement, bottom line, baseline rows, blockers, major findings, language
  rows, demonstration rewrite, and praise. It must not call external AI or LLM services.
- Production DOCX export in `backend/api/documents.py` adapts persisted issues and
  `artifacts/{document_id}/budinski_scorecard.json` through
  `assessment_from_document_findings()` and then calls `generate_ale_review_docx()`.
- Persisted scorecards created with Pydantic `model_dump_json()` include computed fields
  such as `average`, `score`, `summary_ratio`, `baseline_score`, and `group_averages`.
  `_load_scorecard()` in `export.py` strips only those derived fields before strict model
  validation; do not replace it with direct validation of the raw artifact.
- The executive DOCX has ten narrative sections: title/metadata, summary/bottom line,
  baseline measures, blockers, next revision actions, language/mechanics, demonstration
  rewrite, Budinski scorecard, praise, and limits/REVIEWSCORE.
- `backend/services/report.py` remains a compatibility builder for existing direct callers
  and reference-pack tests. Do not route production DOCX export back to its raw findings
  table path without an explicit migration decision.
- Do not reintroduce sample-specific strings such as client names, asset names, dates, component counts, or report identifiers into the export service.
- DOCX export supports `include_minors`; the default remains concise by excluding minor and informational findings from annotated PDF selection unless requested.

## Frontend Workspace Contract

- `frontend/src/components/review/review-workspace-view.tsx` loads all issue pages through `listAllDocumentIssues()` and subscribes to SSE completion events while processing.
- `frontend/src/components/review/split-screen-viewer.tsx` owns the document viewer, issue curation, report preview, dictionary, and export actions.
- The default findings tabs are `Budinski & Layout Audit`, `Standards Audit`, and `Language`. `BUDINSKI` and `LAYOUT` findings belong to the first tab.
- Current workspace status banners cover `QUEUED`, `PROCESSING`, `COMPLETED_WITH_WARNINGS`, and `FAILED` without inventing scorecard data.
- The `/documents` dashboard subscribes to SSE for active documents, updates rows without reload, and retains five-second polling as a fallback. Active rows use a pulse indicator and the `Live monitoring active` banner.
- `DocumentRead` currently exposes metadata only. It does not expose the persisted `BudinskiScorecard`; do not add baseline or Group I-IV values to the workspace until a backend endpoint/response contract exposes them.
- Export controls are buttons using `frontend/src/lib/download.ts`, not direct anchor links, so asynchronous download errors can be surfaced consistently.
- The project dashboard lives under `/projects` and `/projects/{id}`. Project cards and the
  project document table are separate from the review workspace.
- `review-workspace-view.tsx` owns the isolated workflow status strip and workflow action bar;
  `split-screen-viewer.tsx`, the PDF viewer, highlight overlay, issue panel, issue card, and
  export modal remain protected internals.
- Workflow actions call `/documents/{id}/mark-reviewed`, `/verify`, and `/request-revision` and
  update the document state from the response without a full-page reload.
- Frontend authentication uses the HttpOnly `access_token` cookie with `credentials: "include"`.
  The API client redirects 401 responses to `/login`; do not reintroduce JWT storage in
  `localStorage`.

## Multi-User API Contract

- `POST /api/v1/auth/login` returns a bearer token and user role; `GET /api/v1/auth/me` returns
  the current user.
- `GET /api/v1/projects` lists visible projects. `GET /api/v1/projects/{project_id}/documents`
  applies engineer isolation and lead-only engineer/date/blocker filters.
- `POST /api/v1/projects` can be used by any authenticated user. Project responses include
  `created_by_name`, `assigned_to_id`, `assigned_to_name`, `total_documents`, and `status`.
- `PATCH /api/v1/projects/{project_id}/assign` is lead/superuser-only and accepts an active user's
  UUID or `null`. `GET /api/v1/projects?user_id=...` returns projects assigned to that user.
- `POST /api/v1/projects/{project_id}/documents/upload` assigns the uploaded document to the
  project and current user.
- Engineer owners can mark their own document reviewed. Lead engineers can verify or request
  revision. Do not broaden these permissions in the UI without changing backend authorization.
- `SUPERUSER` is an authorization role accepted by `require_lead` and `require_user_manager`.
  It is not creatable through the user-management API; managed account creation accepts only
  `ENGINEER` and `LEAD_ENGINEER`.
- `GET /api/v1/auth/users` returns `UserManagementRead` entries with
  `total_documents_owned`. `POST /api/v1/auth/users` creates an account from a temporary
  password. `PATCH /api/v1/auth/users/{user_id}/status` changes `is_active`, and
  `POST /api/v1/auth/users/{user_id}/reset-password` replaces the bcrypt password hash.
- `PATCH /api/v1/auth/me` updates only the authenticated user's `full_name` and `email`; email
  uniqueness is checked case-insensitively and stored values are normalized to lowercase.
- `POST /api/v1/auth/change-password` requires the current password and replaces the authenticated
  user's bcrypt hash. The corresponding UI routes are `/settings/profile` and `/settings/password`.
- The `/admin/users` route is guarded client-side using `/auth/me`; only lead engineers and
  superusers may remain on the page. The table and modal are in
  `frontend/src/components/admin/`.
- Regenerate `frontend/src/lib/api-schema.d.ts` once the backend OpenAPI contract is finalized;
  temporary local type extensions in `frontend/src/lib/api.ts` should then be removed where
  generated types cover the same fields.
- `DocumentRead.owner_name` is populated by document list queries using `joinedload(Document.owner)`;
  do not replace it with an owner-ID placeholder.

## Safe Change Rules

- Read `docs/START_HERE.md`, this file, and the relevant source before editing.
- Preserve unrelated worktree changes. Never use destructive reset/checkout commands.
- Regenerate `frontend/src/lib/api-schema.d.ts` only after the backend OpenAPI contract has intentionally changed.
- Do not commit client or sample documents. Local commits are allowed; do not push.
- Run the focused tests for touched areas plus frontend typecheck/lint before committing.

## Remaining Release Queue

- Add frontend tests for login, project cards, document filtering/upload, and workflow action
  transitions.
- Add backend integration tests for project visibility, lead filters, upload ownership, and JWT
  workflow authorization.
- Add HTTP integration and browser/e2e coverage for user-management authorization and actions.
- Add HTTP coverage for profile update and project assignment authorization/visibility.
- Add browser coverage for `/settings/profile`, `Lihat Projects`, and long-page scrolling.
- PostgreSQL and Redis are healthy in the local Docker stack. The default backend suite skips the
  Redis vertical-slice test unless `RUN_REDIS_INTEGRATION=1` is set; a skipped test does not mean
  Redis is unavailable.
- Run the full Alembic chain against PostgreSQL before release. The current local database is at
  `20260910_0008`; migration `20260910_0009_project_assignment` must be applied before the latest
  assignment code is deployed.
- Decide whether self-disable, lead demotion, and last-active-admin protection are allowed, then
  enforce those rules in the backend rather than relying on the UI.
- Complete manual visual inspection of the rendered report PNGs for pagination and margins.

## Verification Snapshot

The latest completed frontend verification is:

```text
npm run typecheck  passed
npm run test       48 passed
npm run lint       passed
npm run build      passed
```

Latest focused auth-isolation verification:

```text
backend/tests/test_auth_isolation.py: 7 passed
```

The focused backend Budinski/export verification must be rerun after changes to the evaluator, schemas, pipeline, or export service.

Latest focused export verification:

```text
55 passed
ruff check passed
git diff --check passed
```

Latest account-management verification:

```text
backend/tests/test_user_management.py: 5 passed
frontend typecheck: passed
frontend lint: passed
OpenAPI and TypeScript contract regeneration: passed
```

Latest Docker visual smoke:

```text
worker: healthy
LibreOffice: available in worker
DOCX -> PDF: passed
PDF pages: 16
PNG pages rendered: 16
page size: 612 x 792 pt (Letter)
all rendered pages: non-empty text content
```

The smoke files were created under the worker's `/tmp` directory only and were not added to
Git. Manual visual inspection remains a separate step from this automated conversion check.

Export incident regression:

```text
persisted computed scorecard fields -> normalized -> strict validation -> DOCX
production endpoint: HTTP 200
```
