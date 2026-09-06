import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { ThemeToggle } from "./theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.className = "";
  });

  it("defaults to light and toggles to dark mode on click", () => {
    render(<ThemeToggle />);

    const toggleBtn = screen.getByLabelText("Switch to dark theme");
    expect(toggleBtn).toBeDefined();

    fireEvent.click(toggleBtn);

    expect(localStorage.getItem("matqc-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(document.documentElement.classList.contains("light")).toBe(false);

    // Click again to toggle back to light
    fireEvent.click(screen.getByLabelText("Switch to light theme"));
    expect(localStorage.getItem("matqc-theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
