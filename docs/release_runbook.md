# DocsQA Production Release & Operational Runbook

**Milestone**: M5 — Export, Hardening, and Production Release  
**Version**: 1.0.0  
**Status**: Release Candidate; identity and project-assignment integration hardening in progress
**Audience**: DevOps, SRE, Platform Engineers, QA Lead Reviewers  

---

## 1. System Architecture & Components Overview

DocsQA is an automated quality assurance and traceability platform designed for heavy-engineering design manuals, specifications, and calculation sheets.

```mermaid
graph TD
    Client[Next.js 16 Web Client] -->|HTTP REST / Uploads| API[FastAPI Web Server]
    Client -->|Server-Sent Events (SSE)| API
    Client -->|Exports: PDF / XLSX / CSV / JSON| API
    API -->|PostgreSQL 16| DB[(Database & Audit Ledger)]
    API -->|Local / Cloud Storage| FS[(Document & Artifact Storage)]
    API -->|Celery Tasks| Redis[(Redis Broker)]
    Redis --> Worker[Celery Pipeline Workers]
    Worker -->|Stage Runs & Findings| DB
    Cron[Retention Cron Job] -->|Cleanup Expired Docs| API
```

### Core Services
1. **Frontend App (`frontend/`)**: Next.js 16 App Router (Turbopack, TypeScript, Tailwind CSS, Lucide icons).
2. **Backend API (`backend/`)**: FastAPI with Pydantic v2 schemas, SQLAlchemy 2.0 Async, security headers middleware, and Server-Sent Events (`/api/v1/documents/{id}/events`).
3. **Pipeline Workers (`backend/tasks/`, `backend/services/`)**: Celery workers executing decoupled analyzers for Table Math, Revision Sync, Standard Traceability, Reference Drift, Grammar, and Spellcheck.
4. **Export Service (`backend/services/export.py`)**: Generates annotated PDFs with coordinate overlays, formatted 4-tab Excel workbooks, flat RFC 4180 CSVs, and cryptographic JSON audit packages.
5. **Retention Service (`backend/services/retention.py`)**: Prunes expired files and database records exceeding the configurable TTL (default 30 days).

---

## 2. Pre-Deployment Checklist

- [x] Python 3.13+ virtual environment pinned with all requirements in `backend/requirements.txt` (including `openpyxl>=3.1.0`, `pypdf>=5.0.0`, `types-openpyxl`).
- [x] Node.js 20+ installed for `frontend/`.
- [x] PostgreSQL 16+ instance available with valid connection string; local Docker PostgreSQL is healthy.
- [x] Redis 7+ instance running for Celery broker; local Docker Redis is healthy.
- [x] Storage mount available with read/write permissions for upload staging and artifact retention.
- [x] Backend quality suite 100% passing (`backend/scripts/quality.ps1`).
- [x] Frontend checks 100% passing (`npm run check`: lint, typecheck, tests, production build).
- [x] Zero uncommitted local modifications.
- [ ] Apply and verify Alembic migration `20260910_0009_project_assignment` against the release database.
- [ ] Verify profile update, project assignment visibility, and admin project modal with HTTP/browser tests.

The default backend suite reports the Redis vertical-slice test as skipped because it is opt-in.
Redis is available in the local Docker stack; run the integration test explicitly with
`RUN_REDIS_INTEGRATION=1` after configuring the test process to reach the Docker API/worker.

---

## 3. Database Migration Runbook

All database schema migrations are managed through Alembic.

### 3.1 Inspect Pending Migrations
```bash
cd backend
python -m alembic current
python -m alembic heads
```

The local Docker database was last verified at revision `20260910_0008`. Do not deploy the latest
assignment code until `20260910_0009_project_assignment` has been applied.

### 3.2 Offline SQL Review (Recommended for Production DBA Review)
To generate the raw SQL script without executing it:
```bash
python -m alembic upgrade head --sql > migration_output.sql
```

### 3.3 Apply Migrations
```bash
python -m alembic upgrade head
```

### 3.4 Reversible Rollback (Emergency Only)
```bash
python -m alembic downgrade -1
```

The current head adds `projects.assigned_to_id`. On Docker, run the migration job before recreating
the application services:

```bash
docker compose build migrate api worker frontend
docker compose up migrate
docker compose up -d api worker frontend
```

Do not delete `postgres-data` or `backend-data` during a normal release update. The migration is
additive and preserves existing projects; existing projects remain unassigned until a lead assigns
them through the API/UI.

---

## 4. Environment Variables & Security Configuration

Configure the following environment variables in `.env` or container orchestrator secrets:

| Variable | Description | Default | Security Notes |
| :--- | :--- | :--- | :--- |
| `DOCSQA_DATABASE_URL` | Async Postgres connection URI | `postgresql+asyncpg://postgres:postgres@localhost:5432/docsqa` | Keep in secret manager |
| `DOCSQA_REDIS_URL` | Redis connection URI | `redis://localhost:6379/0` | Protect with Redis ACL / TLS |
| `DOCSQA_STORAGE_ROOT` | Root filesystem path for document storage | `./storage` | Ensure disk quotas and ACLs |
| `DOCSQA_RETENTION_DAYS` | Days before expired uploads are purged | `30` | Per PRD §4.3 ephemeral policy |
| `DOCSQA_CORS_ORIGINS` | Permitted browser origins | `http://localhost:3000` | Set to exact production domain |
| `NEXT_PUBLIC_API_BASE_URL`| Frontend API endpoint | `http://localhost:8000/api/v1`| Use HTTPS in production |
| `AUTH_MODE` | Authentication mode | `required` in Docker | Keep required outside local development |
| `SECRET_KEY` | JWT signing secret | none for production | Use a long random secret from a secret manager |
| `COOKIE_SECURE` | Require secure auth cookies | `false` locally | Set `true` behind HTTPS |

