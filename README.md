# DocsQA — Automated Document Quality Assurance & Traceability Platform

[![Backend Quality](https://img.shields.io/badge/backend-195%20passed-success?style=flat-square&logo=python)](backend/)
[![Frontend Checks](https://img.shields.io/badge/frontend-28%20passed-success?style=flat-square&logo=react)](frontend/)
[![Architecture](https://img.shields.io/badge/type-100%25%20deterministic%20(non--LLM)-blue?style=flat-square)]()
[![Docker Compose](https://img.shields.io/badge/docker%20compose-ready-2496ED?style=flat-square&logo=docker)](docker-compose.yml)

**DocsQA** is an automated, audit-grade Quality Assurance (QA) and Traceability platform designed for heavy-engineering design deliverables, specifications, calculation sheets, and vendor manuals.

Unlike generative AI tools that hallucinate, DocsQA runs on **100% deterministic, reproducible algorithms** to provide rigorous compliance auditing against international standards (ASME, ASTM, API, ISO, NACE, AWS).

---

## Key Features & Capabilities

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       DOCSQA PLATFORM                                       │
├──────────────────────────────┬──────────────────────────────┬───────────────────────────────┤
│  DETERMINISTIC TRACEABILITY  │     REVIEW WORKSPACE & OCC   │     LINGUISTIC GOVERNANCE     │
│  • Table Math & Tolerances   │  • Split-Screen PDF Viewer   │  • Custom Engineering Dict    │
│  • 3-Way Revision Sync       │  • Visual Coordinate Boxes   │  • Specialized Spellcheck     │
│  • Standard & Edition Drift  │  • OCC Versioning (409 lock) │  • Grammar & Style Analysis   │
│  • ToC/LoF/LoT Page Drift    │  • Lead Reviewer Sign-Off    │  • Duplicate & Ambiguity Flag │
├──────────────────────────────┴──────────────────────────────┴───────────────────────────────┤
│                             EXPORT, TELEMETRY & HARDENING                                   │
│  • Annotated PDF Highlights  │  • Multi-Sheet Excel (.xlsx) │  • CSV & JSON Audit Package   │
│  • Real-Time SSE Telemetry   │  • 30-Day Ephemeral Cleanup  │  • HTTP Security Headers      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Deterministic Traceability Core
- **Table Math & Arithmetic Cross-Footing**: Parses locale-aware numbers (decimal commas/dots), currency & engineering units (`kN`, `MPa`, `bar`, `kg/m³`). Computes row and column totals/subtotals without double counting, evaluating dual-threshold tolerances (percentage & absolute).
- **3-Way Revision Synchronization**: Compares explicit revision identifiers across the filename, title/cover page, and internal revision history block.
- **Standards & Edition Year Drift**: Extracts citations (e.g., *ASME Section VIII Div 2*, *API 650*, *ISO 9001*), validates edition years against the document bibliography, and surfaces missing citations or ambiguous bare standards.
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
- **Annotated PDF**: Injects visual highlight rectangles and callout notes directly onto original PDF pages using pure-Python `pypdf`.
- **Multi-Sheet Excel Workbook (`.xlsx`)**: Formatted executive report with KPI Summary, Traceability Findings, Linguistic Findings, and full Audit Trail with auto-adjusted columns.
- **Flat CSV**: RFC 4180 compliant tabular export for data science, BI, and spreadsheet analysis.
- **Cryptographic JSON Audit Package**: Machine-readable artifact (`schema_version: 1.0`) with document SHA-256 hash, raw evidence trees, and tamper-evident event history.
- **Real-Time Scan Telemetry (SSE)**: Streams pipeline progress (`text/event-stream`) to the browser with automatic fallback to exponential backoff HTTP polling.
- **Live Inspection Register**: The `/documents` dashboard subscribes to each queued or processing document, updates status/progress without a browser reload, and shows an animated live-monitoring indicator while work is active. The document status page uses the same SSE stream.
- **Audit-First Review Workspace**: Review findings are organized into `Budinski & Layout Audit`, `Standards Audit`, and `Language`; layout evidence includes cross-page sentence snippets and page navigation, while Budinski evidence exposes rule context and suggested fixes.
- **Retention Policy Worker**: Enforces ephemeral upload boundaries (default 30 days), automatically pruning expired database records, local storage files, and extraction artifacts.
- **Security Middleware**: Injects `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, and `Referrer-Policy` headers on all responses.

---

## Docker Deployment

Docker Compose starts the complete stack: PostgreSQL 17, Redis 7, Alembic migrations, FastAPI, Celery, and Next.js. Authentication is enabled by default. The canonical Compose file is `compose.yaml`; Docker Compose automatically prefers it when both Compose files exist.

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
git clone https://github.com/<your-org>/DocsQA.git
cd DocsQA
```

2. Create the Docker environment file:

```bash
cp .env.docker.example .env
```

On Windows PowerShell, use `Copy-Item .env.docker.example .env`.

3. Edit `.env` before starting the server. At minimum, set unique values for:

```env
POSTGRES_PASSWORD=replace-with-a-database-password
SECRET_KEY=replace-with-a-long-random-secret
NEXT_PUBLIC_API_BASE_URL=http://your-server:8000/api/v1
COOKIE_SECURE=false
```

Use `COOKIE_SECURE=true` when the browser reaches the application through HTTPS. If a reverse proxy exposes only the frontend and proxies `/api` internally, set `NEXT_PUBLIC_API_BASE_URL` to the public API URL expected by the browser.

4. Build the application images and start PostgreSQL, Redis, and the migration job:

```bash
docker compose build migrate api worker frontend
docker compose up -d postgres redis
docker compose up migrate
```

The `migrate` command creates the schema and seeds these initial accounts:

| Email | Initial password | Role |
|---|---|---|
| `admin@localhost` | `super123` | `SUPERUSER` |
| `lead.engineer@localhost` | `super123` | `LEAD_ENGINEER` |
| `engineer@localhost` | `user123` | `ENGINEER` |

5. Start the API, worker, and frontend after migration succeeds:

```bash
docker compose up -d api worker frontend
```

6. Open the application and immediately change the initial account password from `Change Password`:

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

The initial passwords are development/bootstrap credentials. Do not keep them on an exposed server.

### Updating an Existing Server

For source changes, rebuild the application images. Do not rebuild or delete PostgreSQL and Redis volumes. From the repository directory on the server:

```bash
git pull
docker compose build migrate api worker frontend
docker compose up migrate
docker compose up -d api worker frontend
```

`docker compose up migrate` runs all pending Alembic migrations, including account seed changes. The migration is safe for an existing database: it updates the documented local accounts and creates `admin@localhost` if the account does not already exist. The migration is not a password rotation mechanism for accounts that have already been changed manually.

If only frontend files changed, rebuilding `frontend` is sufficient. If backend Python, schema, migration, or worker code changed, rebuild `migrate`, `api`, and `worker`. If `compose.yaml`, `.env`, or Dockerfile changed, recreate the affected services after rebuilding. PostgreSQL and Redis only need to be recreated when their image or service configuration changes.

Useful update/status commands:

```bash
docker compose ps
docker compose logs --tail=200 migrate
docker compose logs -f api worker frontend
docker compose restart api worker frontend
```

### Authentication and Password Management

`AUTH_MODE=required` is set by the Compose file. The frontend login uses the accounts in the table above. `SUPERUSER` has the same lead workflow and user-management permissions as `LEAD_ENGINEER`.

Every authenticated user can change their own password at `/settings/password`. The API endpoint is `POST /api/v1/auth/change-password` and requires the current password plus a new password of at least eight characters. A lead or superuser can reset another account's temporary password from `Manage Users`.

For a production deployment:

- Replace `SECRET_KEY` with a long random secret and keep it outside version control.
- Replace `POSTGRES_PASSWORD` with a strong database password.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Change all bootstrap passwords immediately after the first login.
- Restrict PostgreSQL and Redis ports to the private network or bind them only to localhost.
- Back up the `postgres-data` and `backend-data` Docker volumes.

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
- Running PostgreSQL (`localhost:5432`) and Redis (`localhost:6379`). PostgreSQL and Redis are
  currently healthy in the local Docker stack; Redis is not the reason the default test suite skips
  the integration test. Enable that test explicitly with `RUN_REDIS_INTEGRATION=1`.

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
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
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
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Verification & Quality Gates

Both backend and frontend feature reproducible quality verification suites that enforce zero-lint warnings, strict type safety, and comprehensive test coverage.

### Backend Verification Suite
Runs Ruff linter, strict Mypy typing, 195+ Pytest unit and integration tests, OpenAPI export, and offline Alembic migration checks:

```powershell
# From repository root or backend folder
powershell -ExecutionPolicy Bypass -File backend\scripts\quality.ps1
```

### Frontend Verification Suite
Runs ESLint, strict TypeScript compiler check (`tsc --noEmit`), Vitest unit tests, and production Next.js build:

```bash
cd frontend
npm run check
```

---

## Monorepo Architecture

```text
DocsQA/
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
