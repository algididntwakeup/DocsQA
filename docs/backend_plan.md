# Backend Implementation Plan — Document QC System

> **Source of Truth:** `docs/Document_QC_WebApp_PRD.md` §4.3

> **Implementation status (2026-09-04):** Target design only; the current
> backend is a scaffold. Execute through
> `docs/implementation_readiness_and_execution_plan.md` and its milestone gates.

---

## 1. Architecture Overview

```
backend/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── core/
│   ├── __init__.py
│   └── config.py              # Pydantic Settings (env vars)
├── api/                       # Thin HTTP layer
│   ├── __init__.py
│   ├── documents.py           # Upload, status, export, traceability-summary
│   ├── issues.py              # Decision, disposition
│   ├── dictionary.py          # CRUD + governance
│   └── standards.py           # Standards Registry admin
└── services/                  # Business logic (pipeline stages)
    ├── __init__.py
    ├── extract.py             # Stage 0: Text/layout/table extraction
    ├── spellcheck.py          # Stage 1: Spelling (pyspellchecker)
    ├── grammar.py             # Stage 2: Grammar (LanguageTool)
    ├── duplicate.py           # Stage 3: Duplicate detection (thefuzz)
    ├── ambiguity.py           # Stage 4: Contextual ambiguity (spaCy)
    ├── trace_numbers.py       # Stage 6: Table math validation [F10]
    ├── ref_drift.py           # Stage 7: Reference drift [F11]
    ├── revision_sync.py       # Stage 8: Revision sync [F12]
    ├── standard_traceability.py # Stage 9: Standard traceability [F13]
    └── aggregate.py           # Stage 10: Issue normalization
```

---

## 2. API Endpoint Specifications

### 2.1 Documents

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload PDF/DOCX | `multipart/form-data` | `{id, filename, status: QUEUED}` |
| `GET` | `/api/v1/documents/{id}/status` | Poll scan status | — | `{status, progress_pct, stages: [{name, status}]}` |
| `GET` | `/api/v1/documents/{id}/issues` | List issues | `?category=linguistic\|traceability` | `{issues: [...], total, by_severity: {}}` |
| `GET` | `/api/v1/documents/{id}/export` | Export results | `?format=pdf\|xlsx` | Binary file download |
| `GET` | `/api/v1/documents/{id}/traceability-summary` | Audit summary | — | `{counts_by_type, critical_count}` |

### 2.2 Issues

| Method | Path | Description |
|---|---|---|
| `PATCH` | `/api/v1/issues/{id}/decision` | Accept / Reject / Edit |
| `PATCH` | `/api/v1/issues/{id}/disposition` | Lead Reviewer: Justified Exception / Requires Correction |

### 2.3 Dictionary

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/dictionary/terms` | Propose a new term |
| `GET` | `/api/v1/dictionary/terms` | List terms (filter by scope) |
| `PATCH` | `/api/v1/dictionary/terms/{id}/approve` | Admin approval |

### 2.4 Standards Registry

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/standards-registry` | Register a code pattern |

---

## 3. Service Implementation Details

### 3.1 extract.py (Stage 0 — Shared)

**Input:** Uploaded file (PDF or DOCX)
**Output:** `ExtractionResult` dataclass containing:
- `pages: list[Page]` — each with `text`, `spans` (with font metadata), `page_number`
- `tables: list[Table]` — each with `cells: list[list[Cell]]`, `page`, `bbox`
- `metadata: DocumentMetadata` — filename, file type, page count
- `headings: list[Heading]` — text, level, page, position (for ref_drift)

**Libraries:**
- PDF: `PyMuPDF` (fitz) for text/spans/font metadata; `pdfplumber` for table extraction
- DOCX: `python-docx` for paragraphs, tables, styles

### 3.2 Linguistic Pipeline (Stages 1-4)

Each service follows the same contract:
```python
def analyze(extraction: ExtractionResult, config: Settings) -> list[Issue]:
    ...
```

### 3.3 Traceability Pipeline (Stages 6-9)

Same contract as linguistic, but outputs include additional fields:
- `computed_value`, `stated_value`, `delta` (trace_numbers)
- `referenced_page`, `actual_page` (ref_drift)
- `sources_disagreeing: list[str]` (revision_sync)
- `cited_standard`, `bibliography_entry` (standard_traceability)

### 3.4 aggregate.py (Stage 10)

Normalizes all outputs into the unified `Issue` schema per PRD §4.3.2 item 10.

---

## 4. Data Models (Pydantic)

```python
class Issue(BaseModel):
    issue_id: str
    doc_id: str
    category: Literal["LINGUISTIC", "TRACEABILITY"]
    type: str              # e.g., TABLE_MATH_MISMATCH, REF_DRIFT, SPELLING
    page: int
    span_or_bbox: dict     # {start, end} or {x0, y0, x1, y1}
    original_value: str | None
    expected_value: str | None
    delta: float | None
    suggestion: str | None
    confidence: float
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
```

---

## 5. Task Queue Architecture

```
Celery Chain:
  extract.py
    ├── group([spellcheck, grammar, duplicate, ambiguity])     # Linguistic branch
    ├── group([trace_numbers, ref_drift, revision_sync, standard_traceability])  # Traceability branch
    └── aggregate.py  (runs after both groups complete)
```

- Each subtask has independent try/except — failure is logged as `STAGE_FAILED`
- Per-stage progress reported via Redis pub/sub → WebSocket/SSE to frontend

---

## 6. Database Schema (Key Tables)

| Table | Key Columns |
|---|---|
| `documents` | id, filename, status, filename_revision, detected_cover_revision, uploaded_at |
| `issues` | id, doc_id, category, type, page, severity, decision, disposition, created_at |
| `dictionary_terms` | id, term, scope, status (proposed/approved), created_by |
| `standards_registry` | id, code_pattern, description, org_scope |
| `audit_log` | id, issue_id, action, actor, timestamp (immutable) |

---

## 7. Environment Setup

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy model
python -m spacy download en_core_web_sm

# 4. Start LanguageTool server (Docker recommended)
docker run -d -p 8081:8010 erikvl87/languagetool

# 5. Start Redis
docker run -d -p 6379:6379 redis:alpine

# 6. Run the API
uvicorn main:app --reload --port 8000
```