### HTTP Security Headers
Every HTTP response automatically includes enterprise security headers enforced via `backend/main.py`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Export Services Validation

Verify the 4 export formats against an audited document:

| Format | Endpoint | Verification Command | Expected Output |
| :--- | :--- | :--- | :--- |
| **Annotated PDF** | `GET /api/v1/documents/{id}/export?format=pdf` | `curl -f -o test.pdf "$API/documents/$DOC_ID/export?format=pdf"` | Valid PDF with `/Annots` objects and color-coded bounding boxes |
| **Excel Workbook** | `GET /api/v1/documents/{id}/export?format=xlsx` | `curl -f -o test.xlsx "$API/documents/$DOC_ID/export?format=xlsx"` | Excel workbook with `Summary`, `Traceability Issues`, `Linguistic Issues`, `Audit Trail` sheets |
| **CSV Issues** | `GET /api/v1/documents/{id}/export?format=csv` | `curl -f -o test.csv "$API/documents/$DOC_ID/export?format=csv"` | RFC 4180 CSV with headers and finding rows |
| **JSON Bundle** | `GET /api/v1/documents/{id}/export?format=json` | `curl -f "$API/documents/$DOC_ID/export?format=json"` | JSON package with `schema_version`, `document`, `issues`, and `audit_events` |

---

## 6. Retention Policy & Ephemeral Cleanup

To prevent disk saturation and enforce data retention compliance, run the retention cleanup service periodically (e.g. daily cron):

```bash
cd backend
python -c "
import asyncio
from db.session import get_session
from core.dependencies import get_storage
from services.retention import cleanup_expired_documents, get_retention_metrics

async def run():
    async for session in get_session():
        storage = get_storage()
        metrics = await get_retention_metrics(session, retention_days=30)
        print('Retention metrics:', metrics)
        purged = await cleanup_expired_documents(session, storage, retention_days=30)
        print(f'Purged {purged} expired documents.')
        break

asyncio.run(run())
"
```

---

## 7. Real-Time Telemetry & Health Checks

### 7.1 Service Health
- **Endpoint**: `GET /health`
- **Expected Status**: `200 OK`
- **Payload**: `{"status": "ok"}`

### 7.2 Server-Sent Events (SSE) Stream
- **Endpoint**: `GET /api/v1/documents/{id}/events`
- **Stream Format**: `text/event-stream`
- **Expected Stream Events**:
  - `event: progress` with payload `{"document_id": "...", "status": "...", "progress_pct": 50, "stages": [...]}`
  - `event: close` when document reaches terminal status (`COMPLETED`, `COMPLETED_WITH_WARNINGS`, `FAILED`).
- **Client Fallback**: The frontend client automatically falls back to exponential backoff HTTP polling if SSE encounters network interruptions.
- **Dashboard Behavior**: `/documents` opens one SSE subscription per `QUEUED` or `PROCESSING` document. The row progress, status, active-document metric, and live-monitoring banner update without a manual reload.
- **Visual Liveness**: Active document rows display a pulse indicator and animated progress treatment. Treat the `Live monitoring active` banner as confirmation that the browser is receiving or attempting live status updates.
- **Fallback Polling**: The dashboard refreshes the document list every five seconds while work is active. If SSE is unavailable, this polling path keeps progress visible; after a terminal event it reloads once to reconcile final metadata.

---

## 8. Incident Response & Rollback Procedures

1. **Pipeline Jam / Stalled Scans**:
   - Check worker logs: `celery -A core.celery_app inspect active`
   - Check Redis connectivity: `redis-cli ping`
   - Restart worker processes: `systemctl restart docsqa-celery`
2. **Database OCC Version Collision (`409 Conflict`)**:
   - Occurs when two reviewers submit simultaneous decisions for the same issue version.
   - Client automatically displays conflict banner and refreshes the finding item with latest state.
3. **Corrupted File or Malformed Upload**:
   - Storage service isolates uploads into safe subdirectories with SHA-256 deduplication.
   - If an upload fails validation, temporary unlinked files are cleaned up immediately via `_delete_stored_object`.

## 9. Identity and Project Assignment Smoke Checklist

Run this checklist after migration and before exposing the server:

1. Log in as a lead or superuser and confirm `/admin/users` loads.
2. Open `Lihat Projects` for an engineer and confirm the modal lists only projects assigned to that user.
3. Assign an active engineer through `PATCH /api/v1/projects/{project_id}/assign` and confirm the engineer sees the project.
4. Confirm an engineer can create a project but cannot assign a project to another user.
5. Open `/settings/profile`, update the name, and confirm the navbar reflects it after reload.
6. Attempt a duplicate email update and confirm the API returns `409` without changing the profile.
7. Confirm document list responses include a real `owner_name` for owned documents.
8. Confirm long project, admin, and settings pages scroll from top to bottom on desktop and mobile widths.
