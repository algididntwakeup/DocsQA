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

  it("renders all 4 export format cards with correct download links when isOpen is true", () => {
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
    expect(screen.getByText("Export Findings & Audit Package")).toBeDefined();

    // Verify format cards
    const pdfCard = screen.getByTestId("export-pdf-btn");
    expect(pdfCard.getAttribute("href")).toContain("/documents/test-doc-999/export?format=pdf");

    const xlsxCard = screen.getByTestId("export-xlsx-btn");
    expect(xlsxCard.getAttribute("href")).toContain("/documents/test-doc-999/export?format=xlsx");

    const csvCard = screen.getByTestId("export-csv-btn");
    expect(csvCard.getAttribute("href")).toContain("/documents/test-doc-999/export?format=csv");

    const jsonCard = screen.getByTestId("export-json-btn");
    expect(jsonCard.getAttribute("href")).toContain("/documents/test-doc-999/export?format=json");
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
