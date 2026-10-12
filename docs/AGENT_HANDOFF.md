# Agent Handoff

This file records implementation decisions that must not be reverted or duplicated by future agents. Read it after `docs/START_HERE.md` before changing the review pipeline or workspace.

## Current State


## PRISM Identity and Workspace

- Browser sign-in has a single BIMA SSO action; do not add local password login or registration forms. Password endpoints exist only for managed recovery/admin workflows.
- BIMA is a read-only, flat project catalog. `GET /api/v1/bima/catalog` returns
  `id`/`number`/`name`/`client_name` plus local `is_imported`/`prism_project_id`, and PRISM never
  mirrors BIMA master data. Do not reintroduce directory sync, membership mirroring, or a per-project
  BIMA detail fetch: BIMA's live directory omits membership and its `/api/projects/{id}` answers 404.
- Importing is on demand via `POST /api/v1/projects/import-bima`, which is idempotent on
  `bima_project_id` (existing row → `200`, new row → `201`) and sets `projects.owner_id` to the
  calling user. Project read access is ownership- or document-based; there is no project membership
  table (dropped in Alembic `20261012_0020_bima_on_demand_import`).
- Browser API uses relative `/api/v1`; SSR/rewrite targets `INTERNAL_BACKEND_URL` (Compose alias default `http://backend:8000`). SSO authorization origin is configured through `NEXT_PUBLIC_BIMA_BASE_URL` and returns to `NEXT_PUBLIC_APP_URL`/current app origin.
- PDF canvas and highlight overlay share one viewport-sized wrapper. Continuous Ctrl/Meta-wheel zoom and mouse drag pan must keep that shared coordinate space; touch panning stays native.

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
- The project document register polls every 3 seconds while processing rows are present and disables workspace navigation until `Document.status` is terminal; `workflow_status=ANALYZING` remains the human review state.
- Project lifecycle uses nullable `projects.finished_at` (`20260914_0012_project_lifecycle`). Lead engineers and superusers may finish only projects whose documents have terminal processing statuses. Finished projects remain viewable/exportable but reject upload, project/document assignment, claim, document workflow transitions, and issue curation. Project deletion is restricted to empty projects.
- `DocumentRead` currently exposes metadata only. It does not expose the persisted `BudinskiScorecard`; do not add baseline or Group I-IV values to the workspace until a backend endpoint/response contract exposes them.
- Export controls are buttons using `frontend/src/lib/download.ts`, not direct anchor links, so asynchronous download errors can be surfaced consistently.
- The project dashboard lives under `/projects` and `/projects/{id}`. Project cards and the
  project document table are separate from the review workspace.
- `review-workspace-view.tsx` owns the isolated workflow status strip and workflow action bar;
  `split-screen-viewer.tsx`, the PDF viewer, highlight overlay, issue panel, issue card, and
  export modal remain protected internals.
- Workflow actions call `/documents/{id}/mark-reviewed`, `/verify`, and `/request-revision` and
  update the document state from the response without a full-page reload.
- `/documents/{id}/review` renders inside the shared `AppShell` (h-16 topbar) and uses a
  `h-[calc(100dvh-4rem)]` workspace. Keep the PDF canvas and highlight overlay in the same
  positioned page wrapper so bounding-box coordinates remain precise.
- Frontend authentication uses the HttpOnly `access_token` cookie with `credentials: "include"`.
  The API client redirects 401 responses to `/login`; do not reintroduce JWT storage in
  `localStorage`.

## Multi-User API Contract

- Authentication supports BIMA credential login and BIMA SSO. Credential login calls BIMA
  `/api/auth/login` with `username` and `password`, then resolves the profile through
  `/api/auth/me`. SSO starts at BIMA `/sso/authorize` and exchanges the callback token through
  PRISM `POST /api/v1/auth/sso/exchange`, which calls BIMA `/api/sso/verify` with the configured
  `BIMA_CLIENT_ID` (production: `prism`).
- BIMA responses use a `data` envelope; SSO profile data is at `data.user`. The BIMA client maps
  `is_admin` or `super-administrator` to `SUPERUSER`, lead/manager/project-manager roles or a
  `Lead` position to `LEAD_ENGINEER`, and all other users to `ENGINEER`.
- BIMA users are JIT-provisioned by `upsert_bima_user`, keyed by `bima_id` or normalized email.
  SSO users have a nullable `hashed_password`; local password authentication remains available
  as a fallback for emergency local accounts. Migration `20260916_0013_bima_identity` is the
  current identity schema head.
