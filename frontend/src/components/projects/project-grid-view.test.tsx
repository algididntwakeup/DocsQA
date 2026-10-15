import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { ProjectGridView } from "./project-grid-view";
import type { Project } from "@/types/project";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const baseProject: Project = {
  id: "project-1",
  name: "Plant Upgrade",
  code: null,
  project_number: "13726486.01",
  client_name: "PT. Spektra Megah Semesta",
  owner_id: "user-1",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-02T00:00:00Z",
  total_documents: 3,
};

function renderGrid(project: Project) {
  window.localStorage.setItem("matqc-locale", "en");
  render(
    <LocaleProvider>
      <ProjectGridView projects={[project]} />
    </LocaleProvider>,
  );
}

describe("ProjectGridView metadata", () => {
  it("renders the BIMA project number and client name", () => {
    renderGrid(baseProject);

    expect(screen.getByText("13726486.01")).toBeDefined();
    expect(screen.getByText("PT. Spektra Megah Semesta")).toBeDefined();
    expect(screen.queryByText("Number not available")).toBeNull();
    expect(screen.queryByText("Client not available")).toBeNull();
  });

  it("falls back only when the metadata is null", () => {
    renderGrid({ ...baseProject, project_number: null, client_name: null });

    expect(screen.getByText("Number not available")).toBeDefined();
    expect(screen.getByText("Client not available")).toBeDefined();
  });

  it("marks an imported project as BIMA", () => {
    renderGrid({ ...baseProject, bima_project_id: 4242 });

    expect(screen.getByText("BIMA")).toBeDefined();
    expect(screen.queryByText("Custom")).toBeNull();
  });

  it("marks a project without a BIMA id as Custom", () => {
    renderGrid({ ...baseProject, bima_project_id: null });

    expect(screen.getByText("Custom")).toBeDefined();
    expect(screen.queryByText("BIMA")).toBeNull();
  });
});
