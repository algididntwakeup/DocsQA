# PRISM Production Release & Operational Runbook

**Milestone**: M5 — Export, Hardening, and Production Release  
**Version**: 1.0.0  
**Status**: Release Candidate; identity and project-assignment integration hardening in progress
**Audience**: DevOps, SRE, Platform Engineers, QA Lead Reviewers  

---

## 1. System Architecture & Components Overview

PRISM is an automated quality assurance and traceability platform designed for heavy-engineering design manuals, specifications, and calculation sheets.

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
- [x] Apply and verify Alembic migrations through `20261012_0020_bima_on_demand_import` locally.
- [ ] Verify profile update, project ownership visibility, and admin project modal with HTTP/browser tests.

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

The local Docker database head is `20261012_0020_bima_on_demand_import`. The BIMA identity and
project-metadata migrations (`20260916_0013`, `20260916_0014`, `20261007_0019`) must be applied
before it, and `20261012_0020` then drops the obsolete `project_members` table.

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

The current head (`20261012_0020_bima_on_demand_import`) drops the `project_members` table and
`projects.assigned_to_id`, renames `projects.created_by_id` to `projects.owner_id`, and adds
`projects.updated_at`. On Docker, run the migration job before recreating the application services:

```bash
docker compose build migrate api worker frontend
docker compose up migrate
docker compose up -d api worker frontend
```

Do not delete `postgres-data` or `backend-data` during a normal release update. The migration
preserves existing projects and renames their single owner column in place; projects are created
afterwards only by explicit on-demand import (`POST /api/v1/projects/import-bima`), which assigns the
importing user as `owner_id`. There is no directory sync step.

---

## 4. Environment Variables & Security Configuration

Configure the following environment variables in `.env` or container orchestrator secrets:

| Variable | Description | Default | Security Notes |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Async Postgres connection URI | `postgresql+asyncpg://prism:prism@localhost:5433/prism` | Keep in secret manager |
| `REDIS_URL` | Redis connection URI | `redis://localhost:6380/0` | Protect with Redis ACL / TLS |
| `STORAGE_ROOT` | Root filesystem path for document storage | `./data` | Ensure disk quotas and ACLs |
| `DOCUMENT_RETENTION_DAYS` | Days before expired uploads are purged | `90` | Set according to retention policy |
| `CORS_ORIGINS` | Permitted browser origins | `https://prism.reksolindo.co.id` | Set to the exact PRISM production domain |
| `CORS_ORIGIN_REGEX` | Regex for additional permitted origins | `^https://(?:[a-z0-9-]+\.)*reksolindo\.co\.id$` | Covers corporate subdomains; keep anchored |
| `INTERNAL_BACKEND_URL` | Backend URL used by the Next.js rewrite | `http://backend:8000` | Server-side only; never expose to the browser |
| `POSTGRES_PORT` | Host port published for PostgreSQL | `5433` | Container always listens on `5432`; `5432` is reserved for another local project |
| `REDIS_PORT` | Host port published for Redis | `6380` | Container always listens on `6379`; `6379` is reserved for another local project |
| `API_PORT` | Host port published for the API | `8001` | Container always listens on `8000`; `8000` is reserved for another local project |
| `FRONTEND_PORT` | Host port published for the frontend container | `3001` | Container always listens on `3000`; `3000` is reserved for another local project |
| `NEXT_PUBLIC_APP_URL` | Public PRISM application URL | `https://prism.reksolindo.co.id` | Used for BIMA SSO callback generation |
| `NEXT_PUBLIC_BIMA_BASE_URL` | Browser-facing BIMA origin | `https://bima.reksolindo.co.id` | Compiled into the frontend image; sourced from `BIMA_BASE_URL` |
| `BIMA_BASE_URL` | BIMA API origin (server-side) | `https://bima.reksolindo.co.id` | Also feeds `NEXT_PUBLIC_BIMA_BASE_URL` at build time |
| `BIMA_CLIENT_ID` | Registered BIMA SSO client | `prism` | Must match the BIMA client registration |
| `AUTH_MODE` | Authentication mode | `required` in Docker | Keep required outside local development |

| `SECRET_KEY` | JWT signing secret | none for production | Use a long random secret from a secret manager |
| `COOKIE_SECURE` | Require secure auth cookies | `false` locally | Set `true` behind HTTPS |

### 4.1 Bilingual frontend and report export

