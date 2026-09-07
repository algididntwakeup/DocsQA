import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IssuePanel } from "./issue-panel";
import type { IssueItem } from "@/lib/api";

describe("IssuePanel", () => {
  const sampleIssues: IssueItem[] = [
    {
      id: "trace-1",
      document_id: "doc-1",
      category: "TRACEABILITY",
      type: "RULE_TABLE_MATH_001",
      severity: "CRITICAL",
      confidence: 0.95,
      message: "Total row does not match sum of subtotals",
      included_in_report: true,
      reviewer_note: null,
      version: 1,
      evidence: {
        kind: "TABLE_MATH",
        extractor_version: "1.0",
        rule_version: "1.0",
        stated_value: "100.00",
        computed_value: "120.00",
        delta: "20.00",
        tolerance: "0.01",
        total_location: {
          page_index: 0,
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
    },
    {
      id: "trace-2",
      document_id: "doc-1",
      category: "TRACEABILITY",
      type: "RULE_STANDARDS_STRICTNESS_001",
      severity: "HIGH",
      confidence: 0.9,
      message: "Missing mandatory ISO citation year",
      included_in_report: false,
      reviewer_note: "Excluded because draft reference",
      version: 1,
      evidence: {
        kind: "STANDARD",
        extractor_version: "1.0",
        rule_version: "1.0",
        cited_standard: "ISO 9001",
        body_location: {
          page_index: 1,
          x0: 50,
          y0: 50,
          x1: 150,
          y1: 70,
          page_width: 612,
          page_height: 792,
        },
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    },
    {
      id: "lang-1",
      document_id: "doc-1",
      category: "LINGUISTIC",
      type: "RULE_PASSIVE_VOICE",
      severity: "LOW",
      confidence: 0.85,
      message: "Passive voice construct detected",
      included_in_report: true,
      reviewer_note: null,
      version: 1,
      evidence: {
        kind: "LINGUISTIC",
        extractor_version: "1.0",
        rule_version: "1.0",
        original_text: "was performed by",
        suggestion: "Use active voice",
        location: {
          page_index: 2,
          x0: 10,
          y0: 20,
          x1: 30,
          y1: 40,
          page_width: 612,
          page_height: 792,
        },
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    },
  ];

  it("separates traceability and language issues into tabs", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onCurateIssue={vi.fn()}
      />
    );

    // Initial tab is Traceability & Compliance
    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.getByText("RULE_STANDARDS_STRICTNESS_001")).toBeDefined();
    expect(screen.queryByText("RULE_PASSIVE_VOICE")).toBeNull();

    // Switch to Language & Mechanics tab
    const languageTab = screen.getByRole("tab", { name: /language & mechanics/i });
    fireEvent.click(languageTab);

    expect(screen.getByText("RULE_PASSIVE_VOICE")).toBeDefined();
    expect(screen.queryByText("RULE_TABLE_MATH_001")).toBeNull();
  });

  it("filters findings by severity dropdown", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onCurateIssue={vi.fn()}
      />
    );

    const severitySelect = screen.getByLabelText(/filter by severity/i);
    // Filter by HIGH
    fireEvent.change(severitySelect, { target: { value: "HIGH" } });

    expect(screen.queryByText("RULE_TABLE_MATH_001")).toBeNull();
    expect(screen.getByText("RULE_STANDARDS_STRICTNESS_001")).toBeDefined();
  });

  it("filters findings by curation state (INCLUDED vs EXCLUDED)", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onCurateIssue={vi.fn()}
      />
    );

    const curationSelect = screen.getByLabelText(/filter by report status/i);

    // Filter to INCLUDED
    fireEvent.change(curationSelect, { target: { value: "INCLUDED" } });
    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.queryByText("RULE_STANDARDS_STRICTNESS_001")).toBeNull();

    // Filter to EXCLUDED
    fireEvent.change(curationSelect, { target: { value: "EXCLUDED" } });
    expect(screen.queryByText("RULE_TABLE_MATH_001")).toBeNull();
    expect(screen.getByText("RULE_STANDARDS_STRICTNESS_001")).toBeDefined();
  });

  it("filters findings by search query", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onCurateIssue={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText(/filter by rule/i);
    fireEvent.change(searchInput, { target: { value: "subtotals" } });

    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.queryByText("RULE_STANDARDS_STRICTNESS_001")).toBeNull();
  });

  it("propagates curation action to onCurateIssue", async () => {
    const onCurateIssue = vi.fn().mockResolvedValue(undefined);
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onCurateIssue={onCurateIssue}
      />
    );

    // trace-1 is included, so click Exclude
    const excludeButtons = screen.getAllByRole("button", { name: /exclude from report/i });
    fireEvent.click(excludeButtons[0]);

    expect(onCurateIssue).toHaveBeenCalledWith("trace-1", {
      included_in_report: false,
      reviewer_note: null,
    });
  });
});
