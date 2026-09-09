import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ReportPreviewModal } from "./report-preview-modal";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getReportPreview: vi.fn(),
    getExportUrl: (docId: string, format: string) => `/api/v1/documents/${docId}/export?format=${format}`,
  };
});

describe("ReportPreviewModal", () => {
  const docId = "doc-test-123";
  const docFilename = "pump_spec_v1.pdf";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    render(
      <ReportPreviewModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={false}
        onClose={vi.fn()}
      />
    );

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("loads and displays report preview data", async () => {
    vi.mocked(api.getReportPreview).mockResolvedValue({
      document_id: docId,
      included_findings: 5,
      blockers: 2,
      counts_by_severity: {
        CRITICAL: 1,
        HIGH: 1,
        MEDIUM: 2,
        LOW: 1,
      },
      summary_judgement: "Blockers require correction before reissue.",
    });

    render(
      <ReportPreviewModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByRole("dialog")).toBeDefined();
    expect(screen.getByText(/calculating report composition/i)).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Review Report Preview")).toBeDefined();
      expect(screen.getByText("Blockers require correction before reissue.")).toBeDefined();
      expect(screen.getByText("5")).toBeDefined(); // Included findings
      expect(screen.getByText("2")).toBeDefined(); // Blockers
      expect(screen.getByText("Limits of this review")).toBeDefined();
    });

    // Export actions are buttons so they can show asynchronous toast feedback.
    expect(screen.getByRole("button", { name: /download docx report/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /download annotated pdf/i })).toBeDefined();
  });

  it("handles preview error gracefully", async () => {
    vi.mocked(api.getReportPreview).mockRejectedValue(new Error("Document not processed"));

    render(
      <ReportPreviewModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeDefined();
      expect(screen.getByText("Document not processed")).toBeDefined();
    });
  });

  it("calls onClose when close button is clicked", async () => {
    const handleClose = vi.fn();
    vi.mocked(api.getReportPreview).mockResolvedValue({
      document_id: docId,
      included_findings: 0,
      blockers: 0,
      counts_by_severity: {},
      summary_judgement: "No blocker findings are included in the draft report.",
    });

    render(
      <ReportPreviewModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={handleClose}
      />
    );

    const closeBtn = screen.getByRole("button", { name: /close report preview/i });
    fireEvent.click(closeBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