- BIMA SSO redirect URIs must be registered/whitelisted in BIMA. Local development uses
  `http://localhost:3001/auth/sso/callback` (the Compose frontend publishes host port `3001`
  because `3000` is reserved for another local project); production must register the deployed
  HTTPS URI.
- Runtime frontend API calls use same-origin `/api/v1`; `frontend/next.config.ts` rewrites them to
  `INTERNAL_BACKEND_URL`, defaulting to `http://backend:8000`. Compose keeps the service name `api`
  and publishes a `backend` network alias so that default resolves. Do not reintroduce a public API
  URL into the browser bundle. Set `NEXT_PUBLIC_APP_URL` for SSO callback generation and
  `CORS_ORIGINS` or `CORS_ORIGIN_REGEX` for deployments where the browser origin differs from the
  frontend proxy. The browser-facing BIMA SSO host comes from `NEXT_PUBLIC_BIMA_BASE_URL`, sourced
  from `BIMA_BASE_URL`; never hardcode the BIMA origin in `login/page.tsx`.
- Production deployment identity is PRISM: set `APP_NAME=PRISM - Document Assurance Platform`,
  `NEXT_PUBLIC_APP_URL=https://prism.reksolindo.co.id`, `CORS_ORIGINS=https://prism.reksolindo.co.id`,
  and `BIMA_CLIENT_ID=prism`. Keep the Compose project name unchanged unless volumes are migrated.
- `GET /api/v1/bima/catalog` proxies BIMA `GET /api/projects` with the `bima_access_token` cookie
  (or an `Authorization: Bearer` header for direct API clients) and annotates each flat row with
  local import state from one `SELECT bima_project_id, id FROM projects WHERE bima_project_id IN (...)`.
  `POST /api/v1/projects/import-bima` then creates the local project on demand. Migration
  `20261007_0019_bima_project_metadata` adds `project_number`/`client_name`; migration
  `20261012_0020_bima_on_demand_import` drops `project_members`/`projects.assigned_to_id` and renames
  `projects.created_by_id` to `projects.owner_id`. See "BIMA Catalog & On-Demand Import Contract" below.

- `POST /api/v1/auth/login` returns a bearer token and user role; `GET /api/v1/auth/me` returns
  the current user.
- `GET /api/v1/projects` lists visible projects. `GET /api/v1/projects/{project_id}/documents`
  applies engineer isolation and lead-only engineer/date/blocker filters.
- `POST /api/v1/projects` can be used by any authenticated user. Project responses include
  `owner_id`, `owner_name`, `total_documents`, `status`, and `updated_at`.
- `GET /api/v1/projects?user_id=...` returns the projects **owned** by that user. Project-level
  assignment no longer exists (`PATCH /api/v1/projects/{project_id}/assign` was removed with the
  `projects.assigned_to_id` column); document-level assignment is unaffected.
- `POST /api/v1/projects/{project_id}/documents/upload` assigns the uploaded document to the
  project and current user.
- `POST /api/v1/documents/{document_id}/claim` enforces one active `ANALYZING` document per
  engineer. `POST /api/v1/documents/{document_id}/assign` supports lead assignment and optional
  `override_wip: true`.
- `GET /api/v1/auth/users/{user_id}/projects` returns assigned projects with document titles and
  workflow statuses for the admin task inspector.
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
  `20260910_0010 (head)`, including project and per-document assignment migrations.
- Decide whether self-disable, lead demotion, and last-active-admin protection are allowed, then
  enforce those rules in the backend rather than relying on the UI.
- Complete manual visual inspection of the rendered report PNGs for pagination and margins.

## Verification Snapshot

The latest completed frontend verification is:

```text
npm run typecheck  passed (0 errors)
npm run test       60 passed (16 test files)
npm run lint       passed (0 warnings, 0 errors)
npm run build      passed
```

Latest focused auth-isolation verification:

```text
backend/tests/test_auth_isolation.py: 7 passed
```

The focused backend Budinski/export verification must be rerun after changes to the evaluator, schemas, pipeline, or export service.

Latest focused export verification:

