import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SplitScreenViewer } from "./split-screen-viewer";
import * as api from "@/lib/api";
import type { DocumentItem, IssueItem } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    curateIssue: vi.fn(),
    listDocumentIssues: vi.fn(),
    getReportPreview: vi.fn(),
    getExportUrl: (docId: string, format: string) => `/api/v1/documents/${docId}/export?format=${format}`,
  };
});

vi.mock("./pdf-canvas-viewer", () => ({
  PdfCanvasViewer: () => <div data-testid="pdf-canvas-viewer-mock">PDF Canvas</div>,
}));

describe("SplitScreenViewer", () => {
  const mockDoc: DocumentItem = {
    id: "doc-test-123",
    filename: "hydraulic_spec_v2.pdf",
    media_type: "application/pdf",
    size_bytes: 54000,
    sha256: "a".repeat(64),
    status: "COMPLETED",
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
      message: "Row sum error in hydraulic test data",
      included_in_report: true,
      reviewer_note: null,
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
    vi.mocked(api.getReportPreview).mockResolvedValue({
      document_id: "doc-test-123",
      included_findings: 1,
      blockers: 1,
      counts_by_severity: { CRITICAL: 1 },
      summary_judgement: "Blockers require correction before reissue.",
    });
  });

  it("renders document title, header status, and findings", () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    expect(screen.getByRole("heading", { name: "hydraulic_spec_v2.pdf" })).toBeDefined();
    expect(screen.getByText("1 Included")).toBeDefined();
    expect(screen.getByText("1 Blockers")).toBeDefined();
    fireEvent.click(screen.getByRole("tab", { name: /standards audit/i }));
    expect(screen.getByText("Row sum error in hydraulic test data")).toBeDefined();
  });

  it("opens report preview modal when Report Preview button is clicked", async () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    const previewBtn = screen.getByRole("button", { name: /report preview/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText("Review Report Preview")).toBeDefined();
      expect(screen.getByText("Summary Judgement")).toBeDefined();
      expect(screen.getByText("Blockers require correction before reissue.")).toBeDefined();
    });
  });

  it("opens export modal when Export button is clicked", async () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    const exportBtn = screen.getByRole("button", { name: /^export$/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByText("Export Review Deliverables")).toBeDefined();
      expect(screen.getByTestId("export-docx-btn")).toBeDefined();
      expect(screen.getByTestId("export-pdf-btn")).toBeDefined();
    });
  });

  it("triggers curateIssue and updates finding inclusion state", async () => {
    vi.mocked(api.curateIssue).mockResolvedValue({
      ...mockIssues[0],
      included_in_report: false,
    });

    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    fireEvent.click(screen.getByRole("tab", { name: /standards audit/i }));
    const excludeBtn = screen.getByRole("button", { name: /exclude from report/i });
    fireEvent.click(excludeBtn);

    await waitFor(() => {
      expect(api.curateIssue).toHaveBeenCalledWith("iss-1", {
        included_in_report: false,
        reviewer_note: null,
      });
      expect(screen.getByText(/excluded from report/i)).toBeDefined();
    });
  });

  it("provides direct export links in the footer", () => {
    render(<SplitScreenViewer document={mockDoc} initialIssues={mockIssues} />);

    const docxLink = screen.getByRole("link", { name: /export docx/i });
    expect(docxLink.getAttribute("href")).toBe("/api/v1/documents/doc-test-123/export?format=docx");

    const pdfLink = screen.getByRole("link", { name: /export annotated pdf/i });
    expect(pdfLink.getAttribute("href")).toBe("/api/v1/documents/doc-test-123/export?format=pdf");
  });
});
