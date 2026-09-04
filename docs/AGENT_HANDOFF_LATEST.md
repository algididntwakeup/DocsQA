# Agent Handoff (Latest)

## Resume point

Resume **DocsQA Project** starting from **M1.4 (Extraction workers)** or **M1.5 (Minimal frontend lifecycle)**. 
All commits should be made **locally only**. Do not push to GitHub; the product owner will push manually.

## Repository state

- M1.2 (Secure native-text upload) is **COMPLETE**.
- M0.5 (Stitch MCP Setup & Baseline) is **COMPLETE**. `docs/design_system.md` has been generated from Stitch Project `9978725055094825738`.
- M1.3 (Versioned extraction service) is **COMPLETE**. Implementation included PDFExtractor (PyMuPDF) and DOCXExtractor (soffice fallback), schemas, and unit tests.
- Latest local commit: `feat(extract): implement extraction service (M1.3)`.
- Existing local commits are authored with the repository user's Git identity.
- The project is a root monorepo: `backend/` FastAPI and `frontend/` Next.js.

## Next Work (M1.4 or M1.5)

- Review `docs/implementation_readiness_and_execution_plan.md` to pick up the next milestone.
- **M1.4 Extraction workers**: Implement Celery/arq plumbing to process extraction in the background. Note: DB / Redis local infrastructure may need to be spun up via Docker first.
- **M1.5 Minimal frontend lifecycle**: Initialize Next.js structure and apply the Material QC Stitch Design System.

## General Rules

- Do **not** run `git push`. All commits remain local.
- For Stitch / MCP usage on a new device, ensure the Stitch MCP server is authenticated via Settings -> MCP Servers.
- Use `npm run generate:api` and `npm run check` in `frontend` for frontend validation.
- Use `pytest tests/ -v` and `scripts/quality.ps1` in `backend` for backend validation. (Note: PyMuPDF DLLs may skip tests locally if the Windows container lacks specific VC++ dependencies, but logic should remain structurally complete).
