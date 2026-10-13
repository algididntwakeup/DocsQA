import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SuperuserDashboardPage from "./page";
import * as api from "@/lib/api";
import type { ManagedUser, UserSession } from "@/lib/api";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof api>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: vi.fn(),
    listManagedUsers: vi.fn(),
    fetchPortfolioStats: vi.fn(),
  };
});

function stats(overrides: Partial<api.PortfolioStats> = {}): api.PortfolioStats {
  return {
    total_projects: 3,
    finished_projects: 0,
    total_documents: 4,
    documents_by_status: { COMPLETED: 4 },
    documents_by_workflow: { ANALYZING: 4 },
    projects_by_owner: [
      {
        owner_id: "owner-1",
        owner_name: "Local Lead Engineer",
        project_count: 2,
        document_count: 2,
      },
    ],
    ...overrides,
  };
}

function session(overrides: Partial<UserSession> = {}): UserSession {
  return {
    id: "user-1",
    email: "m.alghifari@reksolindo.co.id",
    full_name: "Muhammad Al Ghifari",
    role: "ENGINEER",
    is_active: true,
    is_superuser: true,
    created_at: "2026-09-10T00:00:00Z",
    ...overrides,
  };
}

function managedUser(overrides: Partial<ManagedUser> = {}): ManagedUser {
  return {
    id: "user-2",
    email: "engineer@example.test",
    full_name: "Engineer One",
    role: "ENGINEER",
    is_active: true,
    is_superuser: false,
    created_at: "2026-09-10T00:00:00Z",
    total_documents_owned: 0,
    ...overrides,
  };
}

describe("SuperuserDashboardPage", () => {
  beforeEach(() => {
    window.localStorage.setItem("matqc-locale", "en");
    vi.clearAllMocks();
  });

  it("renders the control panel for a locally flagged superuser", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session());
    vi.mocked(api.listManagedUsers).mockResolvedValue([managedUser()]);
    vi.mocked(api.fetchPortfolioStats).mockResolvedValue(stats());

    render(<SuperuserDashboardPage />);

    expect(await screen.findByText(/PRISM Control Panel/i)).toBeDefined();
    expect(screen.getByText("Muhammad Al Ghifari · m.alghifari@reksolindo.co.id")).toBeDefined();
    expect(screen.getByRole("link", { name: /Manage Users/i })).toBeDefined();
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the real user and portfolio counts instead of zero", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session());
    vi.mocked(api.listManagedUsers).mockResolvedValue([
      managedUser({ id: "u-2", full_name: "Engineer One" }),
      managedUser({ id: "u-3", full_name: "Engineer Two" }),
      managedUser({ id: "u-4", full_name: "Lead One", role: "LEAD_ENGINEER" }),
    ]);
    vi.mocked(api.fetchPortfolioStats).mockResolvedValue(stats());

    render(<SuperuserDashboardPage />);

    await screen.findByText(/PRISM Control Panel/i);
    // 3 accounts, 1 lead, and the portfolio totals from the stats payload.
    // Counts are read from the card headings so the assertions stay unambiguous.
    const userCard = screen.getByRole("heading", { name: "Manage Users" }).closest("article");
    expect(userCard?.textContent).toContain("3");
    const leadCard = screen.getByRole("heading", { name: "Lead Engineer" }).closest("article");
    expect(leadCard?.textContent).toContain("1");
    expect(leadCard?.textContent).toContain("2 Engineer");
    const portfolioCard = screen
      .getByRole("heading", { name: "Portfolio Overview" })
      .closest("article");
    expect(portfolioCard?.textContent).toContain("3");
    expect(portfolioCard?.textContent).toContain("4 Total documents");
    // The cross-owner table exposes the portfolio detail.
    expect(screen.getByText("Local Lead Engineer")).toBeDefined();
  });

  it("surfaces a refusal instead of silently rendering zeros", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session());
    vi.mocked(api.listManagedUsers).mockRejectedValue(
      new api.ApiError("User management access required.", 403),
    );
    vi.mocked(api.fetchPortfolioStats).mockResolvedValue(stats());

    render(<SuperuserDashboardPage />);

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByText("User management access required.")).toBeDefined();
  });

  it("redirects non-superusers to the project explorer", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(
      session({ role: "LEAD_ENGINEER", is_superuser: false }),
    );

    render(<SuperuserDashboardPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/projects"));
    expect(screen.queryByText(/PRISM Control Panel/i)).toBeNull();
  });

  it("redirects to login when the session is gone", async () => {
    vi.mocked(api.getCurrentUser).mockRejectedValue(new api.ApiError("Unauthorized", 401));

    render(<SuperuserDashboardPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