```text
backend/tests/test_review_export.py: 28 passed
backend/tests/test_report.py: 7 passed
backend/tests/test_export.py: 3 passed
Total export suite: 38 passed
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

## Assignment & Kanban WIP=1 Contract

- Document claim enforces strict WIP = 1 for engineers: an engineer cannot claim a new document if they have $\ge 1$ document in `ANALYZING` workflow status.
- In `backend/api/projects.py`, `await session.refresh(project, attribute_names=["owner", "documents"])` must always be called with explicit attribute names so relationships are loaded before `_project_read()` serializes them, preventing `MissingGreenlet` HTTP 500 errors. The project listing query also groups by `projects.id`, so it must load the owner with `selectinload(Project.owner)`: a `joinedload` adds `users` columns to the `GROUP BY` query and PostgreSQL rejects it with `GroupingError`.
- In PostgreSQL, queries using `with_for_update()` must NOT use `joinedload` on nullable relationships (such as `assigned_to`), because PostgreSQL raises `FeatureNotSupportedError: FOR UPDATE cannot be applied to the nullable side of an outer join`. Single-row locking in `_load_document_for_assignment` locks `Document` directly without joins; relationships are loaded post-commit via `session.refresh(document, attribute_names=["owner", "assigned_to"])`.
- In `backend/api/documents.py` (`mark_document_reviewed`), the permission check restricts action to `document.assigned_to_id == current_user.id` (assignee only). Test fixtures must assign the document to the acting user.
- Frontend document table cell rendering adheres to 5 strict cases (Cases A–E) detailed in `docs/ASSIGNMENT_WIP_FIX_PLAN.md`, with formal Indonesian tooltips ("Selesaikan tugas aktif Anda terlebih dahulu") and "Tugas Anda" badge with direct review link.

## Document Read Permission & PDF/File Preview Contract

- Documents and their canonical preview streams (`GET /documents/{id}/file` and `GET /documents/{id}/pdf`) grant read access if:
  1. `doc.assigned_to_id == current_user.id` (Direct PIC)
  2. `doc.owner_id == current_user.id` (Uploader)
  3. `doc.project.owner_id == current_user.id` (Project owner)
  4. `current_user.role in {LEAD_ENGINEER, SUPERUSER}`
- For DOCX uploads, the review endpoints serve the converted `preview.pdf`. If the document is still in `QUEUED` or `PROCESSING` pipeline state, an HTTP 409 is returned with a descriptive message. If completed, an on-the-fly conversion fallback via headless LibreOffice is invoked if `preview.pdf` was not yet generated.
- `pdf-canvas-viewer.tsx` and API helpers fetch with `credentials: "include"`, pass the Bearer token via `Authorization: Bearer <token>`, and use `cache: "no-store"` to avoid browser caching of transient preview generation states.

## BIMA Catalog & On-Demand Import Contract

BIMA is an upstream, read-only, flat project catalog. PRISM owns every project record; there is no
membership or assignment mirroring, and no BIMA master-data sync.

### Catalog proxy

- `backend/api/bima.py` holds the only BIMA project endpoint: `GET /api/v1/bima/catalog`, which calls
  `BimaService.list_projects(token)` (upstream `GET /api/projects`) and returns a bare JSON array of
  `BimaCatalogItem` — not a `{success, data}` envelope. The upstream credential is the
  `bima_access_token` cookie, falling back to `Authorization: Bearer` for direct API clients.
- `_catalog_fields()` normalizes one row and raises HTTP 502 for a missing/invalid ID or a missing
  number/name. It accepts the documented aliases (`id`/`bima_project_id`, `name`/`project_name`,
  `number`/`project_number`, `client_name`/`client`, and a nested `client_name.name` object).
  A missing or blank client becomes `None`; only a non-textual client is treated as corrupt.
- Import state comes from a single query — `SELECT bima_project_id, id FROM projects WHERE
  bima_project_id IN (...)` — and is rendered as `is_imported` plus `prism_project_id`.
- Do not reintroduce `GET /bima/projects`, its `{success, data}` envelope, or a per-project
  `GET /api/projects/{id}` fetch: the live BIMA directory exposes no membership fields and its detail
  endpoint answers 404 for listed projects. Those paths caused the recurring 500/502s.

### On-demand import

- `POST /api/v1/projects/import-bima` (`backend/api/projects.py::import_bima_project`) takes the
  catalog row it needs — `bima_project_id`, `project_number`, `name`, `client_name` — and never calls
  BIMA itself.
- It is idempotent on the unique `projects.bima_project_id`: an existing row is returned unchanged
  with **200**; a new row is created with **201**. `IntegrityError` (concurrent import) re-selects the
  winner and also returns 200. There is no 409 for a duplicate import.
- A new project is owned by the calling user: `owner_id = current_user.id`, exposed as `owner_id` and
  `owner_name`. Importing still provisions the workspace directory
  (`storage.get_full_path(f"projects/{project.id}")`) and therefore still enforces the folder RBAC —
  `can_manage_folders(role, project_number)`, i.e. `13` engineering numbers for engineering roles and
  `03` internal numbers for HR/GA and finance — returning 403 otherwise.
- `POST /api/v1/projects/sync-bima` no longer exists; `backend/services/bima_adapter.py` was deleted
  with it. Do not restore directory sync, `BimaMasterDataAdapter`, `sync_user_bima_projects`, or the
  `fetch_bima_projects`/`fetch_bima_users` directory clients. `services/bima_client.py` now only owns
  BIMA login/SSO identity (`login_with_bima_credentials`, `verify_sso_token`, `_profile`).

### Persistence

- Migration `20261012_0020_bima_on_demand_import` is the schema head. It drops `project_members` and
  `projects.assigned_to_id`, renames `projects.created_by_id` → `projects.owner_id`, and adds
  `projects.updated_at` (the model now inherits `models.document.TimestampMixin`).
  `documents.assigned_to_id` is deliberately untouched: document kanban assignment is a PRISM
  workflow concept, not BIMA mirroring.
- `backend/tests/test_models.py` asserts the exact registered table set. Adding a table means updating
  that assertion.

### Ownership-based RBAC

- Project read visibility is `Project.owner_id == me` OR the caller owns/holds an assigned document in
  the project. It is applied in `list_projects`, `list_project_documents`, `list_documents`, and
  `check_document_read_access`.
- `list_project_documents` no longer treats BIMA-backed projects specially: every non-privileged role
  gets the `assigned_to_id == me OR owner_id == me` document filter, so an unrelated engineer sees an
  empty list rather than a 403.
- Do **not** widen ownership into write authorization. `PATCH /api/v1/issues/{issue_id}/curation`
  must still 404 for an engineer who is neither owner nor assignee — this is asserted in tests.
- Engineers still cannot inspect other users' projects through the `user_id` filter, which now means
  "projects owned by that user".

### Design tokens and primitives

- `frontend/src/app/globals.css` defines shadcn semantic light/dark pairs (`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--accent`, `--border`, `--ring`, …) plus legacy aliases (`--canvas`, `--panel`, `--line`, `--text`) that keep the older component CSS readable in both themes.
- `@custom-variant dark (&:where(.dark, .dark *))` makes `dark:` utilities follow the `.dark` class rather than the OS preference. `ThemeToggle` sets `data-theme` **and** the `.dark`/`.light` classes, and `app/layout.tsx` runs a pre-paint bootstrap script so a persisted dark theme does not flash light. Keep the `matqc-theme` storage key and `matqc-theme-change` event contract.
- Two legacy names collide with shadcn semantics and must stay separated: text `--muted` is now `--muted-foreground` (the surface value is `--muted`), and the old brand-blue `--accent`/`--accent-soft` are now `--brand`/`--brand-soft`. The brand-blue accents have since been consolidated onto `primary`, so prefer `text-primary` / `bg-primary` / `bg-accent` for new work.
- `frontend/src/components/ui/` holds local `card.tsx`, `table.tsx`, and `resizable.tsx` built on `@/lib/utils`'s `cn`. `cn` is a plain join with **no tailwind-merge**: a `className` prop cannot reliably override a conflicting default utility (Tailwind emits `px-6` after `px-3`). Where an override must win, use arbitrary values such as `px-[12px] py-[8px]`, as `traceability-summary-modal.tsx` does.
- `react-resizable-panels` sizing props must be percentage **strings** (`defaultSize="60"`). Bare numbers are interpreted as pixels.
- The review workspace is `h-[calc(100dvh-4rem)]` and relies on the `h-16` app-shell topbar. At ≥1024 px `split-screen-viewer.tsx` renders a `Group`/`Panel`/`Separator` layout (60/40, mins 45/25, max 55); below that it keeps the Document/Findings pane switcher, which is rendered in both the embedded and standalone headers.

### PDF pan/zoom invariants

- Zoom stays continuous (exponential Ctrl/Meta-wheel, no percent snapping) within `0.4–10`, anchored to the pointer. Ordinary wheel scrolling is untouched.
- Left-button mouse drag pans the existing scroll container via pointer capture with a 3 px threshold. Touch pointer types are ignored so native scrolling survives; the toolbar is never a drag surface.
- The wheel listener is bound in an effect keyed on `isLoading` because the scroll container only exists after the document loads. Reverting it to `[]` silently breaks zoom.
- The canvas and `HighlightOverlay` must keep sharing one positioned wrapper: the wrapper's CSS size comes from the same PDF.js viewport as the canvas, and overlay percentages derive from `BoundingBox.page_width/page_height`. Never scale the overlay with an independent transform.
