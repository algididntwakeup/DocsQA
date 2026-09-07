# START HERE — DocsQA Execution Index

This is the central index every new agent must read in full. Repository state always overrides stale prose.

## Current checkpoint

- **Product Orientation**: Reoriented from an approval/audit system to a deterministic engineering-document review report generator.
- **Core Deliverables**:
  1. Formal DOCX review report (`python-docx`).
  2. Annotated source PDF with highlight bounding boxes and notes (`pypdf`).
- **Curation Workflow**:
  - Finding curation is strictly binary inclusion (`included_in_report: bool`, default `True`) and an optional engineering clarification (`reviewer_note: str | None`).
  - Completely removed: issue decisions (`ACCEPTED`/`REJECTED`), lead dispositions, audit trail events, and bulk decision workflows.
- **Delivery Plan Progress**:
  - **Item 1 (Complete)**: Replaced approval and audit workflow with report curation across database models, Alembic migration `20260907_0006_report_curation`, FastAPI endpoints, and UI.
  - **Item 2 (Complete)**: Added deterministic DOCX report builder (`backend/services/report.py`), report preview endpoint/modal, and restricted export panel to DOCX and annotated PDF.
- **Quality Status**:
  - Backend: **195 passed, 1 skipped, 0 failed** (Ruff check clean, Mypy clean with 64 files, Alembic offline upgrade valid).
  - Frontend: **39 passed, 0 failed** across 11 test suites (TypeScript clean, ESLint clean, Next.js Turbopack build succeeds).
- **Never push to GitHub**; the owner pushes. Local commits are allowed only after quality gates pass.

## Source precedence

1. `docs/PRODUCT_SPEC.md` — product behavior, scope, and non-goals.
2. `docs/REPORT_SPEC.md` — deterministic DOCX review report structure.
3. `docs/UI_SPEC.md` — review workspace, curation UI, and export panels.
4. `docs/ARCHITECTURE.md` — extraction, evidence, and report generators.
5. `docs/DELIVERY_PLAN.md` — active delivery roadmap.
6. `docs/TEST_CORPUS.md` — synthetic and de-identified fixture policies.
7. `backend/openapi.json` — frontend/backend wire contract.

If these conflict, record the conflict. Do not silently blend them.

## Document map

| File | Use when |
|---|---|
| `docs/PRODUCT_SPEC.md` | Resolving product scope, rules, and boundaries |
| `docs/REPORT_SPEC.md` | Building or validating DOCX review report sections |
| `docs/UI_SPEC.md` | Updating review workspace, findings panel, or modals |
| `docs/ARCHITECTURE.md` | Pipeline, analyzer, evidence, or storage design |
| `docs/DELIVERY_PLAN.md` | Tracking milestones and roadmap execution |
| `docs/TEST_CORPUS.md` | Adding or managing test fixtures and documents |
| `docs/design_system.md` | Styling components according to design tokens |

## Required quality commands

```powershell
# Backend quality gate
Set-Location backend
.\scripts\quality.ps1

# Frontend quality gate
Set-Location ..\frontend
npm run generate:api
npm run typecheck
npm run lint
npm run test
npm run build
```

## Commitments & Rules

- **Zero External AI / LLM APIs**: All analysis, reports, and evidence are 100% deterministic.
- **Confidentiality**: Never commit client or sample documents; commit only synthetic/de-identified fixtures.
- **Local Commits Only**: Do not execute `git push`.
