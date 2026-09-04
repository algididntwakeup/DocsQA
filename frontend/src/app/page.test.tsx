import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the current scaffold entry point", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: /to get started/i }),
    ).toBeDefined();
  });
});
