import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { ImportBimaModal } from "./import-bima-modal";
import * as hooks from "@/hooks/use-bima-projects";

const push = vi.fn();

// jsdom does not implement the native <dialog> modal API.
if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.open = false;
  };
}

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/hooks/use-bima-projects", () => ({
  useBimaProjects: vi.fn(),
  useImportBimaProject: vi.fn(),
}));

const importedProject = {
  id: 627,
  number: "13726486.01",
  name: "Plant Upgrade",
  client_name: "Example Client",
  is_imported: true,
  prism_project_id: "prism-project-1",
};

const freshProject = {
  id: 628,
  number: "13726486.02",
  name: "Piping Review",
  client_name: "Example Client",
  is_imported: false,
  prism_project_id: null,
};

const internalProject = {
  id: 700,
  number: "03-2026-001",
  name: "GA Budget",
  client_name: "Internal",
  is_imported: false,
  prism_project_id: null,
};

function mockQueries(projects: unknown[]) {
  vi.mocked(hooks.useBimaProjects).mockReturnValue({
    data: projects,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  } as never);
  vi.mocked(hooks.useImportBimaProject).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
  } as never);
}

async function renderAndOpen(role: "ENGINEER" | "HRGA" | "FINANCE") {
  window.localStorage.setItem("matqc-locale", "id");
  render(
    <LocaleProvider>
      <ImportBimaModal role={role} />
    </LocaleProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /Tambah dari BIMA/i }));
}

describe("ImportBimaModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an active Open Project action for imported items", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("ENGINEER");
    await screen.findByText(importedProject.name);

    const openButton = screen.getByRole("button", { name: /Buka Proyek/i }) as HTMLButtonElement;
    expect(openButton.disabled).toBe(false);
    // The passive badge stays as a subtle indicator.
    expect(screen.getByText("Sudah Ada")).toBeDefined();
  });

  it("navigates to the workspace and closes the modal on click", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("ENGINEER");
    await screen.findByText(importedProject.name);

    fireEvent.click(screen.getByRole("button", { name: /Buka Proyek/i }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/workspace/prism-project-1");
    });
  });

  it("disables Open Project when the imported item lacks a workspace id", async () => {
    mockQueries([{ ...importedProject, prism_project_id: null }]);
    await renderAndOpen("ENGINEER");
    await screen.findByText(importedProject.name);

    const openButton = screen.getByRole("button", { name: /Buka Proyek/i }) as HTMLButtonElement;
    expect(openButton.disabled).toBe(true);
    fireEvent.click(openButton);
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps the import action for items that are not imported yet", async () => {
    mockQueries([freshProject]);
    await renderAndOpen("ENGINEER");
    await screen.findByText(freshProject.name);

    expect(screen.getByRole("button", { name: /^Impor$/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /Buka Proyek/i })).toBeNull();
  });

  it("blocks importing engineering projects for internal roles with a tooltip", async () => {
    mockQueries([freshProject]);
    await renderAndOpen("HRGA");
    await screen.findByText(freshProject.name);

    const importButton = screen.getByRole("button", { name: /^Impor$/i }) as HTMLButtonElement;
    expect(importButton.disabled).toBe(true);
    expect(importButton.title).toContain("13");
  });

  it("blocks importing internal projects for engineering roles with a tooltip", async () => {
    mockQueries([internalProject]);
    await renderAndOpen("ENGINEER");
    await screen.findByText(internalProject.name);

    const importButton = screen.getByRole("button", { name: /^Impor$/i }) as HTMLButtonElement;
    expect(importButton.disabled).toBe(true);
    expect(importButton.title).toContain("03");
  });
});
