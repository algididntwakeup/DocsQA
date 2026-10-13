import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentIngestionFlow } from "./document-ingestion-flow";
import { LocaleProvider } from "@/components/layout/locale-provider";
import * as api from "@/lib/api";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listProjects: vi.fn(),
    uploadProjectDocument: vi.fn(),
    getDocument: vi.fn(),
    getDocumentStatus: vi.fn(),
    subscribeDocumentEvents: vi.fn(),
  };
});

const PROJECT = {
  id: "project-1",
  name: "Central Plant",
  project_number: "13726486.01",
  client_name: "PT Example",
  owner_id: "user-1",
  created_at: "2026-09-10T00:00:00Z",
} as api.ProjectItem;

const COMPLETED_STATUS = {
  id: "doc-1",
  status: "COMPLETED",
  progress_pct: 100,
  current_stage: "Analysis complete",
  error_message: null,
  stages: [],
  updated_at: "2026-09-10T00:00:00Z",
} as api.DocumentStatus;

function pdf(name = "inspection.pdf") {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}

function renderFlow() {
  return render(
    <LocaleProvider>
      <DocumentIngestionFlow />
    </LocaleProvider>,
  );
}

/** Advance from the file step to the project step with one queued file. */
async function selectFileAndContinue() {
  const input = document.querySelector("input[type=file]") as HTMLInputElement;
  fireEvent.change(input, { target: { files: [pdf()] } });
  fireEvent.click(screen.getByRole("button", { name: /continue/i }));
  await screen.findByText(/choose a destination project/i);
}

describe("DocumentIngestionFlow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listProjects).mockResolvedValue([PROJECT]);
    vi.mocked(api.getDocument).mockResolvedValue({
      id: "doc-1",
      filename: "inspection.pdf",
      media_type: "application/pdf",
      size_bytes: 8,
      sha256: "a".repeat(64),
      status: "COMPLETED",
      progress_pct: 100,
      created_at: "2026-09-10T00:00:00Z",
      updated_at: "2026-09-10T00:00:00Z",
    } as api.DocumentItem);
    vi.mocked(api.getDocumentStatus).mockResolvedValue(COMPLETED_STATUS);
    vi.mocked(api.subscribeDocumentEvents).mockReturnValue(() => undefined);
  });

  it("starts on the file step and gates Continue on a selected file", () => {
    renderFlow();

    const continueButton = screen.getByRole("button", { name: /continue/i }) as HTMLButtonElement;
    expect(continueButton.disabled).toBe(true);
    expect(screen.getByText(/select source documents/i)).toBeDefined();
  });

  it("advances to the project step and lists the workspace projects", async () => {
    renderFlow();
    await selectFileAndContinue();

    expect(await screen.findByText("Central Plant")).toBeDefined();
    // Begin Inspection stays disabled until a project is chosen.
    const begin = screen.getByRole("button", { name: /begin inspection/i }) as HTMLButtonElement;
    expect(begin.disabled).toBe(true);
  });

  it("uploads into the selected project and morphs to processing without navigating", async () => {
    vi.mocked(api.uploadProjectDocument).mockResolvedValue({
      id: "doc-1",
      filename: "inspection.pdf",
      deduplicated: false,
    } as api.DocumentUpload);

    renderFlow();
    await selectFileAndContinue();

    fireEvent.click(await screen.findByText("Central Plant"));
    fireEvent.click(screen.getByRole("button", { name: /begin inspection/i }));

    await waitFor(() =>
      expect(api.uploadProjectDocument).toHaveBeenCalledWith("project-1", expect.any(File)),
    );

    // The status view appears in place: no route change was issued.
    expect(await screen.findByText(/step 03 · pipeline telemetry/i)).toBeDefined();
    expect(push).not.toHaveBeenCalled();
    // The destination project is surfaced in the processing header.
    expect(screen.getByText(/filed under central plant/i)).toBeDefined();
  });

  it("offers Open Review Workspace once the pipeline completes", async () => {
    vi.mocked(api.uploadProjectDocument).mockResolvedValue({
      id: "doc-1",
      filename: "inspection.pdf",
      deduplicated: false,
    } as api.DocumentUpload);

    renderFlow();
    await selectFileAndContinue();
    fireEvent.click(await screen.findByText("Central Plant"));
    fireEvent.click(screen.getByRole("button", { name: /begin inspection/i }));

    const openReview = await screen.findByRole("link", { name: /open review workspace/i });
    expect(openReview.getAttribute("href")).toBe("/documents/doc-1/review");
  });

  it("surfaces an upload failure on the project step", async () => {
    vi.mocked(api.uploadProjectDocument).mockRejectedValue(
      new api.ApiError("Only engineering roles may upload here.", 403),
    );

    renderFlow();
    await selectFileAndContinue();
    fireEvent.click(await screen.findByText("Central Plant"));
    fireEvent.click(screen.getByRole("button", { name: /begin inspection/i }));

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByText("Only engineering roles may upload here.")).toBeDefined();
  });
});
