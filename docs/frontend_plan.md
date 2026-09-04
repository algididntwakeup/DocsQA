# Frontend Implementation Plan — Document QC System

> **Source of Truth:** `docs/Document_QC_WebApp_PRD.md` §4.2

> **Implementation status (2026-09-04):** Target design only; the current
> frontend is the default scaffold. Execute through
> `docs/implementation_readiness_and_execution_plan.md` and its milestone gates.

---

## 1. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | Next.js 14+ (App Router) | SSR/SSG flexibility, API route proxying |
| Language | TypeScript | Type safety across components + API calls |
| Styling | Tailwind CSS | Utility-first, rapid iteration |
| UI Components | shadcn/ui | Accessible, composable primitives |
| Icons | Lucide React | Consistent, tree-shakeable icon set |
| PDF Rendering | pdf.js (`react-pdf`) | In-browser PDF viewing with text layer |
| DOCX Rendering | mammoth.js | Server-side DOCX → HTML conversion |
| Resizable Panels | `react-resizable-panels` | Split-screen review layout |
| Server State | React Query (TanStack Query) | Caching, polling, mutation management |
| Client State | Zustand | Lightweight store for review decisions |
| Virtualized Lists | `@tanstack/react-virtual` | Performance for large issue lists |
| Design Source | Stitch via MCP | Fetch approved screens and design DNA for agent implementation |

### 1.1 Stitch MCP Design Handoff

- Stitch is used at development time only; the shipped application must not
  require the Stitch MCP server or its API key.
- Store the API key only in the user's MCP/secret configuration and never in
  `.env`, source files, screenshots, logs, or committed documentation.
- Before implementing a screen, fetch the exact Stitch project and screen,
  then update `docs/design_system.md` and `docs/design_handoff.md` with tokens,
  component states, source IDs, and snapshot date.
- Precedence is: PRD for behavior and accessibility, OpenAPI for data, Stitch
  for layout and visual styling. Record conflicts rather than guessing.
- Verify implemented screens with browser screenshots at the agreed viewport
  sizes. A visually close static page is not complete if loading, empty, error,
  keyboard, focus, or responsive states are missing.

---

## 2. Application Structure

```
frontend/src/
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # Root layout (fonts, providers, nav)
│   ├── page.tsx                   # Dashboard / document list
│   ├── upload/
│   │   └── page.tsx               # Upload page (drag-drop, batch)
│   ├── documents/
│   │   └── [id]/
│   │       ├── page.tsx           # Document detail / status
│   │       └── review/
│   │           └── page.tsx       # Split-screen review UI ★
│   ├── dictionary/
│   │   └── page.tsx               # Custom Engineering Dictionary CRUD
│   └── settings/
│       └── page.tsx               # Admin: Standards Registry, tolerances
├── components/
│   ├── layout/
│   │   ├── Navbar.tsx
│   │   ├── Sidebar.tsx
│   │   └── PageHeader.tsx
│   ├── upload/
│   │   ├── DropZone.tsx           # Drag-and-drop file upload
│   │   └── UploadProgress.tsx     # Per-file upload status
│   ├── review/
│   │   ├── SplitScreenViewer.tsx  # Main resizable two-pane layout ★
│   │   ├── DocumentPane.tsx       # Left: PDF/DOCX rendering + highlights
│   │   ├── IssuePanel.tsx         # Right: tabbed issue browser
│   │   ├── IssueCard.tsx          # Single issue display + actions
│   │   ├── HighlightOverlay.tsx   # Coordinate-based highlight layer
│   │   └── BulkActions.tsx        # Bulk accept/reject controls
│   ├── document/
│   │   ├── DocumentCard.tsx       # Document list item
│   │   ├── StatusBadge.tsx        # QUEUED/PROCESSING/COMPLETED badge
│   │   └── ScanProgress.tsx       # Per-stage progress bars
│   └── shared/
│       ├── DataTable.tsx
│       ├── FilterBar.tsx
│       └── ExportButton.tsx
├── lib/
│   ├── api.ts                     # Axios/fetch wrapper for backend calls
│   ├── types.ts                   # Shared TypeScript interfaces
│   └── constants.ts               # Severity colors, category labels
├── hooks/
│   ├── useDocuments.ts            # React Query hooks for documents
│   ├── useIssues.ts               # React Query hooks for issues
│   ├── useScanProgress.ts         # WebSocket/SSE hook for live progress
│   └── useReviewStore.ts          # Zustand store for review session
└── styles/
    └── globals.css                # Tailwind base + custom tokens
```

---

