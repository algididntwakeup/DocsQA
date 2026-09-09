import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScanProgress } from "@/components/document/scan-progress";
import Home from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listDocuments: vi.fn().mockResolvedValue({
      documents: [],
      pagination: { page: 1, page_size: 100, total: 0 },
    }),
  };
});

describe("Home", () => {
  it("renders the inspection workspace", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: /inspection workspace/i })).toBeDefined();
  });

  it("renders per-stage extraction progress", () => {
    render(<ScanProgress scan={{
      id: "c6a4507d-bbfd-4c71-b64a-5f42f7fd1cde",
      status: "PROCESSING",
      progress_pct: 42,
      updated_at: "2026-09-04T00:00:00Z",
       stages: [{ id: "17471ea1-5671-49bc-825a-8300f4c7bf10", name: "EXTRACTING", status: "RUNNING", progress_pct: 42, attempt: 1 }],
    }} />);
    expect(screen.getAllByText("42%").length).toBeGreaterThan(0);
     expect(screen.getByText("extracting")).toBeDefined();
  });
});
