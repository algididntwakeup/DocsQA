import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ProjectDocumentTable } from "./project-document-table";
import type { DocumentItem } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const documents: DocumentItem[] = [
  {
    id: "doc-a",
    filename: "engineer-a.pdf",
    media_type: "application/pdf",
    size_bytes: 100,
    sha256: "a",
    status: "COMPLETED",
    progress_pct: 100,
    created_at: "2026-09-10T00:00:00Z",
    updated_at: "2026-09-10T00:00:00Z",
    owner_id: "engineer-a",
    workflow_status: "REVIEWED_BY_ENGINEER",
  },
];

describe("ProjectDocumentTable", () => {
  it("shows lead-only filters and reports filter changes", () => {
    const onFiltersChange = vi.fn();
    render(<ProjectDocumentTable documents={documents} role="LEAD_ENGINEER" loading={false} onUpload={vi.fn()} onFiltersChange={onFiltersChange} />);

    expect(screen.getByLabelText("Engineer")).not.toBeNull();
    fireEvent.change(screen.getByLabelText("Blockers"), { target: { value: "yes" } });
    expect(onFiltersChange).toHaveBeenCalledWith({ sortBy: "date_desc", hasBlockers: true });
  });

  it("hides lead filters for engineers", () => {
    render(<ProjectDocumentTable documents={documents} role="ENGINEER" loading={false} onUpload={vi.fn()} onFiltersChange={vi.fn()} />);

    expect(screen.queryByLabelText("Engineer")).toBeNull();
    expect(screen.getByRole("link", { name: /buka workspace/i }).getAttribute("href")).toBe("/documents/doc-a/review");
  });
  it("disables workspace while a document is processing", () => {
    render(
      <ProjectDocumentTable
        documents={[{ ...documents[0], status: "PROCESSING", progress_pct: 42 }]}
        role="ENGINEER"
        loading={false}
        onUpload={vi.fn()}
        onFiltersChange={vi.fn()}
      />,
    );
    expect((screen.getByRole("button", { name: /buka workspace/i }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/42%/)).toBeDefined();
    expect(screen.queryByRole("link", { name: /buka workspace/i })).toBeNull();
  });

  it("gates workspace for legacy serialized analyzing status", () => {
    render(
      <ProjectDocumentTable
        documents={[{ ...documents[0], status: "ANALYZING" as DocumentItem["status"], progress_pct: 42 }]}
        role="ENGINEER"
        loading={false}
        onUpload={vi.fn()}
        onFiltersChange={vi.fn()}
      />,
    );
    expect((screen.getByRole("button", { name: /buka workspace/i }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Sedang Dianalisis/)).toBeDefined();
  });

  it("does not block a claim because of an active task in another project", () => {
    const target = { ...documents[0], project_id: "project-a", assigned_to_id: null };
    const activeElsewhere = {
      ...documents[0],
      id: "doc-b",
      filename: "engineer-b.pdf",
      project_id: "project-b",
      assigned_to_id: "current-user",
      workflow_status: "ANALYZING" as DocumentItem["workflow_status"],
    };
    render(
      <ProjectDocumentTable
        documents={[target, activeElsewhere]}
        projectId="project-a"
        role="ENGINEER"
        currentUserId="current-user"
        loading={false}
        onUpload={vi.fn()}
        onFiltersChange={vi.fn()}
      />,
    );

    expect((screen.getByRole("button", { name: /ambil tugas/i }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("keeps terminal workspace links but hides upload and disables assignment when finished", () => {
    render(
      <ProjectDocumentTable
        documents={documents}
        role="LEAD_ENGINEER"
        loading={false}
        projectFinished
        onUpload={vi.fn()}
        onFiltersChange={vi.fn()}
      />
    );

    expect(screen.getByRole("link", { name: /buka workspace/i })).not.toBeNull();
    expect(screen.queryByRole("button", { name: /upload document/i })).toBeNull();
    expect((screen.getByLabelText(/assign engineer-a/i) as HTMLSelectElement).disabled).toBe(true);
  });
 });