## 3. Key UI Specifications

### 3.1 Split-Screen Review UI (★ Core Feature)

```
┌──────────────────────────────────────────────────────────────────┐
│  Navbar: Document Title | Status Badge | Export Button           │
├───────────────────────────────┬──────────────────────────────────┤
│                               │  [Language] [Traceability & ...]  │
│   Document Pane               │  ─────────────────────────────── │
│   (pdf.js / DOCX-HTML)        │  Filter: Severity ▼  Type ▼     │
│                               │  ─────────────────────────────── │
│   ░░░ highlighted text ░░░    │  ┌─ Issue Card ──────────────┐  │
│   ░░░ (yellow=linguistic,     │  │ ⚠ TABLE_MATH_MISMATCH     │  │
│   ░░░  red=traceability)      │  │ Page 12, Table 3, Row 8   │  │
│                               │  │ Computed: 142.5            │  │
│                               │  │ Stated:   143.0            │  │
│                               │  │ Delta:    +0.5             │  │
│                               │  │ [Accept] [Reject] [Flag]   │  │
│                               │  └────────────────────────────┘  │
│   ◄─── resizable ───►        │  ┌─ Issue Card ──────────────┐  │
│                               │  │ ...                        │  │
├───────────────────────────────┴──────────────────────────────────┤
│  Status Bar: 12 issues remaining | 3 critical | 45% reviewed    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Color System

| Severity | Color | Hex |
|---|---|---|
| Critical | Red | `#DC2626` |
| High | Orange | `#EA580C` |
| Medium | Amber | `#D97706` |
| Low | Blue | `#2563EB` |
| Linguistic highlight | Yellow | `rgba(250, 204, 21, 0.3)` |
| Traceability highlight | Red | `rgba(239, 68, 68, 0.3)` |

### 3.3 Interaction Patterns

- **Click issue card** → Left pane scrolls to the exact page/position, highlights pulse
- **Table Math issues** → Both the offending cell AND the total cell are highlighted simultaneously
- **Reference Drift** → Both the ToC entry and the actual page are highlighted, with a "Jump to" toggle
- **Bulk Accept** → Available only for Linguistic tab; disabled for Traceability by default (per PRD §3.2)
- **Keyboard shortcuts** → `J/K` to navigate issues, `A` to accept, `R` to reject, `E` to edit

---

## 4. State Management

### 4.1 Server State (React Query)

```typescript
// Key query patterns
useQuery(['document', id])                          // Document metadata
useQuery(['document', id, 'issues', { category }])  // Issue list
useQuery(['document', id, 'status'])                // Scan status (polling)
useMutation(['issues', id, 'decision'])             // Accept/reject
```

### 4.2 Client State (Zustand)

```typescript
interface ReviewStore {
  // In-session decisions (before committing to server)
  pendingDecisions: Map<string, Decision>;
  activeIssueId: string | null;
  activeTab: 'language' | 'traceability';
  filters: { severity: string[]; type: string[] };

  // Actions
  setDecision: (issueId: string, decision: Decision) => void;
  commitDecisions: () => Promise<void>;
  setActiveIssue: (id: string) => void;
}
```

---

## 5. Real-Time Updates

- **Scan Progress:** WebSocket connection to `ws://backend/ws/scan/{docId}`
- **Per-stage progress:** Backend publishes `{stage: "trace_numbers", progress: 60}` events
- **Fallback:** SSE polling at 2-second intervals if WebSocket not available

---

## 6. Additional Libraries to Install

```bash
cd frontend
npm install @tanstack/react-query zustand react-resizable-panels
npm install react-pdf pdfjs-dist mammoth
npm install lucide-react
npm install @tanstack/react-virtual
# shadcn/ui (initialized separately)
npx shadcn-ui@latest init
```

---

## 7. Implementation Phases

### Phase A — Shell & Navigation (Sprint 1)
- Root layout with Navbar + Sidebar
- Dashboard page (placeholder)
- Upload page with DropZone

### Phase B — Document Lifecycle (Sprint 1-2)
- Document list with status badges
- Upload → backend integration
- Scan progress with per-stage indicators

### Phase C — Split-Screen Review (Sprint 4)
- `react-resizable-panels` layout
- PDF rendering with `react-pdf`
- Issue panel with tabs + filtering
- Highlight overlay system
- Issue card actions (accept/reject/edit)

### Phase D — Export & Polish (Sprint 4-5)
- Export buttons (PDF, XLSX)
- Dictionary management UI
- Keyboard shortcuts
- Responsive design pass
- Dark mode support
