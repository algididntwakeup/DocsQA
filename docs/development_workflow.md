# Development Workflow — Document QC System

> **Purpose:** Defines the sprint structure, branching strategy, CI/CD pipeline, and coordination rules for building the Document QC & Traceability Audit Web Application.

> **Planning note (2026-09-04):** This file describes the original target
> sprints. The repository has not completed Sprint 1. Follow the dependency and
> gate order in `docs/implementation_readiness_and_execution_plan.md` for actual
> execution; that plan inserts a required M0 contract/foundation gate and moves
> deterministic P0 traceability ahead of linguistic tuning.

---

## 1. Sprint Structure

### Sprint 1 — Foundation (Weeks 1-2)
**Goal:** Upload a document and get extracted text back.

| # | Task | Owner | Depends On |
|---|---|---|---|
| 1.1 | `extract.py` — PDF text + table extraction (PyMuPDF) | Backend | — |
| 1.2 | `extract.py` — DOCX text + table extraction (python-docx) | Backend | — |
| 1.3 | `POST /documents/upload` endpoint | Backend | 1.1, 1.2 |
| 1.4 | `GET /documents/{id}/status` endpoint | Backend | 1.3 |
| 1.5 | Upload UI (DropZone + progress) | Frontend | — |
| 1.6 | Document list page + StatusBadge | Frontend | 1.4 |
| 1.7 | Database schema + Alembic migrations | Backend | — |
| 1.8 | Docker Compose (PostgreSQL + Redis) | DevOps | — |

**Exit Criteria:** User can upload a PDF/DOCX, see it in the document list, and the backend extracts text successfully.

---

### Sprint 2 — Linguistic Pipeline (Weeks 3-4)
**Goal:** Run the full linguistic scan and see issues.

| # | Task | Owner | Depends On |
|---|---|---|---|
| 2.1 | `spellcheck.py` — pyspellchecker + dictionary | Backend | 1.1 |
| 2.2 | `grammar.py` — LanguageTool integration | Backend | 1.1 |
| 2.3 | `duplicate.py` — RapidFuzz near-duplicate detection | Backend | 1.1 |
| 2.4 | `ambiguity.py` — spaCy NER + EntityRuler | Backend | 1.1 |
| 2.5 | Celery task chain (extract → linguistic group → aggregate) | Backend | 2.1-2.4 |
| 2.6 | `GET /documents/{id}/issues?category=linguistic` | Backend | 2.5 |
| 2.7 | Custom Dictionary API (CRUD) | Backend | — |
| 2.8 | Dictionary management UI | Frontend | 2.7 |

**Exit Criteria:** Upload triggers an async scan; linguistic issues are returned via API.

---

### Sprint 3 — Traceability Pipeline (Weeks 5-6) ⚠️ P0-CRITICAL
**Goal:** All four CTO audit checks operational.

| # | Task | Owner | Depends On |
|---|---|---|---|
| 3.1 | `trace_numbers.py` — table math validation | Backend | 1.1 |
| 3.2 | `ref_drift.py` — ToC/LoF/LoT reference drift | Backend | 1.1 |
| 3.3 | `revision_sync.py` — filename/cover/rev-sheet sync | Backend | 1.1 |
| 3.4 | `standard_traceability.py` — standard/code cross-ref | Backend | 1.1 |
| 3.5 | Standards Registry API + admin UI | Backend + FE | — |
| 3.6 | Extend Celery chain: add traceability group | Backend | 3.1-3.4 |
| 3.7 | `GET /documents/{id}/issues?category=traceability` | Backend | 3.6 |
| 3.8 | Traceability summary endpoint | Backend | 3.7 |

**Exit Criteria:** All four traceability checks produce correct findings on test documents; issues are categorized separately from linguistic.

---

### Sprint 4 — Split-Screen Review UI (Weeks 7-8)
**Goal:** Full review workflow operational.

| # | Task | Owner | Depends On |
|---|---|---|---|
| 4.1 | SplitScreenViewer with react-resizable-panels | Frontend | — |
| 4.2 | DocumentPane — pdf.js rendering + DOCX-HTML | Frontend | — |
| 4.3 | HighlightOverlay — coordinate-based highlights | Frontend | 4.2 |
| 4.4 | IssuePanel — tabbed view (Language / Traceability) | Frontend | — |
| 4.5 | IssueCard — actions (Accept, Reject, Edit, Flag) | Frontend | 4.4 |
| 4.6 | Issue ↔ Document linking (click issue → scroll to location) | Frontend | 4.3, 4.5 |
| 4.7 | `PATCH /issues/{id}/decision` endpoint | Backend | — |
| 4.8 | BulkActions component | Frontend | 4.5 |

