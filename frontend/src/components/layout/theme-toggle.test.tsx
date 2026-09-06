import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { ThemeToggle } from "./theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.className = "";
  });

  it("defaults to dark and toggles to light mode on click", () => {
    render(<ThemeToggle />);

    const toggleBtn = screen.getByLabelText("Switch to light theme");
    expect(toggleBtn).toBeDefined();

    fireEvent.click(toggleBtn);

    expect(localStorage.getItem("matqc-theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);

    // Click again to toggle back to dark
    fireEvent.click(screen.getByLabelText("Switch to dark theme"));
    expect(localStorage.getItem("matqc-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
