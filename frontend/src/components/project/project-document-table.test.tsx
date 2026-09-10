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
    expect(screen.getByRole("link", { name: /open review/i }).getAttribute("href")).toBe("/documents/doc-a/review");
  });
});
