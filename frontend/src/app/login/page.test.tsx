import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";
import { ApiError, login } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, login: vi.fn() };
});

describe("LoginPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("submits credentials and navigates without writing localStorage", async () => {
    vi.mocked(login).mockResolvedValue({ access_token: "server-cookie-token", token_type: "bearer", user: {} as never });
    const storage = vi.spyOn(Storage.prototype, "setItem");
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "engineer@test.local" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: /enter workspace/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/projects"));
    expect(storage).not.toHaveBeenCalled();
  });

  it("shows an API authentication error", async () => {
    vi.mocked(login).mockRejectedValue(new ApiError("Invalid email or password.", 401));
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "bad@test.local" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /enter workspace/i }));
    expect((await screen.findByRole("alert")).textContent).toContain("Invalid email or password.");
  });
});
