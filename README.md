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
- **Retention Policy Worker**: Enforces ephemeral upload boundaries (default 30 days), automatically pruning expired database records, local storage files, and extraction artifacts.
- **Security Middleware**: Injects `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, and `Referrer-Policy` headers on all responses.

---

## Quickstart with Docker Compose

Running DocsQA with Docker Compose starts the entire production stack: PostgreSQL 17, Redis 7, database migrations, FastAPI backend, Celery analyzer worker, and Next.js 16 frontend.

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose (v2.20+)

### 2. Clone & Setup Environment
```bash
git clone https://github.com/<your-org>/DocsQA.git
cd DocsQA

# Copy example environment configuration
cp .env.docker.example .env
```

### 3. Launch Services
```bash
docker compose up --build
```

### 4. Access the Application
- **Review Workspace & Inspection Register**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 5. Managing the Containers
```bash
# View service status
docker compose ps

# Follow live container logs
docker compose logs -f api worker frontend

# Stop containers (preserves database and uploaded files)
docker compose down

# Stop and wipe database volume (clean slate reset)
docker compose down --volumes
```

---

## Local Development (Without Docker)

### System Requirements
- Python `3.13` or `3.14`
- Node.js `20.x` or `24.x` (LTS)
- Running PostgreSQL (`localhost:5432`) and Redis (`localhost:6379`)

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
