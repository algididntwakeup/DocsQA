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
        onDecideIssue={vi.fn()}
        onDisposeIssue={vi.fn()}
        onBulkDecideLanguage={vi.fn()}
      />
    );

    // Initial tab is Traceability & Compliance
    expect(screen.getByText("RULE_TABLE_MATH_001")).toBeDefined();
    expect(screen.getByText("RULE_STANDARDS_STRICTNESS_001")).toBeDefined();
    expect(screen.queryByText("RULE_PASSIVE_VOICE")).toBeNull();

    // Switch to Language & Style tab
    const languageTab = screen.getByRole("tab", { name: /language & style/i });
    fireEvent.click(languageTab);

    expect(screen.getByText("RULE_PASSIVE_VOICE")).toBeDefined();
    expect(screen.queryByText("RULE_TABLE_MATH_001")).toBeNull();
  });

  it("displays PRD §3.2 prohibited banner and disabled bulk button on Traceability tab", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onDecideIssue={vi.fn()}
        onDisposeIssue={vi.fn()}
        onBulkDecideLanguage={vi.fn()}
      />
    );

    expect(screen.getByText(/human sign-off enforced \(prd §3\.2\)/i)).toBeDefined();
    const disabledBtn = screen.getByRole("button", { name: /bulk acceptance prohibited/i });
    expect(disabledBtn.hasAttribute("disabled")).toBe(true);
  });

  it("enables bulk accept button on Language tab and calls handler", async () => {
    const onBulkDecideLanguage = vi.fn().mockResolvedValue(undefined);
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onDecideIssue={vi.fn()}
        onDisposeIssue={vi.fn()}
        onBulkDecideLanguage={onBulkDecideLanguage}
      />
    );

    const languageTab = screen.getByRole("tab", { name: /language & style/i });
    fireEvent.click(languageTab);

    const bulkBtn = screen.getByRole("button", { name: /accept all high-confidence/i });
    expect(bulkBtn.hasAttribute("disabled")).toBe(false);

    fireEvent.click(bulkBtn);
    expect(onBulkDecideLanguage).toHaveBeenCalled();
  });

  it("filters findings by severity dropdown", () => {
    render(
      <IssuePanel
        issues={sampleIssues}
        selectedIssueId={null}
        onSelectIssue={vi.fn()}
        onDecideIssue={vi.fn()}
        onDisposeIssue={vi.fn()}
        onBulkDecideLanguage={vi.fn()}
      />
    );

    const severitySelect = screen.getByLabelText(/filter by severity/i);
    // Filter by HIGH
    fireEvent.change(severitySelect, { target: { value: "HIGH" } });

    expect(screen.queryByText("RULE_TABLE_MATH_001")).toBeNull();
    expect(screen.getByText("RULE_STANDARDS_STRICTNESS_001")).toBeDefined();
  });
});
