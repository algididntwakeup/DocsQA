import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { ProjectActionsMenu } from "./project-actions-menu";
import type { Project } from "@/types/project";

const baseProject: Project = {
  id: "project-1",
  name: "Plant Upgrade",
  code: null,
  project_number: "13726486.01",
  client_name: "PT. Spektra Megah Semesta",
  owner_id: "user-1",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-02T00:00:00Z",
  total_documents: 0,
};

function openMenu(project: Project, onDelete = vi.fn()) {
  window.localStorage.setItem("matqc-locale", "en");
  render(
    <LocaleProvider>
      <ProjectActionsMenu project={project} canManage onDelete={onDelete} />
    </LocaleProvider>,
  );
  fireEvent.click(screen.getByLabelText(/actions for/i));
  return onDelete;
}

describe("ProjectActionsMenu deletion rules", () => {
  it("offers deletion for a custom project", () => {
    const onDelete = openMenu({ ...baseProject, bima_project_id: null });

    const button = screen.getByRole("button", { name: /delete project/i });
    fireEvent.click(button);

    expect(onDelete).toHaveBeenCalledWith("project-1");
  });

  it("hides deletion for a BIMA imported project", () => {
    const onDelete = openMenu({ ...baseProject, bima_project_id: 4242 });

    expect(screen.queryByRole("button", { name: /delete project/i })).toBeNull();
    expect(screen.getByText(/BIMA projects cannot be deleted/i)).toBeDefined();
    expect(onDelete).not.toHaveBeenCalled();
  });
});
