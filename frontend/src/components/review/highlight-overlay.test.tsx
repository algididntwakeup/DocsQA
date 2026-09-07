import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightOverlay } from "./highlight-overlay";
import type { IssueItem } from "@/lib/api";

describe("HighlightOverlay", () => {
  const baseIssue: IssueItem = {
    id: "issue-123",
    document_id: "doc-1",
    category: "TRACEABILITY",
    type: "RULE_TABLE_MATH_001",
    severity: "CRITICAL",
    confidence: 0.98,
    message: "Table total mismatch: stated 100.00, computed 110.00",
    included_in_report: true,
    reviewer_note: null,
    version: 1,
    evidence: {
      kind: "TABLE_MATH",
      extractor_version: "1.0",
      rule_version: "1.0",
      stated_value: "100.00",
      computed_value: "110.00",
      delta: "10.00",
      tolerance: "0.01",
      total_location: {
        page_index: 1,
        x0: 100,
        y0: 200,
        x1: 300,
        y1: 250,
        page_width: 600,
        page_height: 800,
      },
      operand_locations: [
        {
          page_index: 1,
          x0: 100,
          y0: 100,
          x1: 200,
          y1: 150,
          page_width: 600,
          page_height: 800,
        },
      ],
    },
    created_at: "2026-09-05T10:00:00Z",
    updated_at: "2026-09-05T10:00:00Z",
  };

  it("renders highlight bounding boxes on matching page", () => {
    const { container } = render(
      <HighlightOverlay activeIssue={baseIssue} currentPage={2} />
    );

    const highlights = container.querySelectorAll(".highlight-box");
    expect(highlights.length).toBeGreaterThanOrEqual(1);

    const primary = container.querySelector(".highlight-primary") as HTMLElement;
    expect(primary).toBeTruthy();
    // Verify percentage calculations: (100 / 600) * 100 = 16.6667%
    expect(primary.style.left).toMatch(/16\.666/);
  });

  it("does not render highlight when currentPage does not match issue page", () => {
    const { container } = render(
      <HighlightOverlay activeIssue={baseIssue} currentPage={5} />
    );

    const highlights = container.querySelectorAll(".highlight-box");
    expect(highlights.length).toBe(0);
  });

  it("renders operand boxes when present in evidence", () => {
    const { container } = render(
      <HighlightOverlay activeIssue={baseIssue} currentPage={2} />
    );

    const operands = container.querySelectorAll(".highlight-operand");
    expect(operands.length).toBe(1);
  });
});
