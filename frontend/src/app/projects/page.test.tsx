import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { ApiError } from "@/lib/api";
import type { Project } from "@/types/project";
import ProjectsPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const bimaProject: Project = {
  id: "bima-1",
  name: "BIMA Boiler Feedwater",
  code: null,
  project_number: "13726486.01",
  client_name: "PT. Spektra",
  bima_project_id: 4242,
  owner_id: "user-1",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-02T00:00:00Z",
  total_documents: 0,
};

const customProject: Project = {
  id: "custom-1",
  name: "Custom Turnaround",
  code: null,
  project_number: "03-2026-001",
  client_name: "Internal",
  bima_project_id: null,
  owner_id: "user-1",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-02T00:00:00Z",
  total_documents: 0,
};

const listProjects = vi.fn();
const deleteProject = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listProjects: (...args: unknown[]) => listProjects(...args),
    deleteProject: (...args: unknown[]) => deleteProject(...args),
    listProjectDocuments: vi.fn().mockResolvedValue({ documents: [], pagination: { page: 1, page_size: 20, total: 0 } }),
    getCurrentUser: vi.fn().mockResolvedValue({ role: "LEAD_ENGINEER", is_superuser: false }),
  };
});

vi.mock("@/hooks/use-bima-projects", () => ({
  useBimaProjects: () => ({ data: [], isPending: false, isError: false, refetch: vi.fn() }),
  useImportBimaProject: () => ({ isPending: false, mutateAsync: vi.fn(), variables: undefined }),
}));

function renderPage() {
  window.localStorage.setItem("matqc-locale", "en");
  return render(
    <LocaleProvider>
      <ProjectsPage />
    </LocaleProvider>,
  );
}

describe("ProjectsPage origin filter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listProjects.mockResolvedValue([bimaProject, customProject]);
  });

  it("shows both projects under the default All filter", async () => {
    renderPage();

    expect(await screen.findByText("BIMA Boiler Feedwater")).toBeDefined();
    expect(screen.getByText("Custom Turnaround")).toBeDefined();
  });

  it("narrows the grid to BIMA projects only", async () => {
    renderPage();
    await screen.findByText("BIMA Boiler Feedwater");

    fireEvent.change(screen.getByLabelText("Project origin"), { target: { value: "bima" } });

    expect(screen.getByText("BIMA Boiler Feedwater")).toBeDefined();
    expect(screen.queryByText("Custom Turnaround")).toBeNull();
  });

  it("narrows the grid to custom projects only", async () => {
    renderPage();
    await screen.findByText("Custom Turnaround");

    fireEvent.change(screen.getByLabelText("Project origin"), { target: { value: "custom" } });

    expect(screen.getByText("Custom Turnaround")).toBeDefined();
    expect(screen.queryByText("BIMA Boiler Feedwater")).toBeNull();
  });
});

describe("ProjectsPage deletion flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listProjects.mockResolvedValue([customProject]);
  });

  it("asks for confirmation before deleting a custom project", async () => {
    deleteProject.mockResolvedValue(undefined);
    renderPage();
    await screen.findByText("Custom Turnaround");

    fireEvent.click(screen.getByLabelText(/actions for custom turnaround/i));
    fireEvent.click(screen.getByRole("button", { name: /delete project/i }));

    // Nothing is deleted until the dialog is confirmed.
    expect(deleteProject).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /^delete project$/i }));

    await waitFor(() => expect(deleteProject).toHaveBeenCalledWith("custom-1"));
  });

  it("surfaces the API refusal when a BIMA project is deleted directly", async () => {
    listProjects.mockResolvedValue([customProject]);
    deleteProject.mockRejectedValue(
      new ApiError("BIMA imported projects cannot be deleted.", 403),
    );
    renderPage();
    await screen.findByText("Custom Turnaround");

    fireEvent.click(screen.getByLabelText(/actions for custom turnaround/i));
    fireEvent.click(screen.getByRole("button", { name: /delete project/i }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /^delete project$/i }));

    expect(await screen.findByText(/BIMA imported projects cannot be deleted/i)).toBeDefined();
  });
});
