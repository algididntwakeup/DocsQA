import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("LoginPage", () => {
  it("offers BIMA SSO without local credential or registration forms", () => {
    render(<LoginPage />);

    expect(screen.getByRole("button", { name: /sign in with bima sso/i })).toBeTruthy();
    expect(screen.queryByLabelText(/email|username|password/i)).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("link", { name: /register|sign up/i })).toBeNull();
    expect(
      screen.queryByRole("button", { name: /^(sign in|register|sign up)$/i })
    ).toBeNull();
  });
});
