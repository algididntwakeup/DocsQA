import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DocumentList } from "./document-list";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    deleteDocument: vi.fn(),
  };
});

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
    render(<DocumentList documents={[]} onRefresh={vi.fn()} />);
    expect(screen.getByText("No documents yet")).toBeDefined();
  });

  it("renders documents and allows deletion with confirmation", async () => {
    const onRefresh = vi.fn();
    vi.mocked(api.deleteDocument).mockResolvedValueOnce();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DocumentList documents={mockDocuments} onRefresh={onRefresh} />);

    expect(screen.getByText("test-document.pdf")).toBeDefined();

    const deleteBtn = screen.getByLabelText("Delete test-document.pdf");
    expect(deleteBtn).toBeDefined();

    fireEvent.click(deleteBtn);

    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(api.deleteDocument).toHaveBeenCalledWith("doc-123");
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it("does not delete if confirmation is rejected", async () => {
    const onRefresh = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<DocumentList documents={mockDocuments} onRefresh={onRefresh} />);

    const deleteBtn = screen.getByLabelText("Delete test-document.pdf");
    fireEvent.click(deleteBtn);

    expect(window.confirm).toHaveBeenCalled();
    expect(api.deleteDocument).not.toHaveBeenCalled();
    expect(onRefresh).not.toHaveBeenCalled();
  });
});
