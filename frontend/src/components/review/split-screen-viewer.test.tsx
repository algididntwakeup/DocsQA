import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SplitScreenViewer } from "./split-screen-viewer";
import * as api from "@/lib/api";
import type { DocumentItem, IssueItem } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listAuditEvents: vi.fn(),
    getTraceabilitySummary: vi.fn(),
    setDocumentDisposition: vi.fn(),
    decideIssue: vi.fn(),
    disposeIssue: vi.fn(),
    bulkDecideIssues: vi.fn(),
    listDocumentIssues: vi.fn(),
  };
});

describe("SplitScreenViewer", () => {
  const mockDoc: DocumentItem = {
    id: "doc-test-123",
    filename: "hydraulic_spec_v2.pdf",
    media_type: "application/pdf",
    size_bytes: 54000,
    sha256: "a".repeat(64),
    status: "COMPLETED",
    review_status: "PENDING",
    progress_pct: 100,
    page_count: 5,
    created_at: "2026-09-05T10:00:00Z",
    updated_at: "2026-09-05T10:05:00Z",
  };

  const mockIssues: IssueItem[] = [
    {
      id: "iss-1",
      document_id: "doc-test-123",
      category: "TRACEABILITY",
      type: "RULE_TABLE_MATH_001",
      severity: "CRITICAL",
      confidence: 0.95,
      message: "Row sum error",
      version: 1,
      evidence: {
        kind: "TABLE_MATH",
        extractor_version: "1.0",
        rule_version: "1.0",
        stated_value: "100.00",
        computed_value: "105.00",
        delta: "5.00",
        tolerance: "0.01",
        total_location: {
          page_index: 0,
          x0: 100,
          y0: 200,
          x1: 300,
          y1: 250,
          page_width: 612,
          page_height: 792,
        },
        operand_locations: [],
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listAuditEvents).mockResolvedValue({
      total: 1,
      events: [
        {
          id: "audit-1",
          document_id: "doc-test-123",
          action: "ISSUE_DECISION",
          actor_id: "qa@local",
          actor_role: "QA_ENGINEER",
          created_at: "2026-09-05T10:30:00Z",
          previous_state: { status: "PENDING" },
          new_state: { status: "ACCEPTED" },
          notes: "Approved after recalculation",
        },
      ],
    });

    vi.mocked(api.getTraceabilitySummary).mockResolvedValue({
      document_id: "doc-test-123",
      counts_by_type: { RULE_TABLE_MATH_001: 1 },
      counts_by_severity: { CRITICAL: 1 },
      critical_count: 1,
      unresolved_count: 1,
    });
  });

  it("renders document title and findings in split panes", () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    expect(screen.getByText("hydraulic_spec_v2.pdf")).toBeDefined();
    expect(screen.getAllByText("RULE_TABLE_MATH_001").length).toBeGreaterThanOrEqual(1);
  });

  it("opens audit trail modal when Audit Trail button is clicked", async () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    const auditBtn = screen.getByRole("button", { name: /audit trail/i });
    fireEvent.click(auditBtn);

    await waitFor(() => {
      expect(screen.getByText("Document Audit Trail")).toBeDefined();
      expect(screen.getByText(/Approved after recalculation/i)).toBeDefined();
    });
  });

  it("allows Lead Reviewer to approve document with required justification", async () => {
    vi.mocked(api.setDocumentDisposition).mockResolvedValue({
      ...mockDoc,
      review_status: "APPROVED",
    });

    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    // Click Approve Document in bottom footer
    const approveBtn = screen.getByRole("button", { name: /approve document/i });
    fireEvent.click(approveBtn);

    // Modal opens asking for justification
    expect(screen.getByText("Approve Document Sign-Off")).toBeDefined();

    const textarea = screen.getByLabelText(/justification \/ audit notes/i);
    fireEvent.change(textarea, { target: { value: "Sign-off verified by chief engineer" } });

    const confirmBtn = screen.getByRole("button", { name: /confirm approval/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.setDocumentDisposition).toHaveBeenCalledWith("doc-test-123", {
        disposition: "APPROVED",
        justification: "Sign-off verified by chief engineer",
        actor_id: "lead_reviewer@local",
        actor_role: "LEAD_REVIEWER",
      });
    });
  });

  it("opens export modal when Export button is clicked", async () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    const exportBtn = screen.getByTestId("open-export-modal-btn");
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByText("Export Findings & Audit Package")).toBeDefined();
      expect(screen.getByTestId("export-pdf-btn")).toBeDefined();
      expect(screen.getByTestId("export-xlsx-btn")).toBeDefined();
      expect(screen.getByTestId("export-csv-btn")).toBeDefined();
      expect(screen.getByTestId("export-json-btn")).toBeDefined();
    });
  });
});
