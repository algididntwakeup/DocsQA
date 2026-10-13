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
  is_mine: true,
  bima_owner_known: true,
};

const freshProject = {
  id: 628,
  number: "13726486.02",
  name: "Piping Review",
  client_name: "Example Client",
  is_imported: false,
  prism_project_id: null,
  // The caller's own project: standard users only ever see their own catalog.
  is_mine: true,
  bima_owner_known: true,
};

/** An engineering project owned by someone else, used to prove scoping. */
const foreignProject = {
  id: 629,
  number: "13726486.03",
  name: "Foreign Facility",
  client_name: "Other Client",
  is_imported: false,
  prism_project_id: null,
  is_mine: false,
  bima_owner_known: true,
};

const internalProject = {
  id: 700,
  number: "03-2026-001",
  name: "GA Budget",
  client_name: "Internal",
  is_imported: false,
  prism_project_id: null,
  is_mine: true,
  bima_owner_known: true,
};

/** An engineering project owned by the caller, used for the folder-RBAC cases. */
const engineeringProject = {
  id: 701,
  number: "13726486.09",
  name: "Engineering Scoped",
  client_name: "Example Client",
  is_imported: false,
  prism_project_id: null,
  is_mine: true,
  bima_owner_known: true,
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

function renderWithLocale(
  locale: "en" | "id",
  role: "ENGINEER" | "HRGA" | "FINANCE" = "ENGINEER",
  isSuperuser = false,
) {
  window.localStorage.setItem("matqc-locale", locale);
  render(
    <LocaleProvider>
      <ImportBimaModal role={role} isSuperuser={isSuperuser} />
    </LocaleProvider>,
  );
}

async function renderAndOpen(
  locale: "en" | "id",
  role: "ENGINEER" | "HRGA" | "FINANCE" = "ENGINEER",
  isSuperuser = false,
) {
  renderWithLocale(locale, role, isSuperuser);
  // The UI is pinned to English, so the trigger label is always English.
  fireEvent.click(screen.getByRole("button", { name: /Add from BIMA/i }));
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

  it("stays English even when the stored locale is id", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("id");

    expect(screen.getByText("BIMA Integration")).toBeDefined();
    expect(screen.getByText("Choose a project to import")).toBeDefined();
    expect(screen.getByText("Search by project number, title, or client name.")).toBeDefined();
    expect(screen.getByPlaceholderText("Search project number, name, or client...")).toBeDefined();
    expect(screen.getByRole("button", { name: "Close dialog" })).toBeDefined();
    expect(screen.getByText("Already in Folder")).toBeDefined();
    expect(screen.queryByText("Integrasi BIMA")).toBeNull();
  });

  it("keeps the folder tooltip in English for a blocked role", async () => {
    mockQueries([engineeringProject]);
    await renderAndOpen("id", "HRGA");
    await screen.findByText(engineeringProject.name);

    const button = screen.getByRole("button", { name: /Add to Folder/i }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("13");
    expect(button.title).toContain("Only engineers");
  });

  it("keeps the empty state in English", async () => {
    mockQueries([]);
    await renderAndOpen("id");

    expect(screen.getByText("No matching projects.")).toBeDefined();
    expect(screen.getByText("Try another keyword or clear the search.")).toBeDefined();
  });

  it("keeps the load-failure state in English", async () => {
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

    expect(screen.getByText("Could not load the BIMA project catalog.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Retry" })).toBeDefined();
  });

  it("marks the caller's own BIMA projects without offering a navigation action", async () => {
    mockQueries([importedProject]);
    await renderAndOpen("en");
    await screen.findByText(importedProject.name);

    // The ownership marker stays, but adding to the folder is the modal's only
    // action: opening a workspace happens on /projects.
    expect(screen.getByText("My Project")).toBeDefined();
    expect(screen.getByText("Already in Folder")).toBeDefined();
    expect(screen.queryByRole("button", { name: /Open Workspace/i })).toBeNull();
  });

  it("shows only the caller's own projects for a standard user", async () => {
    mockQueries([importedProject, foreignProject]);
    await renderAndOpen("en");

    // No scope tabs at all: the list is pinned to "mine".
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.queryByRole("tab", { name: "All Projects" })).toBeNull();
    expect(screen.getByText(importedProject.name)).toBeDefined();
    expect(screen.queryByText(foreignProject.name)).toBeNull();
  });

  it("offers both scope tabs to a superuser", async () => {
    mockQueries([importedProject, foreignProject]);
    await renderAndOpen("en", "ENGINEER", true);

    const tabs = screen.getByRole("tablist");
    expect(tabs).toBeDefined();
    expect(screen.getByRole("tab", { name: "My Projects" })).toBeDefined();
    expect(screen.getByRole("tab", { name: "All Projects" })).toBeDefined();

    // "My Projects" is the default scope, so the foreign project is hidden.
    expect(screen.getByText(importedProject.name)).toBeDefined();
    expect(screen.queryByText(foreignProject.name)).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "All Projects" }));

    expect(screen.getByText(importedProject.name)).toBeDefined();
    expect(screen.getByText(foreignProject.name)).toBeDefined();
  });
});