**Exit Criteria:** Reviewer can view a document side-by-side with its issues, click to navigate, and accept/reject findings.

---

### Sprint 5 — Export, Polish & Integration (Weeks 9-10)
**Goal:** Production-ready MVP.

| # | Task | Owner | Depends On |
|---|---|---|---|
| 5.1 | Export: annotated PDF generation | Backend | 4.7 |
| 5.2 | Export: Issue Log CSV/XLSX (two sheets) | Backend | 4.7 |
| 5.3 | `GET /documents/{id}/export` endpoint | Backend | 5.1, 5.2 |
| 5.4 | WebSocket/SSE for real-time scan progress | Backend + FE | — |
| 5.5 | Lead Reviewer disposition workflow | Backend + FE | 4.7 |
| 5.6 | RBAC (Inspector, QA Engineer, Lead Reviewer, Admin) | Backend + FE | — |
| 5.7 | Keyboard shortcuts (J/K/A/R/E) | Frontend | 4.5 |
| 5.8 | End-to-end test suite (Playwright) | QA | All |
| 5.9 | Performance optimization (virtualized lists, lazy loading) | Frontend | 4.4 |
| 5.10 | Dark mode | Frontend | — |

**Exit Criteria:** Full Upload → Scan → Review → Export workflow works E2E; all P0 features operational.

---

## 2. Branching Strategy

```
main                    ← production-ready; protected
  └── develop           ← integration branch
       ├── feature/sprint1-extract
       ├── feature/sprint2-linguistic-pipeline
       ├── feature/sprint3-traceability-pipeline
       ├── feature/sprint4-review-ui
       └── fix/trace-numbers-tolerance
```

- **Feature branches** are created from `develop`, merged back via PR
- **Hotfix branches** are created from `main` for critical bugs
- PR requires: passing tests + 1 review approval

---

## 3. Development Environment

### 3.1 Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Node.js | 20+ | Frontend runtime |
| Python | 3.11+ | Backend runtime |
| Docker | Latest | PostgreSQL, Redis, LanguageTool |
| Git | Latest | Version control |

### 3.2 Quick Start

```bash
# 1. Clone & enter project
cd DocsQA

# 2. Start infrastructure
docker compose up -d  # PostgreSQL, Redis, LanguageTool

# 3. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev  # → http://localhost:3000
```

### 3.3 Environment Variables

Create `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docqc
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=["http://localhost:3000"]
UPLOAD_DIR=./uploads
LANGUAGE_TOOL_HOST=http://localhost:8081
TABLE_MATH_TOLERANCE_PERCENT=0.5
```

---

## 4. Testing Protocol

### 4.1 Per-Sprint Test Requirements

| Sprint | Test Type | Requirement |
|---|---|---|
| Sprint 1 | Unit tests for extract.py | ≥1 PDF + ≥1 DOCX test fixture |
| Sprint 2 | Unit tests per linguistic service | Happy path + edge case per service |
| Sprint 3 | Unit tests per traceability service | ≥3 test fixtures per service (correct, mismatch, malformed) |
| Sprint 4 | Component tests for review UI | SplitScreen, IssueCard rendering + interaction |
| Sprint 5 | E2E tests | Full flow: Upload → Scan → Review → Export |

### 4.2 Test Fixtures

Maintain test documents in `backend/tests/fixtures/`:
```
fixtures/
├── valid_report.pdf          # Clean document (no issues expected)
├── typos_report.pdf          # Known spelling errors
├── math_mismatch.pdf         # Table with wrong totals
├── ref_drift.pdf             # ToC with wrong page numbers
├── revision_mismatch.pdf     # Filename rev ≠ cover rev
├── missing_standard.pdf      # Body cites ASME, not in bibliography
└── valid_report.docx         # DOCX equivalent of valid_report
```

---

## 5. CI/CD Pipeline

```
On PR to develop:
  ├── Lint (ruff + eslint)
  ├── Type-check (mypy + tsc)
  ├── Unit tests (pytest + jest)
  └── Build check (next build)

On merge to main:
  ├── All of the above
  ├── Integration tests
  ├── E2E tests (Playwright)
  └── Deploy to staging
```

---

## 6. Coordination Rules

1. **Backend-first for data contracts.** API response shapes are defined in `docs/backend_plan.md` — frontend must code against these contracts.
2. **No cross-layer imports.** Frontend never imports backend code; they communicate only via HTTP.
3. **Feature flags for incomplete features.** If a sprint's frontend isn't ready but backend is, the API is deployed but the UI route is hidden behind a feature flag.
4. **Daily sync on Sprint 3.** Traceability pipeline is P0-CRITICAL — any blockers escalated immediately.
5. **Test fixtures are shared.** The same test documents are used by backend unit tests and E2E tests.
