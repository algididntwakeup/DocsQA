# START HERE — Document QC Agent Handoff

Use this file when continuing the project in a new chat, with a new agent, or
on another computer. Chat history is not required if the complete repository,
including `/docs`, is available.

## Current State

The product direction is documented, but implementation is still a scaffold.
Do not begin linguistic, traceability, review, or export features until the M0
and M1 gates in the execution plan are complete.

## Required Reading Order

1. `docs/START_HERE.md`
2. `docs/Document_QC_WebApp_PRD.md`
3. `docs/implementation_readiness_and_execution_plan.md`
4. `docs/acceptance_matrix.md`
5. `docs/agent_execution_playbook.md`
6. `docs/backend_plan.md` or `docs/frontend_plan.md` for the active ticket
7. Every applicable `AGENTS.md` in the target directory tree

The PRD controls product behavior. The implementation readiness plan controls
execution order and milestone gates. OpenAPI controls FE/BE data contracts.
Stitch controls visual design only.

## First Ticket

M0.1 was completed on 2026-09-04: the nested frontend repository was flattened
into the product-root monorepo while retaining the frontend commit as merge
history. Runtime pins are Node.js 24.20.0 and Python 3.13.15. Start with the next
unblocked M0 ticket shown in the execution plan and verify actual Git state
before relying on this handoff note.

## Stitch MCP Prerequisite

Before frontend ticket M1.5:

1. Connect the user's Stitch account through MCP.
2. Verify the intended Stitch project and screen identifiers.
3. Create/update `docs/design_system.md` and `docs/design_handoff.md`.
4. Store the Stitch API key only in MCP/secret configuration—never in the repo.
5. Use PRD for behavior/accessibility, OpenAPI for data, and Stitch for visuals.

## Bootstrap Prompt for a New Agent

Copy this prompt into the new task:

```text
Continue the Document QC project from this repository. Chat history is not
available and must not be assumed.

Read docs/START_HERE.md first, then follow its required reading order. Inspect
the actual repository before changing anything. Use
docs/implementation_readiness_and_execution_plan.md as the delivery source of
truth and work only on the next unblocked ticket. Respect every applicable
AGENTS.md.

For the active ticket, state its dependencies, allowed file scope, observable
outcome, tests, definition of done, and non-goals. Preserve existing work. Do
not skip milestone gates or treat TODO scaffolds as completed functionality.
Run focused verification and update the execution-plan evidence before handing
off. For frontend work, use the connected Stitch MCP project as the visual
source, but never place credentials in the repository.

Start by verifying the M0.1 evidence, then work on the next unblocked M0 ticket.
Report any decision that requires repository-owner approval before performing
destructive or history-rewriting Git operations.
```

## Owner Checklist for a New Laptop

- Copy or clone the entire product root, not only `frontend/`.
- Confirm these directories exist: `docs/`, `backend/`, and `frontend/`.
- Install the pinned Node and Python versions once M0.1 records them.
- Install Docker/compatible containers for PostgreSQL, Redis, and LanguageTool.
- Configure Stitch MCP locally and keep its API key outside the repository.
- Create local environment files from committed `.env.example` files after M0.
- Run the quality commands documented by M0.4 before starting feature work.

## Completion Rule

A new agent is correctly onboarded when it can name the current milestone,
identify the next unblocked ticket, explain its testable outcome, and locate the
PRD, API contract, and Stitch design source without relying on chat history.
