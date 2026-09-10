import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserProjectsModal } from "./user-projects-modal";
import * as api from "@/lib/api";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, listProjectsForUser: vi.fn() };
});

const user = {
  id: "user-1", email: "engineer@example.test", full_name: "Engineer One", role: "ENGINEER" as const,
  is_active: true, created_at: "2026-09-10T00:00:00Z", total_documents_owned: 2,
};

describe("UserProjectsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listProjectsForUser).mockResolvedValue([{
      id: "project-1", name: "Central Plant", code: null, description: null, plant_area: "Unit A",
      created_by_id: "lead-1", created_by_name: "Lead One", assigned_to_id: user.id,
      assigned_to_name: user.full_name, total_documents: 3, status: "ACTIVE", created_at: "2026-09-10T00:00:00Z",
    }]);
  });

  it("renders projects assigned to the selected user", async () => {
    render(<UserProjectsModal user={user} onClose={vi.fn()} />);
    expect(await screen.findByText("Central Plant")).toBeDefined();
    expect(screen.getByText(/3 documents/)).toBeDefined();
    await waitFor(() => expect(api.listProjectsForUser).toHaveBeenCalledWith(user.id));
  });
});
