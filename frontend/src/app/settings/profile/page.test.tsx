import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfileSettingsPage from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getCurrentUser: vi.fn(), updateProfile: vi.fn() };
});
vi.mock("sonner", () => ({ toast: { success: vi.fn() } }));

const user = {
  id: "user-1", email: "old@example.test", full_name: "Old Name", role: "ENGINEER" as const,
  is_active: true, created_at: "2026-09-10T00:00:00Z",
};

describe("ProfileSettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCurrentUser).mockResolvedValue(user);
    vi.mocked(api.updateProfile).mockResolvedValue({ ...user, email: "new@example.test", full_name: "New Name" });
  });

  it("edits and submits profile fields with a success toast", async () => {
    render(<ProfileSettingsPage />);
    const name = await screen.findByLabelText("Nama Lengkap");
    fireEvent.change(name, { target: { value: "New Name" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => expect(api.updateProfile).toHaveBeenCalledWith({ full_name: "New Name", email: "new@example.test" }));
    expect((await import("sonner")).toast.success).toHaveBeenCalledWith("Profile updated successfully.");
  });
});
