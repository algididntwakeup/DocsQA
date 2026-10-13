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
  return { ...actual, getCurrentUser: vi.fn(), listManagedUsers: vi.fn() };
});

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

    render(<SuperuserDashboardPage />);

    expect(await screen.findByText(/PRISM Control Panel/i)).toBeDefined();
    expect(screen.getByText("Muhammad Al Ghifari · m.alghifari@reksolindo.co.id")).toBeDefined();
    expect(screen.getByRole("link", { name: /Manage Users/i })).toBeDefined();
    expect(replace).not.toHaveBeenCalled();
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
