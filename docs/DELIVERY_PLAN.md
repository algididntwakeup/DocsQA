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

## Phase 3: Deployment & Hardening (In Progress)
- [x] **Milestone 7: Docker Headless Visual Validation**
  - [x] Compose and backend image now verify that `soffice --headless --version` is available in the worker.
  - [x] Added `backend/scripts/verify_libreoffice.py` for deterministic DOCX-to-PDF smoke validation.
  - [x] Run the LibreOffice smoke command on Docker Desktop; worker reports LibreOffice 25.2.3.2.
   - [x] Render the generated PDF to page PNGs; 16 pages rendered successfully.
   - [ ] Test pagination fidelity and margin alignment across platforms.

## Phase 4: Agent-Protected Integration Checkpoint (Completed)

- [x] **Milestone 8: Flat Budinski Rule Contract**
  - Added deterministic `EvaluationContext` and flat `ScorecardEntry` handling.
  - Covered the 41 canonical Appendix 12 items across Groups I-IV.
  - Added computed baseline score and group-average accessors while retaining legacy
    grouped scorecard compatibility.
- [x] **Milestone 9: Dynamic Review Export**
  - DOCX scorecard rendering prefers flat scorecard items, computed averages, and baseline
    values instead of sample-document constants.
  - Preserved legacy grouped export behavior for existing artifacts and fixtures.
- [x] **Milestone 10: Workspace Synchronization**
  - Frontend loads all findings pages, handles SSE completion refresh, supports current
    severity levels, and shows processing/warning/failure state banners.
  - Export actions support the `include_minors` option.
- [x] **Milestone 11: Handoff Documentation**
  - Added `docs/AGENT_HANDOFF.md` with protected contracts, safe-change rules, and known
    API boundaries to prevent future agents from reverting completed work.
- [x] **Milestone 12: Executive DOCX Narrative Export**
  - Added deterministic `ReportSynthesizer` and `docx_styler` modules.
  - Replaced the production raw alert-table DOCX path with the ten-section executive
    `Review of [Document]` report and dynamic scorecard adapter.
  - Added XML-level tests for callout borders, cell shading, repeating headers, and no raw
    JSON/issue-object dump in the report.
  - Preserved the legacy report builder for existing direct callers and compatibility tests.

## Phase 5: Multi-User Project Review Workflow (Implemented; Hardening In Progress)

- [x] **Milestone 13: Authentication and User Isolation**
  - Added JWT login and current-user endpoints with engineer and lead-engineer roles.
  - Restricted document/project visibility through the authenticated user context.
- [x] **Milestone 14: Project Dashboard**
  - Added Level 1 project cards and Level 2 project document register routes.
  - Added project-scoped document upload, lead-only engineer/date/blocker filters, and direct
    links into the existing review workspace.
- [x] **Milestone 15: Document Review Workflow**
  - Added owner `mark-reviewed`, lead `verify`, and lead `request-revision` transitions.
  - Added workflow metadata to DOCX export without changing locked report-generation components.
- [x] **Milestone 16: Review Workspace Workflow UI**
  - Added isolated workflow status and role-aware action controls around the existing split-screen
    viewer. Viewer, PDF canvas, findings panel, issue cards, and export modal internals remain
    unchanged.
- [ ] **Milestone 17: Contract and Test Hardening**
  - Regenerate frontend OpenAPI types after the auth/project/workflow contract is finalized.
  - Add frontend unit tests for login, project dashboard, filters, upload, and workflow actions.
  - Add backend integration tests for role isolation, project filters, upload ownership, and all
    workflow transitions.
- [ ] **Milestone 18: Production Session and Release Validation**
  - Secure HttpOnly SameSite cookie authentication, logout, expiry handling, and unauthorized
    frontend redirects are implemented; production deployment still requires `COOKIE_SECURE=true`
    and environment validation.
  - Manually inspect report pagination/margins across rendered PNGs and rerun full quality gates.

## Phase 6: Account Administration (Implemented; Integration Hardening In Progress)

- [x] **Milestone 19: Lead/Superuser User Management API**
  - Added `SUPERUSER` as an authorization role while restricting account creation to
    `ENGINEER` and `LEAD_ENGINEER`.
  - Added protected account listing with `total_documents_owned`.
  - Added account creation with bcrypt-hashed temporary passwords.
  - Added account activation/deactivation and password reset endpoints.
  - Preserved the existing login, cookie session, and bearer-token fallback flow.
- [x] **Milestone 20: Admin User Interface**
  - Added `/admin/users` with a lead/superuser route guard.
  - Added user table with name, email, role, status, creation date, owned-document count, and actions.
  - Added create-user modal for name, email, temporary password, and Engineer/Lead role.
  - Added status toggle and password reset actions using the cookie-authenticated API client.
- [x] **Milestone 21: Account Management Verification**
  - Added role-protection, listing, password hashing, status toggle, and password reset tests.
  - Regenerated OpenAPI and frontend TypeScript definitions for the account-management contract.
  - Focused user-management tests pass: 5 passed.
- [ ] **Milestone 22: Account Management Release Hardening**
  - Add HTTP integration and browser/e2e coverage for `/admin/users` and all management actions.
  - Define and enforce policy for self-deactivation, lead demotion, and last-active-admin protection.

## Phase 7: Identity and Project Assignment (Implemented; Verification In Progress)

- [x] **Milestone 23: Profile and Password Self-Service**
  - Added authenticated `PATCH /api/v1/auth/me` for normalized, unique email and full-name updates.
  - Added `/settings/profile` with success toast and error feedback.
  - Preserved `/settings/password` and the authenticated password-change API.
- [x] **Milestone 24: Project Assignment Contract**
  - Added nullable `projects.assigned_to_id` and Alembic migration `20260910_0009_project_assignment`.
  - Added explicit SQLAlchemy relationships for creator and assignee to avoid ambiguous foreign keys.
  - Added lead/superuser assignment endpoint, `user_id` filtering, and engineer project creation.
  - Exposed creator/assignee names and document counts in project responses.
- [x] **Milestone 25: Admin Assignment Visibility and Scroll Fix**
  - Added `Lihat Projects` modal with assigned project metadata and direct project links.
  - Added real `owner_name` to document list responses through eager-loaded owner relations.
  - Removed whole-page layout constraints that prevented normal scrolling on project, admin, and settings pages.
- [ ] **Milestone 26: Assignment and Identity Verification**
  - Add backend HTTP tests for profile update, duplicate email, project assignment, visibility, and role boundaries.
  - Add frontend tests for profile form, project modal, assignment visibility, and responsive scrolling.
  - Regenerate OpenAPI and TypeScript contracts after finalizing the new response fields.
  - Run the full backend suite, frontend suite, Docker migration, and production smoke test.
