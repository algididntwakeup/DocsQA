# PRISM - Precision Review and Inspection System Management

[![Backend Quality](https://img.shields.io/badge/backend-195%2B%20passed-success?style=flat-square&logo=python)](backend/)
[![Frontend Checks](https://img.shields.io/badge/frontend-60%20passed-success?style=flat-square&logo=react)](frontend/)
[![Architecture](<https://img.shields.io/badge/type-100%25%20deterministic%20(non--LLM)-blue?style=flat-square>)]()
[![Docker Compose](https://img.shields.io/badge/docker%20compose-ready-2496ED?style=flat-square&logo=docker)](compose.yaml.example)

**PRISM** is an automated, audit-grade Quality Assurance (QA) and Traceability platform designed for heavy-engineering design deliverables, specifications, calculation sheets, and vendor manuals.

Unlike generative AI tools that hallucinate, PRISM runs on **100% deterministic, reproducible algorithms** to provide rigorous compliance auditing against international standards (ASME, ASTM, API, ISO, NACE, AWS).

---

## Key Features & Capabilities

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       PRISM PLATFORM                                       │
├──────────────────────────────┬──────────────────────────────┬───────────────────────────────┤
│  DETERMINISTIC TRACEABILITY  │     REVIEW WORKSPACE & OCC   │     LINGUISTIC GOVERNANCE     │
│  • Table Math & Tolerances   │  • Split-Screen PDF Viewer   │  • Custom Engineering Dict    │
│  • 3-Way Revision Sync       │  • Visual Coordinate Boxes   │  • Specialized Spellcheck     │
│  • Standard & Edition Drift  │  • OCC Versioning (409 lock) │  • Grammar & Style Analysis   │
│  • ToC/LoF/LoT Page Drift    │  • Lead Reviewer Sign-Off    │  • Duplicate & Ambiguity Flag │
├──────────────────────────────┴──────────────────────────────┴───────────────────────────────┤
│                             EXPORT, TELEMETRY & HARDENING                                   │
│  • Headless LibreOffice PDF  │  • Multi-Sheet Excel (.xlsx) │  • Strict Bilingual Isolation │
│  • Executive Word (.docx)    │  • Annotated PDF Highlights  │  • Real-Time SSE Telemetry    │
│  • CSV & JSON Audit Package  │  • 30-Day Ephemeral Cleanup  │  • HTTP Security Headers      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Deterministic Traceability Core

- **Table Math & Arithmetic Cross-Footing**: Parses locale-aware numbers (decimal commas/dots), currency & engineering units (`kN`, `MPa`, `bar`, `kg/m³`). Computes row and column totals/subtotals without double counting, evaluating dual-threshold tolerances (percentage & absolute).
- **3-Way Revision Synchronization**: Compares explicit revision identifiers across the filename, title/cover page, and internal revision history block.
- **Standards & Edition Year Drift**: Extracts citations (e.g., _ASME Section VIII Div 2_, _API 650_, _ISO 9001_), validates edition years against the document bibliography, and surfaces missing citations or ambiguous bare standards.
- **Reference Drift (ToC / LoF / LoT)**: Automatically cross-references Table of Contents, List of Figures, and List of Tables page numbers against actual target headings and captions in the document body, calculating signed `page_delta` and detecting missing targets.

### 2. Interactive Split-Screen Review Workspace

- **Coordinate-Accurate Visual Overlays**: Interactive PDF canvas featuring bounding boxes color-coded by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **Optimistic Concurrency Control (OCC)**: Prevents accidental reviewer collision through strict versioning on issue decisions (`ACCEPTED`, `REJECTED`, `EDITED`, `FLAGGED`) with immediate HTTP 409 conflict detection.
- **Lead Reviewer Disposition**: Requires mandatory technical justification for audit-sensitive findings and document-level approval sign-offs.
- **Traceability Safeguard (PRD §3.2)**: Enforces a strict prohibition against bulk-accepting engineering traceability findings while permitting bulk approval for purely linguistic items.
- **Immutable Audit Trail**: Append-only ledger recording every actor ID, role, timestamp, previous state, new state, and rationale.

### 3. Linguistic Governance & Custom Engineering Dictionary

- **Governed Custom Engineering Dictionary**: Role-based workflow (`PENDING`, `APPROVED`, `REJECTED`) for company-specific abbreviations, proprietary alloy designations, and technical jargon.
- **Deterministic Spellchecker**: Whitelist of 100+ engineering acronyms (HAZ, NDT, PWHT), metallurgical grades (Inconel, Monel, Duplex, UNS), and chemical formulas, keeping false positives under 5%.
- **Grammar & Technical Writing Circuit-Breaker**: Identifies double words, homophone errors, and passive voice, while safely suppressing procedural imperative instructions and table fragments.
- **Near-Duplicate & Ambiguity Detection**: Flags near-duplicate paragraphs (>= 85% token sort ratio) and inconsistent alloy specifications within the same document (e.g., 316 vs 316L).

### 4. Multi-Format Export & Enterprise Hardening

- **Headless LibreOffice PDF Deliverable**: Generates production-ready read-only PDF review reports with exact table layouts, banners, and scorecards converted directly from DOCX via Headless LibreOffice (`soffice`).
- **Executive DOCX Review Report**: Formatted Word document for reviewers who need to add manual revisions or comments.
- **Strict Bilingual Localization ("Anti-Bahasa Belang")**: 100% pure English (`en`) OR 100% pure Indonesian (`id`) reports with zero mixed-language boilerplate phrases and fully localized 41-item Budinski compliance checklist.
- **Redesigned Deliverable Modal**: Format cards for PDF (Recommended), DOCX (Editable), and Annotated Source PDF (Visual Inspection), with language selector, minor findings toggle, and a separate opt-in Language & Mechanics section.
- **Annotated PDF Highlights**: Injects visual highlight rectangles and callout notes directly onto original PDF pages using pure-Python `pypdf`.
- **Multi-Sheet Excel Workbook (`.xlsx`)**: Formatted executive report with KPI Summary, Traceability Findings, Linguistic Findings, and full Audit Trail with auto-adjusted columns.
- **Flat CSV & Cryptographic JSON**: RFC 4180 compliant tabular export and machine-readable audit package (`schema_version: 1.0`) with document SHA-256 hash.
- **Real-Time Scan Telemetry (SSE)**: Streams pipeline progress (`text/event-stream`) to the browser with automatic fallback to exponential backoff HTTP polling.
- **Live Inspection Register**: The `/documents` dashboard subscribes to each queued or processing document, updates status/progress without a browser reload, and shows an animated live-monitoring indicator while work is active. The document status page uses the same SSE stream.
- **Audit-First Review Workspace**: Review findings are organized into `Budinski & Layout Audit`, `Standards Audit`, and `Language`; layout evidence includes cross-page sentence snippets and page navigation, while Budinski evidence exposes rule context and suggested fixes.
- **Budinski Technical-Writing Evaluation**: Applies the four baseline measures and the 41-item Appendix 12 checklist with integer scores from 1 to 5. Uninitialized legacy zeroes are treated as missing, never as a real score.
- **Document-Type-Aware Scoring**: SoR, Specification, and Procedure documents mark laboratory-only checklist items as `NOT_APPLICABLE` with no numeric score; those items are excluded from group and overall averages.
- **Retention Policy Worker**: Enforces ephemeral upload boundaries (default 30 days), automatically pruning expired database records, local storage files, and extraction artifacts.
- **Security Middleware**: Injects `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, and `Referrer-Policy` headers on all responses.

---

## Docker Deployment

Docker Compose starts the complete stack: PostgreSQL 17, Redis 7, Alembic migrations, FastAPI, Celery, and Next.js. Authentication is enabled by default. The template Compose file is provided as `compose.yaml.example`.

Current local Docker status: PostgreSQL and Redis are both running and healthy. The full backend
suite passes with the Redis integration test skipped by default; that test is opt-in through
`RUN_REDIS_INTEGRATION=1`. The running database is currently at Alembic revision `20260910_0010`,
including project and per-document assignment/WIP migrations. The project register supports engineer
claim, lead assignment, and emergency WIP override actions.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose v2.20+
- A server with enough disk space for PostgreSQL data, uploaded documents, and generated artifacts
- A reverse proxy and HTTPS certificate for production internet access

### Fresh Server Installation

1. Clone the repository and enter the project directory:

```bash
git clone https://github.com/reksolindo-org/PRISM.git
cd PRISM
```

2. Create the Docker environment and Compose files:

```bash
cp .env.docker.example .env
cp compose.yaml.example compose.yaml
```

On Windows PowerShell, use `Copy-Item .env.docker.example .env; Copy-Item compose.yaml.example compose.yaml`.

3. Edit `.env` before starting the server. At minimum, set unique values for:

```env
POSTGRES_PASSWORD=replace-with-a-database-password
SECRET_KEY=replace-with-a-long-random-secret
NEXT_PUBLIC_APP_URL=https://prism.example.com
BIMA_BASE_URL=https://bima.reksolindo.co.id
BIMA_CLIENT_ID=prism
INTERNAL_BACKEND_URL=http://backend:8000
COOKIE_SECURE=true
```

Browser requests use same-origin `/api/v1` through the frontend proxy. Set `NEXT_PUBLIC_APP_URL` to the public PRISM origin for the BIMA redirect URI; `BIMA_BASE_URL` selects BIMA host and API origin.

4. Build the application images and start PostgreSQL, Redis, and the migration job:

```bash
docker compose build migrate api worker frontend
docker compose up -d postgres redis
docker compose up migrate
```

The migration creates the schema and bootstrap accounts used only for recovery; frontend authentication uses BIMA SSO.

5. Start the API, worker, and frontend after migration succeeds:

```bash
docker compose up -d api worker frontend
```

6. Open the application:

- Frontend: `http://localhost:3001`
- API docs: `http://localhost:8001/docs`
- Health check: `http://localhost:8001/health`

Choose **Sign in with BIMA SSO**. Local password endpoints remain available for managed-account recovery but have no browser login or registration form.

### Updating an Existing Server

For source changes, rebuild the application images. Do not rebuild or delete PostgreSQL and Redis volumes. Compose project is `prism`; existing local volumes retain explicit `docsqa_*` names to preserve data. From the repository directory on the server:

```bash
git pull
docker compose build migrate api worker frontend
docker compose up migrate
docker compose up -d api worker frontend
```


If only frontend files changed, rebuilding `frontend` is sufficient. If backend Python, schema, migration, or worker code changed, rebuild `migrate`, `api`, and `worker`. If `compose.yaml`, `.env`, or Dockerfile changed, recreate the affected services after rebuilding. PostgreSQL and Redis only need to be recreated when their image or service configuration changes.

Useful update/status commands:

```bash
docker compose ps
docker compose logs --tail=200 migrate
docker compose logs -f api worker frontend
docker compose restart api worker frontend
```

### Authentication and Access Management

The frontend exposes a single **Sign in with BIMA SSO** action. BIMA authenticates users and redirects to PRISM; the API verifies the SSO token, synchronizes the identity, and issues the PRISM session cookie. There is no local password login or self-registration form.

Lead/superuser project synchronization uses the signed-in BIMA token to fetch project and user directories. Engineer `GET /api/v1/projects` requests also use the engineer's BIMA session token to provision their accessible BIMA projects as PRISM project folders and add the engineer as a member. Membership grants read access to those projects and their documents; it does not grant upload, assignment, review, or issue-curation rights.

Managed account provisioning and password-reset endpoints remain administrative recovery tools. Configure `BIMA_BASE_URL`, `BIMA_CLIENT_ID`, `NEXT_PUBLIC_BIMA_BASE_URL`, `NEXT_PUBLIC_APP_URL`, corporate CORS origins, and a secure cookie for production HTTPS.

For a production deployment:

- Replace `SECRET_KEY` with a long random secret and keep it outside version control.
- Replace `POSTGRES_PASSWORD` with a strong database password.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Restrict PostgreSQL and Redis ports to the private network or bind them only to localhost.
- Back up the `postgres-data`, `redis-data`, and `app_uploads` Docker volumes.

### Container Management

```bash
# Stop containers while preserving database and uploaded files
docker compose down

# Start the existing images again
docker compose up -d

# Clean-slate reset: permanently deletes database, Redis, and uploaded-file volumes
docker compose down --volumes
```

---

## Local Development (Without Docker)

### System Requirements

- Python `3.13` or `3.14`
- Node.js `20.x` or `24.x` (LTS)
- Running PostgreSQL (`localhost:5433`) and Redis (`localhost:6380`). These host ports are
  published by the local Docker stack; PostgreSQL and Redis are healthy there. Redis is not the
  reason the default test suite skips the integration test. Enable that test explicitly with
  `RUN_REDIS_INTEGRATION=1`.

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head

# Start FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

In a separate terminal, start the Celery pipeline worker:

```bash
cd backend
# Activate virtual environment
celery -A core.celery_app worker --loglevel=INFO --concurrency=2
```

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
# Use `npm run dev:3001` instead if port 3000 is taken by another project
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser (or
[http://localhost:3001](http://localhost:3001) when using `npm run dev:3001`).

---

## Verification & Quality Gates

Both backend and frontend feature reproducible quality verification suites that enforce zero-lint warnings, strict type safety, and comprehensive test coverage.

### Backend Verification Suite

Runs Ruff linter, strict Mypy typing, the Pytest unit and integration suite, OpenAPI export, and offline Alembic migration checks:

```powershell
# From repository root or backend folder
powershell -ExecutionPolicy Bypass -File backend\scripts\quality.ps1
```

The focused access-control and document-delete tests can be run independently:

```powershell
python -m pytest backend/tests/test_auth_isolation.py backend/tests/test_document_delete.py
```

### Frontend Verification Suite

Runs ESLint, strict TypeScript compiler check (`tsc --noEmit`), Vitest unit tests, and production Next.js build:

```bash
cd frontend
npm run check
```

### Document Access and Review Workspace

The `/documents` register is role-aware:

- `ENGINEER` sees documents uploaded by or assigned to that engineer.
- `LEAD_ENGINEER` and `SUPERUSER` see the global document register and can open any review workspace across projects.
- Lead users can filter the register by project, assigned engineer, and workflow status.
- Review initialization uses read-only `GET` requests for document metadata, issues, and PDF content. Workflow mutations are only sent when a user presses an action button.
- Lead and superuser review workspaces show an audit-mode banner and expose verification or revision actions after engineer review.

Uploaded files and generated artifacts persist in the `app_uploads` Docker volume mounted at `/app/storage/uploads` by both the API and Celery worker. Do not use `docker compose down --volumes` unless a full data reset is intended.

### Budinski Evaluation, DOCX & PDF Export

The deterministic evaluator in `backend/services/budinski_evaluator.py` supports both laboratory reports and non-laboratory engineering documents. For non-laboratory document types, experimental-step, repeatability, and discussion-only checklist items are emitted with `status=NOT_APPLICABLE` and `score=null`. Averages include only evaluated items and are always within the 1.00–5.00 range when evaluated items exist.

The production export path in `backend/services/export.py` generates executive Word documents via `generate_ale_review_docx()` and converts them to production-grade PDFs via Headless LibreOffice (`soffice` via `convert_docx_to_pdf()`). Deliverables strictly isolate languages (`lang="en"` for English, `lang="id"` for Indonesian). Its executive order is:

1. Document identity and localized verdict badge (`LAYAK TERBIT` / `PASSED`, etc.).
2. Executive summary and concrete recommendations.
3. Four-pillar Budinski summary.
4. Consolidated blockers and actionable corrections, including source excerpts and page ranges.
5. Next revision guidance and language/drafting mechanics findings.
6. Optional demonstration rewrite.
7. Category group summary.
8. Appendix A with the fully localized 41-item Budinski compliance checklist.
9. Positive observations and limits of review.

Run the focused evaluator/export regression suite from the repository root:

```powershell
python -m pytest backend/tests/test_budinski_evaluator.py backend/tests/test_report.py backend/tests/test_review_export.py -q
```

Targeted validation commands:

```powershell
python -m pytest backend/tests/test_auth_isolation.py
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

---

## Monorepo Architecture

```text
PRISM/
├── backend/
│   ├── alembic/              # Database schema versioning & migration scripts
│   ├── api/                  # FastAPI routers (documents, issues, audit, dictionary)
│   ├── core/                 # Config, security middleware, Celery app
│   ├── db/                   # Async SQLAlchemy engine and session factories
│   ├── domain/               # Core enums and domain vocabulary
│   ├── models/               # SQLAlchemy ORM models (Document, Issue, Audit, Dictionary)
│   ├── schemas/              # Pydantic v2 validation contracts & evidence trees
│   ├── services/             # Deterministic analyzer engines:
│   │   ├── export.py         # Multi-format PDF, Excel, CSV, JSON export service
│   │   ├── retention.py      # Ephemeral document TTL & disk artifact cleanup
│   │   ├── table_math.py     # Deterministic table math & cross-footing
│   │   ├── ref_drift.py      # Table of Contents & page drift analyzer
│   │   ├── revision_sync.py  # 3-way revision synchronization
│   │   ├── standard_trace.py # ASME/ASTM/API standard edition matcher
│   │   ├── spellcheck.py     # Metallurgical & engineering spellchecker
│   │   ├── grammar.py        # Grammar analysis with circuit-breaker fallback
│   │   ├── duplicate.py      # Near-duplicate section detection
│   │   └── ambiguity.py      # Contractual ambiguity & passive voice analyzer
│   ├── tasks/                # Celery decoupled task workers
│   └── tests/                # 195+ unit, integration, OCC, and lifecycle tests
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js 16 App Router (routes, layout, global styles)
│   │   ├── components/
│   │   │   ├── document/     # Document status, scan progress (SSE), upload
│   │   │   └── review/       # Split-screen viewer, highlight overlay, issue card,
│   │   │                     # export modal, audit modal, dictionary modal
│   │   └── lib/              # API client, SSE subscriber, type declarations
│   └── public/               # Static assets and icons
├── docs/                     # Technical specifications, PRD, release runbook
├── compose.yaml              # Docker Compose canonical definition
├── docker-compose.yml        # Docker Compose standard entrypoint
└── README.md                 # Project documentation
```

---

## Production Release & Operations Runbook

For detailed deployment instructions, secret management, offline migration execution, and incident response procedures, refer to [`docs/release_runbook.md`](docs/release_runbook.md).

---

## Troubleshooting & Incident Response

- For issues with background pipeline extraction hanging or long-running worker tasks on dense engineering vector drawings, see [`docs/troubleshooting_pipeline_stuck.md`](docs/troubleshooting_pipeline_stuck.md).
