import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { ExplorerToolbar } from "./explorer-toolbar";
import { ImportBimaModal } from "./import-bima-modal";

vi.mock("@/hooks/use-bima-projects", () => ({
  useBimaProjects: () => ({ data: [], isPending: false, isError: false, refetch: vi.fn() }),
  useImportBimaProject: () => ({ isPending: false, mutateAsync: vi.fn(), variables: undefined }),
}));

function renderWithLocale(ui: ReactElement, locale: "en" | "id") {
  window.localStorage.setItem("matqc-locale", locale);
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

const toolbarProps = {
  search: "",
  onSearchChange: vi.fn(),
  sortBy: "updated_at" as const,
  onSortByChange: vi.fn(),
  sortDirection: "desc" as const,
  onToggleSortDirection: vi.fn(),
  viewMode: "grid" as const,
  onViewModeChange: vi.fn(),
};

describe("ExplorerToolbar localization", () => {
  beforeEach(() => window.localStorage.clear());

  it("renders English copy when locale is en", () => {
    renderWithLocale(<ExplorerToolbar {...toolbarProps} />, "en");

    expect(screen.getByPlaceholderText("Search projects by name, number, or client...")).toBeDefined();
    expect(screen.getByRole("button", { name: "Grid View" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Table View" })).toBeDefined();
    expect(screen.getByLabelText("Sort by:")).toBeDefined();
    expect(screen.getByRole("option", { name: "Project Name" })).toBeDefined();
    expect(screen.getByRole("option", { name: "Last Modified" })).toBeDefined();
    expect(screen.queryByText(/Tampilan|Urutkan/)).toBeNull();
  });

  it("renders Indonesian copy when locale is id", () => {
    renderWithLocale(<ExplorerToolbar {...toolbarProps} />, "id");

    expect(screen.getByPlaceholderText("Cari proyek berdasarkan nama, nomor, atau klien...")).toBeDefined();
    expect(screen.getByRole("button", { name: "Tampilan Grid" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Tampilan Tabel" })).toBeDefined();
    expect(screen.getByRole("option", { name: "Nama Proyek" })).toBeDefined();
    expect(screen.getByRole("option", { name: "Terakhir Diperbarui" })).toBeDefined();
  });
});

describe("ImportBimaModal localization", () => {
  beforeEach(() => window.localStorage.clear());

  it("renders English copy when locale is en", () => {
    renderWithLocale(<ImportBimaModal />, "en");

    expect(screen.getByRole("button", { name: /Import from BIMA/ })).toBeDefined();
    expect(screen.queryByText("Tambah dari BIMA")).toBeNull();
  });

  it("renders Indonesian copy when locale is id", () => {
    renderWithLocale(<ImportBimaModal />, "id");

    expect(screen.getByRole("button", { name: /Tambah dari BIMA/ })).toBeDefined();
    expect(screen.queryByText("Import from BIMA")).toBeNull();
  });
});
