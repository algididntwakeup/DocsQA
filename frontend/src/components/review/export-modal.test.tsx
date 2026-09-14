import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ExportModal } from "./export-modal";
import * as downloadModule from "@/lib/download";

vi.mock("@/lib/download", () => ({
  downloadExport: vi.fn(),
}));

describe("ExportModal", () => {
  const docId = "test-doc-999";
  const docFilename = "engineering_manual.pdf";

  beforeEach(() => {
    vi.clearAllMocks();
  });

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

    const annotatedCard = screen.getByTestId("export-annotated-pdf-btn");
    expect(annotatedCard.tagName).toBe("BUTTON");

    // Legacy formats should not exist
    expect(screen.queryByTestId("export-xlsx-btn")).toBeNull();
    expect(screen.queryByTestId("export-csv-btn")).toBeNull();
    expect(screen.queryByTestId("export-json-btn")).toBeNull();
  });

  it("calls downloadExport with pdf format and default language", () => {
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const pdfBtn = screen.getByTestId("export-pdf-btn");
    fireEvent.click(pdfBtn);

    expect(downloadModule.downloadExport).toHaveBeenCalledWith(
      docId,
      "pdf",
      false,
      "en"
    );
  });

  it("calls downloadExport with id language when Bahasa Indonesia is selected", () => {
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const idRadio = screen.getByLabelText("Bahasa Indonesia");
    fireEvent.click(idRadio);

    const docxBtn = screen.getByTestId("export-docx-btn");
    fireEvent.click(docxBtn);

    expect(downloadModule.downloadExport).toHaveBeenCalledWith(
      docId,
      "docx",
      false,
      "id"
    );
  });

  it("passes includeMinors=true when checkbox is toggled", () => {
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    const pdfBtn = screen.getByTestId("export-pdf-btn");
    fireEvent.click(pdfBtn);

    expect(downloadModule.downloadExport).toHaveBeenCalledWith(
      docId,
      "pdf",
      true,
      "en"
    );
  });

  it("calls downloadExport with annotated_pdf when overlay card is clicked", () => {
    render(
      <ExportModal
        documentId={docId}
        documentFilename={docFilename}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const annotatedBtn = screen.getByTestId("export-annotated-pdf-btn");
    fireEvent.click(annotatedBtn);

    expect(downloadModule.downloadExport).toHaveBeenCalledWith(
      docId,
      "annotated_pdf",
      false
    );
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
