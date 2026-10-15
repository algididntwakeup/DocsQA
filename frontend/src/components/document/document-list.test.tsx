import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DocumentList } from "./document-list";
import { LocaleProvider } from "@/components/layout/locale-provider";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    deleteDocument: vi.fn(),
  };
});

// jsdom does not implement the native <dialog> modal API.
if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.open = false;
  };
}

function renderList(documents: api.DocumentItem[], onRefresh = vi.fn()) {
  return render(
    <LocaleProvider>
      <DocumentList documents={documents} onRefresh={onRefresh} />
    </LocaleProvider>,
  );
}

describe("DocumentList", () => {
  const mockDocuments: api.DocumentItem[] = [
    {
      id: "doc-123",
      filename: "test-document.pdf",
      media_type: "application/pdf",
      size_bytes: 2048,
      sha256: "testsha256hash",
      status: "COMPLETED",
      progress_pct: 100,
      page_count: 5,
      created_at: "2026-09-06T00:00:00Z",
      updated_at: "2026-09-06T00:05:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no documents exist", () => {
    renderList([]);
    expect(screen.getByText("No documents yet")).toBeDefined();
  });

  it("shows the Reviewed By column instead of the obsolete Assigned PIC", () => {
    renderList([
      { ...mockDocuments[0], reviewed_by_name: "Engineer One" },
    ]);

    expect(screen.getByText("Reviewed By")).toBeDefined();
    expect(screen.queryByText("Assigned PIC")).toBeNull();
    expect(screen.getByText("Engineer One")).toBeDefined();
  });

  it("shows Pending in the Reviewed By column when nobody has reviewed", () => {
    renderList(mockDocuments);

    expect(screen.getByText("Pending")).toBeDefined();
  });

  it("opens a confirmation dialog instead of a native confirm", async () => {
    const onRefresh = vi.fn();
    vi.mocked(api.deleteDocument).mockResolvedValueOnce(undefined);
    const confirmSpy = vi.spyOn(window, "confirm");

    renderList(mockDocuments, onRefresh);

    fireEvent.click(screen.getByLabelText("Delete test-document.pdf"));

    // The dialog is rendered, and no native confirm was used.
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeDefined();
    expect(screen.getByText("Delete Document")).toBeDefined();
    expect(confirmSpy).not.toHaveBeenCalled();
    // Nothing is deleted until the user confirms.
    expect(api.deleteDocument).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Yes, Delete Document" }));

    await waitFor(() => {
      expect(api.deleteDocument).toHaveBeenCalledWith("doc-123");
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it("does not delete when the confirmation is cancelled", async () => {
    const onRefresh = vi.fn();

    renderList(mockDocuments, onRefresh);

    fireEvent.click(screen.getByLabelText("Delete test-document.pdf"));
    await screen.findByRole("dialog");

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(api.deleteDocument).not.toHaveBeenCalled();
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("surfaces a failure inside the dialog without refreshing", async () => {
    const onRefresh = vi.fn();
    vi.mocked(api.deleteDocument).mockRejectedValueOnce(new Error("Document not found."));

    renderList(mockDocuments, onRefresh);

    fireEvent.click(screen.getByLabelText("Delete test-document.pdf"));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Yes, Delete Document" }));

    expect(await screen.findByText("Document not found.")).toBeDefined();
    expect(onRefresh).not.toHaveBeenCalled();
  });
});
