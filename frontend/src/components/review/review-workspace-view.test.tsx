import { act, render, screen, waitFor, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewWorkspaceView } from "./review-workspace-view";
import * as api from "@/lib/api";
import type { DocumentItem, DocumentProgressEvent, DocumentStatus } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a>,
}));
vi.mock("./split-screen-viewer", () => ({ SplitScreenViewer: () => <div>viewer</div> }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getDocument: vi.fn(),
    getDocumentStatus: vi.fn(),
    retryDocumentAnalysis: vi.fn(),
    listDocumentIssues: vi.fn().mockResolvedValue({ issues: [], pagination: { page: 1, page_size: 50, total: 0 }, counts_by_severity: {} }),
    getCurrentUser: vi.fn(),
    subscribeDocumentEvents: vi.fn().mockReturnValue(() => undefined),
  };
});

const document: DocumentItem = {
  id: "doc-1", filename: "review.pdf", media_type: "application/pdf", size_bytes: 1,
  sha256: "hash", status: "COMPLETED", progress_pct: 100,
  created_at: "2026-09-10T00:00:00Z", updated_at: "2026-09-10T00:00:00Z",
  workflow_status: "ANALYZING" as const,
};

const completedStatus: DocumentStatus = {
  id: "doc-1",
  status: "COMPLETED",
  progress_pct: 100,
  current_stage: "Analysis complete",
  error_message: null,
  stages: [],
  updated_at: "2026-09-10T00:00:00Z",
};
let progressCallback: ((event: DocumentProgressEvent) => void) | undefined;

describe("ReviewWorkspaceView workflow actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    progressCallback = undefined;
    vi.mocked(api.getDocumentStatus).mockResolvedValue(completedStatus);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...document, workflow_status: "REVIEWED_BY_ENGINEER" }) }));
  });

  it("shows Mark Reviewed for engineers and posts with cookie credentials", async () => {
    vi.mocked(api.getDocument).mockResolvedValue(document);
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "ENGINEER" } as never);
    render(<ReviewWorkspaceView id="doc-1" />);

    const button = await screen.findByRole("button", { name: /tandai selesai/i });
    fireEvent.click(button);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/mark-reviewed"), expect.objectContaining({ credentials: "include" })));
  });

  it("shows Verify for leads after engineer review", async () => {
    vi.mocked(api.getDocument).mockResolvedValue({ ...document, workflow_status: "REVIEWED_BY_ENGINEER" });
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "LEAD_ENGINEER" } as never);
    render(<ReviewWorkspaceView id="doc-1" />);

    expect(await screen.findByRole("button", { name: /verifikasi/i })).not.toBeNull();
    expect(screen.queryByRole("button", { name: /tandai selesai/i })).toBeNull();
  });

  it("keeps exports available but disables workflow actions for finished projects", async () => {
    vi.mocked(api.getDocument).mockResolvedValue({
      ...document,
      project_finished: true,
      workflow_status: "REVIEWED_BY_ENGINEER",
    });
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "LEAD_ENGINEER" } as never);
    render(<ReviewWorkspaceView id="doc-1" />);

    expect(await screen.findByText(/project finished/i)).not.toBeNull();
    expect(screen.queryByRole("button", { name: /verifikasi/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /minta revisi/i })).toBeNull();
    expect(screen.getByRole("button", { name: /export docx/i })).not.toBeNull();
  });

  it("shows live progress and disables export while analysis is running", async () => {
    const processingDocument = { ...document, status: "PROCESSING" as const, progress_pct: 30 };
    vi.mocked(api.getDocument).mockResolvedValue(processingDocument);
    vi.mocked(api.getDocumentStatus).mockResolvedValue({
      ...completedStatus,
      status: "PROCESSING",
      progress_pct: 42,
      current_stage: "Budinski checks",
    });
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "ENGINEER" } as never);
    render(<ReviewWorkspaceView id="doc-1" />);

    expect(await screen.findByText("Budinski checks")).not.toBeNull();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("42");
    const exportButton = screen.getByRole("button", { name: /export docx/i }) as HTMLButtonElement;
    expect(exportButton.disabled).toBe(true);
    expect(exportButton.getAttribute("title")).toBe("Fitur ekspor aktif setelah analisis selesai.");
  });

  it("shows the failure message and retries analysis", async () => {
    const failedDocument = { ...document, status: "FAILED" as const, progress_pct: 0 };
    vi.mocked(api.getDocument).mockResolvedValue(failedDocument);
    vi.mocked(api.getDocumentStatus).mockResolvedValue({
      ...completedStatus,
      status: "FAILED",
      progress_pct: 0,
      current_stage: "Text extraction",
      error_message: "Extraction timed out.",
    });
    vi.mocked(api.retryDocumentAnalysis).mockResolvedValue({
      ...failedDocument,
      status: "QUEUED",
    });
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "ENGINEER" } as never);
    render(<ReviewWorkspaceView id="doc-1" />);

    expect(await screen.findByText("Extraction timed out.")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /retry analysis/i }));
    await waitFor(() => expect(api.retryDocumentAnalysis).toHaveBeenCalledWith("doc-1"));
    expect(await screen.findByRole("progressbar")).not.toBeNull();
  });

  it("unlocks the workspace when SSE reports completion", async () => {
    const processingDocument = { ...document, status: "PROCESSING" as const, progress_pct: 30 };
    const processingStatus: DocumentStatus = {
      ...completedStatus,
      status: "PROCESSING",
      progress_pct: 42,
      current_stage: "Budinski checks",
    };
    vi.mocked(api.getDocument)
      .mockResolvedValueOnce(processingDocument)
      .mockResolvedValueOnce(document);
    vi.mocked(api.getDocumentStatus)
      .mockResolvedValueOnce(processingStatus)
      .mockResolvedValueOnce(completedStatus);
    vi.mocked(api.getCurrentUser).mockResolvedValue({ role: "ENGINEER" } as never);
    vi.mocked(api.subscribeDocumentEvents).mockImplementation((_id, onProgress) => {
      progressCallback = onProgress;
      return () => undefined;
    });
    vi.stubGlobal("EventSource", undefined);
    render(<ReviewWorkspaceView id="doc-1" />);

    expect(await screen.findByRole("progressbar")).not.toBeNull();
    await waitFor(() => expect(progressCallback).toBeDefined());
    await act(async () => {
      progressCallback?.({
        document_id: "doc-1",
        status: "COMPLETED",
        progress_pct: 100,
        stages: [],
      });
    });

    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
    expect((screen.getByRole("button", { name: /export docx/i }) as HTMLButtonElement).disabled).toBe(false);
    expect(api.getDocument).toHaveBeenCalledTimes(2);
  });
 });
