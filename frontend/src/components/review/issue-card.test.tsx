import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IssueCard } from "./issue-card";
import type { IssueItem } from "@/lib/api";

describe("IssueCard", () => {
  const tableMathIssue: IssueItem = {
    id: "iss-math-1",
    document_id: "doc-1",
    category: "TRACEABILITY",
    type: "RULE_TABLE_MATH_001",
    severity: "CRITICAL",
    confidence: 0.95,
    message: "Column sum mismatch in Table 3.2",
    included_in_report: true,
    reviewer_note: null,
    version: 1,
    evidence: {
      kind: "TABLE_MATH",
      extractor_version: "1.0",
      rule_version: "1.0",
      stated_value: "1,250.00",
      computed_value: "1,350.00",
      delta: "100.00",
      tolerance: "0.01",
      total_location: {
        page_index: 3,
        x0: 100,
        y0: 200,
        x1: 300,
        y1: 250,
        page_width: 612,
        page_height: 792,
      },
      operand_locations: [],
    },
    created_at: "2026-09-05T10:00:00Z",
    updated_at: "2026-09-05T10:00:00Z",
  };

  it("renders severity, rule ID, and message", () => {
    render(
      <IssueCard
        issue={tableMathIssue}
        onCurate={vi.fn()}
        onJumpToPage={vi.fn()}
      />
    );

    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.getByText("CRITICAL")).toBeDefined();
    expect(screen.getByText("Column sum mismatch in Table 3.2")).toBeDefined();
    expect(screen.getByText("1,250.00")).toBeDefined();
    expect(screen.getByText("1,350.00")).toBeDefined();
    expect(screen.getByText("In Report")).toBeDefined();
  });

  it("triggers onCurate with included_in_report: false when Exclude from Report button is clicked", async () => {
    const onCurate = vi.fn().mockResolvedValue(undefined);
    render(
      <IssueCard
        issue={tableMathIssue}
        onCurate={onCurate}
        onJumpToPage={vi.fn()}
      />
    );

    const excludeBtn = screen.getByRole("button", { name: /exclude from report/i });
    fireEvent.click(excludeBtn);

    expect(onCurate).toHaveBeenCalledWith("iss-math-1", {
      included_in_report: false,
      reviewer_note: null,
    });
  });

  it("triggers onCurate with included_in_report: true when Include in Report button is clicked", async () => {
    const onCurate = vi.fn().mockResolvedValue(undefined);
    const excludedIssue: IssueItem = {
      ...tableMathIssue,
      included_in_report: false,
    };

    render(
      <IssueCard
        issue={excludedIssue}
        onCurate={onCurate}
        onJumpToPage={vi.fn()}
      />
    );

    expect(screen.getByText("Excluded")).toBeDefined();
    const includeBtn = screen.getByRole("button", { name: /include in report/i });
    fireEvent.click(includeBtn);

    expect(onCurate).toHaveBeenCalledWith("iss-math-1", {
      included_in_report: true,
      reviewer_note: null,
    });
  });

  it("allows adding a reviewer note and calls onCurate with updated note", async () => {
    const onCurate = vi.fn().mockResolvedValue(undefined);
    render(
      <IssueCard
        issue={tableMathIssue}
        onCurate={onCurate}
        onJumpToPage={vi.fn()}
      />
    );

    // Click Add Note
    const addNoteBtn = screen.getByRole("button", { name: /add note/i });
    fireEvent.click(addNoteBtn);

    // Textarea appears
    const textarea = screen.getByPlaceholderText(/engineering clarification/i);
    fireEvent.change(textarea, { target: { value: "Discrepancy verified against sensor log." } });

    // Save note
    const saveBtn = screen.getByRole("button", { name: /save note/i });
    fireEvent.click(saveBtn);

    expect(onCurate).toHaveBeenCalledWith("iss-math-1", {
      included_in_report: true,
      reviewer_note: "Discrepancy verified against sensor log.",
    });
  });

  it("calls onJumpToPage when page badge is clicked", () => {
    const onJumpToPage = vi.fn();
    render(
      <IssueCard
        issue={tableMathIssue}
        onCurate={vi.fn()}
        onJumpToPage={onJumpToPage}
      />
    );

    const pageBadge = screen.getByText("p. 4");
    fireEvent.click(pageBadge);

    expect(onJumpToPage).toHaveBeenCalledWith(4);
  });

  it("renders Add to Dictionary button and triggers callback for spelling issues", () => {
    const onAddToDictionary = vi.fn();
    const spellIssue: IssueItem = {
      id: "iss-spell-1",
      document_id: "doc-1",
      category: "LINGUISTIC",
      type: "SPELLING_ERROR",
      severity: "LOW",
      confidence: 0.9,
      message: "Unrecognized word 'inconel'",
      included_in_report: true,
      reviewer_note: null,
      version: 1,
      evidence: {
        kind: "LINGUISTIC",
        extractor_version: "1.0",
        rule_version: "1.0",
        original_text: "inconel",
        suggestion: "incline",
        location: {
          page_index: 0,
          x0: 50,
          y0: 100,
          x1: 150,
          y1: 120,
          page_width: 612,
          page_height: 792,
        },
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };

    render(
      <IssueCard
        issue={spellIssue}
        onCurate={vi.fn()}
        onJumpToPage={vi.fn()}
        onAddToDictionary={onAddToDictionary}
      />
    );

    const dictBtn = screen.getByRole("button", { name: /add .* to dictionary/i });
    expect(dictBtn).toBeDefined();
    fireEvent.click(dictBtn);
    expect(onAddToDictionary).toHaveBeenCalledWith("inconel");
  });
});
