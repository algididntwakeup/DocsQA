import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./app-shell";
import { LocaleProvider } from "./locale-provider";
import * as api from "@/lib/api";
import type { UserSession } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/projects",
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof api>("@/lib/api");
  return { ...actual, getCurrentUser: vi.fn(), logout: vi.fn() };
});

function session(overrides: Partial<UserSession> = {}): UserSession {
  return {
    id: "user-1",
    email: "engineer@example.test",
    full_name: "Engineer One",
    role: "ENGINEER",
    is_active: true,
    is_superuser: false,
    created_at: "2026-09-10T00:00:00Z",
    ...overrides,
  };
}

function renderShell() {
  window.localStorage.setItem("matqc-locale", "en");
  return render(
    <LocaleProvider>
      <AppShell>
        <div>workspace content</div>
      </AppShell>
    </LocaleProvider>,
  );
}

describe("AppShell dashboard navigation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows Open Dashboard only for locally flagged superusers", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session({ is_superuser: true }));

    renderShell();

    const dashboard = await screen.findByRole("link", { name: /Open Dashboard/i });
    expect(dashboard.getAttribute("href")).toBe("/admin/dashboard");
  });

  it("hides Open Dashboard for lead engineers without the local flag", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(
      session({ role: "LEAD_ENGINEER", is_superuser: false }),
    );

    renderShell();

    // Leads keep the user console but never the superuser control panel.
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /Manage Users/i })).toBeDefined(),
    );
    expect(screen.queryByRole("link", { name: /Open Dashboard/i })).toBeNull();
  });

  it("hides Open Dashboard from regular engineers", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session());

    renderShell();

    await waitFor(() => expect(screen.getByText("Engineer One")).toBeDefined());
    expect(screen.queryByRole("link", { name: /Open Dashboard/i })).toBeNull();
  });

  it("renders the dashboard button in English regardless of stored locale", async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue(session({ is_superuser: true }));

    // A stale Indonesian locale in storage must not switch the interface: the
    // app is pinned to English.
    window.localStorage.setItem("matqc-locale", "id");
    render(
      <LocaleProvider>
        <AppShell>
          <div>workspace content</div>
        </AppShell>
      </LocaleProvider>,
    );

    expect(await screen.findByRole("link", { name: /Open Dashboard/i })).toBeDefined();
    expect(screen.queryByRole("link", { name: /Buka Dashboard/i })).toBeNull();
  });
});
