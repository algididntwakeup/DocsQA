import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DropZone } from "./drop-zone";

describe("DropZone", () => {
  it("accepts a native PDF into the queue", () => {
    const onChange = vi.fn();
    const { container } = render(<DropZone files={[]} onChange={onChange} />);
    const input = container.querySelector("input[type=file]") as HTMLInputElement;
    const file = new File(["%PDF-1.7"], "inspection.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onChange).toHaveBeenCalledWith([file]);
  });

  it("reports an unsupported file", () => {
    const { container } = render(<DropZone files={[]} onChange={vi.fn()} />);
    const input = container.querySelector("input[type=file]") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "notes.txt")] } });
    expect(screen.getByRole("alert").textContent).toMatch(/must be a PDF\/DOCX/i);
  });
});