The browser UI supports English and Bahasa Indonesia. The preference is stored locally under `matqc-locale`; it is not a backend or database setting. The DOCX/PDF review-report language is selected independently in the export modal and is sent as `language=en` or `language=id`. Language and Mechanics is a separate opt-in: the default export omits that entire section, and enabling it sends `include_language_mechanics=true`. The annotated source PDF remains source-faithful and ignores report-language options.

For this feature, rebuild the frontend and backend application images:

```bash
docker compose build migrate api worker frontend
docker compose up migrate
docker compose up -d --force-recreate api worker frontend
```

`postgres` and `redis` do not need rebuilding. There is no schema migration for locale/report language or the Language & Mechanics export option. The backend image installs LibreOffice/Writer plus DejaVu and Liberation fonts for headless DOCX-to-PDF conversion. The browser no longer needs a compiled API host: requests are same-origin `/api/v1` and the Next.js rewrite resolves `INTERNAL_BACKEND_URL`, which defaults to `http://backend:8000` (the Compose `api` service publishes a `backend` network alias). `NEXT_PUBLIC_BIMA_BASE_URL` **is** compiled into the frontend image, so set it before `docker compose build frontend`.

### HTTP Security Headers
Every HTTP response automatically includes enterprise security headers enforced via `backend/main.py`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Export Services Validation

Verify the three review export formats against an audited document. The backend container must include `libreoffice-writer`, `fonts-dejavu`, and `fonts-liberation`; PDF reports are converted from a temporary DOCX with Headless LibreOffice.

| Format | Endpoint | Verification Command | Expected Output |
| :--- | :--- | :--- | :--- |
| **PDF Review Report** | `GET /api/v1/documents/{id}/export?format=pdf` | `curl -f -o review.pdf "$API/documents/$DOC_ID/export?format=pdf"` | HTTP 200 and a readable PDF generated from the configured review DOCX; language/mechanics section omitted by default |
| **DOCX Review Report** | `GET /api/v1/documents/{id}/export?format=docx` | `curl -f -o review.docx "$API/documents/$DOC_ID/export?format=docx"` | Editable report with language/mechanics section omitted by default |
| **Annotated Source PDF** | `GET /api/v1/documents/{id}/export?format=annotated_pdf` | `curl -f -o annotated.pdf "$API/documents/$DOC_ID/export?format=annotated_pdf"` | Valid source PDF with `/Annots` objects and finding overlays |

To opt into spelling/grammar/mechanics entries in the DOCX or PDF report, append `&include_language_mechanics=true` to the export URL. The section groups repeated matching findings and lists the affected pages.

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
   - Restart worker processes: `docker compose restart worker`
2. **Database OCC Version Collision (`409 Conflict`)**:
   - Occurs when two reviewers submit simultaneous decisions for the same issue version.
   - Client automatically displays conflict banner and refreshes the finding item with latest state.
3. **Corrupted File or Malformed Upload**:
   - Storage service isolates uploads into safe subdirectories with SHA-256 deduplication.
   - If an upload fails validation, temporary unlinked files are cleaned up immediately via `_delete_stored_object`.

## 9. BIMA Catalog and On-Demand Import Smoke Checklist

Run after migrations and before exposing the server:

1. Open `/login`; confirm only **Sign in with BIMA SSO** appears, with no email/password or registration form.
2. Complete BIMA SSO and confirm PRISM returns to the configured app origin with an authenticated session.
3. Call `GET /api/v1/bima/catalog`; confirm the flat BIMA directory returns with `is_imported: false` for projects PRISM does not have.
4. Import one project from the `Tambah dari BIMA` modal; confirm `201` and that the response `owner_id` is the signed-in user.
5. Import the same project again; confirm `200` with the identical `id` and that no duplicate row exists (`SELECT count(*) FROM projects WHERE bima_project_id = <id>` returns 1).
6. Re-open the catalog; confirm that project now reports `is_imported: true` with its `prism_project_id`.
7. Sign in as an engineer who did not import the project and call `GET /api/v1/projects`; confirm the project is not listed and `GET /api/v1/projects/{id}/documents` returns an empty list rather than foreign documents.
8. Confirm lead/superuser retain global project/document visibility.
9. Open `/settings/profile`, update the name, and confirm the navbar reflects it after reload.
10. Confirm long project, admin, and settings pages scroll on desktop and mobile widths.
