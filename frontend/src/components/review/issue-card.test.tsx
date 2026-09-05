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
        onDecide={vi.fn()}
        onDispose={vi.fn()}
        onJumpToPage={vi.fn()}
      />
    );

    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.getByText("CRITICAL")).toBeDefined();
    expect(screen.getByText("Column sum mismatch in Table 3.2")).toBeDefined();
    expect(screen.getByText("1,250.00")).toBeDefined();
    expect(screen.getByText("1,350.00")).toBeDefined();
  });

  it("triggers onDecide with ACCEPTED and expected_version when Accept button is clicked", async () => {
    const onDecide = vi.fn().mockResolvedValue(undefined);
    render(
      <IssueCard
        issue={tableMathIssue}
        onDecide={onDecide}
        onDispose={vi.fn()}
        onJumpToPage={vi.fn()}
      />
    );

    const acceptBtn = screen.getByRole("button", { name: /accept/i });
    fireEvent.click(acceptBtn);

    expect(onDecide).toHaveBeenCalledWith("iss-math-1", {
      decision: "ACCEPTED",
      expected_version: 1,
      comment: undefined,
      actor_id: "reviewer@local",
      actor_role: "QA_ENGINEER",
    });
  });

  it("requires justification before submitting Lead Reviewer disposition", async () => {
    const onDispose = vi.fn().mockResolvedValue(undefined);
    render(
      <IssueCard
        issue={tableMathIssue}
        onDecide={vi.fn()}
        onDispose={onDispose}
        onJumpToPage={vi.fn()}
      />
    );

    // Expand lead controls
    const leadToggle = screen.getByRole("button", { name: /lead disposition/i });
    fireEvent.click(leadToggle);

    // Click Justified Exception without justification
    const justifyBtn = screen.getByRole("button", { name: /justified exception/i });
    fireEvent.click(justifyBtn);

    // Disposition should NOT be called without justification
    expect(onDispose).not.toHaveBeenCalled();
    expect(screen.getByText(/justification note is required/i)).toBeDefined();

    // Type justification and retry
    const textarea = screen.getByPlaceholderText(/regulatory justification/i);
    fireEvent.change(textarea, { target: { value: "Approved under engineering waiver #402" } });
    fireEvent.click(justifyBtn);

    expect(onDispose).toHaveBeenCalledWith("iss-math-1", {
      disposition: "JUSTIFIED_EXCEPTION",
      justification: "Approved under engineering waiver #402",
      expected_version: 1,
      actor_id: "lead_reviewer@local",
      actor_role: "LEAD_REVIEWER",
    });
  });

  it("calls onJumpToPage when page badge is clicked", () => {
    const onJumpToPage = vi.fn();
    render(
      <IssueCard
        issue={tableMathIssue}
        onDecide={vi.fn()}
        onDispose={vi.fn()}
        onJumpToPage={onJumpToPage}
      />
    );

    const pageBadge = screen.getByText("p. 4");
    fireEvent.click(pageBadge);

    expect(onJumpToPage).toHaveBeenCalledWith(4);
  });
});
