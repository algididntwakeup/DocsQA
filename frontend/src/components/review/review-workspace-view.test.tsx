import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewWorkspaceView } from "./review-workspace-view";
import * as api from "@/lib/api";
import type { DocumentItem } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a>,
}));
vi.mock("./split-screen-viewer", () => ({ SplitScreenViewer: () => <div>viewer</div> }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getDocument: vi.fn(),
    listAllDocumentIssues: vi.fn().mockResolvedValue([]),
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

describe("ReviewWorkspaceView workflow actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
