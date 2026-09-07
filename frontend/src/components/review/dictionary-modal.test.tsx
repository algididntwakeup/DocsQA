import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DictionaryModal } from "./dictionary-modal";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listDictionaryTerms: vi.fn(),
    createDictionaryTerm: vi.fn(),
  };
});

describe("DictionaryModal", () => {
  const mockTerms: api.DictionaryTermItem[] = [
    {
      id: "term-1",
      term: "Inconel625",
      scope: "organization",
      status: "APPROVED",
      rationale: "Nickel-based superalloy standard",
      created_at: "2026-09-05T10:00:00Z",
      approved_by: "lead@local",
      approved_at: "2026-09-05T10:05:00Z",
    },
    {
      id: "term-2",
      term: "ASTM-A516",
      scope: "organization",
      status: "PENDING",
      rationale: "Pressure vessel carbon steel plate",
      created_at: "2026-09-05T11:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listDictionaryTerms).mockResolvedValue({
      terms: mockTerms,
      page_info: {
        page: 1,
        page_size: 50,
        total: 2,
      },
    });
  });

  it("renders modal when isOpen is true and loads terms", async () => {
    render(<DictionaryModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText("Governed Engineering Dictionary")).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText("Inconel625")).toBeDefined();
      expect(screen.getByText("ASTM-A516")).toBeDefined();
    });
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(<DictionaryModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("pre-fills form when initialTerm is provided and submits new term", async () => {
    const onTermCreated = vi.fn();
    vi.mocked(api.createDictionaryTerm).mockResolvedValue({
      id: "term-3",
      term: "Monel400",
      scope: "organization",
      status: "PENDING",
      rationale: "Marine alloy specification",
      created_at: "2026-09-05T12:00:00Z",
    });

    render(
      <DictionaryModal
        isOpen={true}
        onClose={vi.fn()}
        initialTerm="Monel400"
        onTermCreated={onTermCreated}
      />
    );

    const input = screen.getByPlaceholderText(/Inconel625/i) as HTMLInputElement;
    expect(input.value).toBe("Monel400");

    const submitBtn = screen.getByRole("button", { name: /submit to dictionary/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createDictionaryTerm).toHaveBeenCalledWith({
        term: "Monel400",
        scope: "organization",
        rationale: undefined,
      });
      expect(onTermCreated).toHaveBeenCalledWith("Monel400");
    });
  });

  it("allows switching between list and add term tabs", async () => {
    render(<DictionaryModal isOpen={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Inconel625")).toBeDefined();
    });

    // Click Add Term tab
    const addTab = screen.getByRole("button", { name: /add term/i });
    fireEvent.click(addTab);

    expect(screen.getByText(/Term \/ Specification Symbol/i)).toBeDefined();

    // Click Approved & Pending Terms tab
    const listTab = screen.getByRole("button", { name: /approved & pending terms/i });
    fireEvent.click(listTab);

    expect(screen.getByText("Inconel625")).toBeDefined();
  });
});
