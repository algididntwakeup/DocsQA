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

function mockQueries(projects: unknown[], mutateAsync = vi.fn().mockResolvedValue(undefined)) {
  vi.mocked(hooks.useBimaProjects).mockReturnValue({
    data: projects,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  } as never);
  vi.mocked(hooks.useImportBimaProject).mockReturnValue({
    mutateAsync,
    isPending: false,
    variables: undefined,
  } as never);
}

function renderWithLocale(locale: "en" | "id", role: "ENGINEER" | "HRGA" | "FINANCE" = "ENGINEER") {
  window.localStorage.setItem("matqc-locale", locale);
  render(
    <LocaleProvider>
      <ImportBimaModal role={role} />
    </LocaleProvider>,
  );
}

async function renderAndOpen(locale: "en" | "id", role: "ENGINEER" | "HRGA" | "FINANCE" = "ENGINEER") {
  renderWithLocale(locale, role);
  const trigger = locale === "id" ? /Tambah dari BIMA/i : /Add from BIMA/i;
  fireEvent.click(screen.getByRole("button", { name: trigger }));
}

describe("ImportBimaModal", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows a passive in-folder badge for projects already added", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("en");
    await screen.findByText(importedProject.name);

    expect(screen.getByText("Already in Folder")).toBeDefined();
    // Adding is the only action the modal offers; opening lives on /projects.
    expect(screen.queryByRole("button", { name: /Open Workspace/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Add to Folder/i })).toBeNull();
  });

  it("sends the whole catalog row when adding to the folder", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockQueries([freshProject], mutateAsync);
    await renderAndOpen("en");
    await screen.findByText(freshProject.name);

    fireEvent.click(screen.getByRole("button", { name: /Add to Folder/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        bima_project_id: freshProject.id,
        project_number: freshProject.number,
        name: freshProject.name,
        client_name: freshProject.client_name,
      });
    });
  });

  it("keeps the dialog open and stays on the page after adding", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockQueries([freshProject], mutateAsync);
    await renderAndOpen("en");
    await screen.findByText(freshProject.name);

    fireEvent.click(screen.getByRole("button", { name: /Add to Folder/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    // No redirect into the workspace: the user keeps adding from the modal.
    expect(push).not.toHaveBeenCalled();
    expect((document.querySelector("dialog") as HTMLDialogElement).open).toBe(true);
  });

  it("blocks adding engineering projects for internal roles with a tooltip", async () => {
    mockQueries([freshProject]);
    await renderAndOpen("en", "HRGA");
    await screen.findByText(freshProject.name);

    const button = screen.getByRole("button", { name: /Add to Folder/i }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("13");
  });

  it("blocks adding internal projects for engineering roles with a tooltip", async () => {
    mockQueries([internalProject]);
    await renderAndOpen("en");
    await screen.findByText(internalProject.name);

    const button = screen.getByRole("button", { name: /Add to Folder/i }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("03");
  });

  it("renders every modal string in English when the locale is en", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("en");

    expect(screen.getByText("BIMA Integration")).toBeDefined();
    expect(screen.getByText("Choose a project to import")).toBeDefined();
    expect(screen.getByText("Search by project number, title, or client name.")).toBeDefined();
    expect(screen.getByPlaceholderText("Search project number, name, or client...")).toBeDefined();
    expect(screen.getByRole("button", { name: "Close dialog" })).toBeDefined();
    expect(screen.getByText("Already in Folder")).toBeDefined();
    expect(screen.queryByText("Integrasi BIMA")).toBeNull();
  });

  it("renders every modal string in Indonesian when the locale is id", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("id");

    expect(screen.getByText("Integrasi BIMA")).toBeDefined();
    expect(screen.getByText("Pilih proyek untuk diimpor")).toBeDefined();
    expect(screen.getByText("Cari berdasarkan nomor proyek, judul, atau nama klien.")).toBeDefined();
    expect(screen.getByPlaceholderText("Cari nomor proyek, judul, atau nama klien...")).toBeDefined();
    expect(screen.getByRole("button", { name: "Tutup dialog" })).toBeDefined();
    expect(screen.getByText("Sudah di Folder")).toBeDefined();
    expect(screen.queryByText("Choose a project to import")).toBeNull();
  });

  it("localizes the add action and its folder tooltip in Indonesian", async () => {
    mockQueries([freshProject]);
    await renderAndOpen("id", "HRGA");
    await screen.findByText(freshProject.name);

    const button = screen.getByRole("button", { name: /Tambah ke Folder/i }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("13");
    expect(button.title).toContain("Hanya engineer");
  });

  it("localizes the empty state in Indonesian", async () => {
    mockQueries([]);
    await renderAndOpen("id");

    expect(screen.getByText("Tidak ada proyek yang cocok.")).toBeDefined();
    expect(screen.getByText("Coba kata kunci lain atau hapus pencarian.")).toBeDefined();
  });

  it("localizes the load-failure state in Indonesian", async () => {
    vi.mocked(hooks.useBimaProjects).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("boom"),
      refetch: vi.fn(),
    } as never);
    vi.mocked(hooks.useImportBimaProject).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      variables: undefined,
    } as never);
    await renderAndOpen("id");

    expect(screen.getByText("Katalog proyek BIMA tidak dapat dimuat.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Coba lagi" })).toBeDefined();
  });
});
