import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExportModal } from "./export-modal";

describe("ExportModal", () => {
  const docId = "test-doc-999";
  const docFilename = "engineering_manual.pdf";

  it("does not render when isOpen is false", () => {
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={false}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders both export format actions when isOpen is true", () => {
    const handleClose = vi.fn();
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={handleClose}
      />
    );

    expect(screen.getByRole("dialog")).toBeDefined();
    expect(screen.getByText("Export Review Deliverables")).toBeDefined();

    // Verify format cards
    const docxCard = screen.getByTestId("export-docx-btn");
    expect(docxCard.tagName).toBe("BUTTON");

    const pdfCard = screen.getByTestId("export-pdf-btn");
    expect(pdfCard.tagName).toBe("BUTTON");

    // Legacy formats should not exist
    expect(screen.queryByTestId("export-xlsx-btn")).toBeNull();
    expect(screen.queryByTestId("export-csv-btn")).toBeNull();
    expect(screen.queryByTestId("export-json-btn")).toBeNull();
  });

  it("calls onClose when Close button is clicked", () => {
    const handleClose = vi.fn();
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={handleClose}
      />
    );

    const closeBtn = screen.getByRole("button", { name: /close export modal/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape key is pressed", () => {
    const handleClose = vi.fn();
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={handleClose}
      />
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
