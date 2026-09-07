"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  Filter,
  Layers,
  Search,
  Sparkles,
} from "lucide-react";
import { getIssueLocation, type IssueItem } from "@/lib/api";
import { IssueCard } from "./issue-card";

interface IssuePanelProps {
  issues: IssueItem[];
  selectedIssueId: string | null;
  onSelectIssue: (issueId: string) => void;
  onCurateIssue: (
    issueId: string,
    payload: { included_in_report: boolean; reviewer_note?: string | null }
  ) => Promise<void>;
  onJumpToPage?: (page: number) => void;
  onAddToDictionary?: (term: string) => void;
  isLoading?: boolean;
}

type TabType = "traceability" | "language";
type SeverityFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
type CurationFilter = "ALL" | "INCLUDED" | "EXCLUDED";

function isTraceabilityIssue(issue: IssueItem): boolean {
  if (issue.category === "TRACEABILITY" || issue.category === "SYSTEM") {
    return true;
  }
  const rid = (issue.type || "").toUpperCase();
  return (
    rid.startsWith("RULE_TABLE_MATH") ||
    rid.startsWith("RULE_REFERENCE_DRIFT") ||
    rid.startsWith("RULE_REVISION_SYNC") ||
    rid.startsWith("RULE_STANDARDS") ||
    rid.startsWith("SYSTEM_")
  );
}

export function IssuePanel({
  issues,
  selectedIssueId,
  onSelectIssue,
  onCurateIssue,
  onJumpToPage,
  onAddToDictionary,
  isLoading = false,
}: IssuePanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("traceability");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [curationFilter, setCurationFilter] = useState<CurationFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const activeCardRef = useRef<HTMLDivElement | null>(null);

  // Group issues into tabs
  const traceabilityIssues = useMemo(
    () => issues.filter((iss) => isTraceabilityIssue(iss)),
    [issues]
  );
  const languageIssues = useMemo(
    () => issues.filter((iss) => !isTraceabilityIssue(iss)),
    [issues]
  );

  const currentTabIssues = activeTab === "traceability" ? traceabilityIssues : languageIssues;

  // Filter issues based on active filters
  const filteredIssues = useMemo(() => {
    return currentTabIssues.filter((iss) => {
      if (severityFilter !== "ALL" && iss.severity.toUpperCase() !== severityFilter) {
        return false;
      }
      if (curationFilter === "INCLUDED" && !iss.included_in_report) {
        return false;
      }
      if (curationFilter === "EXCLUDED" && iss.included_in_report) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesRule = (iss.type || "").toLowerCase().includes(query);
        const matchesMsg = iss.message.toLowerCase().includes(query);
        const loc = getIssueLocation(iss);
        const matchesLocation = loc.page_number?.toString().includes(query);
        if (!matchesRule && !matchesMsg && !matchesLocation) {
          return false;
        }
      }
      return true;
    });
  }, [currentTabIssues, severityFilter, curationFilter, searchQuery]);

  // Scroll active card into view
  useEffect(() => {
    if (activeCardRef.current && typeof activeCardRef.current.scrollIntoView === "function") {
      activeCardRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [selectedIssueId]);

  const traceIncludedCount = traceabilityIssues.filter((i) => i.included_in_report).length;
  const langIncludedCount = languageIssues.filter((i) => i.included_in_report).length;

  return (
    <aside
      className="flex flex-col h-full bg-surface border-l border-border overflow-hidden"
      aria-label="Findings Panel"
    >
      {/* Tab Switcher */}
      <div className="flex items-center border-b border-border bg-panel shrink-0">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "traceability"}
          onClick={() => setActiveTab("traceability")}
          className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
            activeTab === "traceability"
              ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-surface"
              : "border-transparent text-muted hover:text-ink hover:bg-muted/5"
          }`}
        >
          <Layers size={15} />
          <span>Technical Consistency</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-muted/20 text-muted">
            {traceIncludedCount}/{traceabilityIssues.length}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "language"}
          onClick={() => setActiveTab("language")}
          className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
            activeTab === "language"
              ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-surface"
              : "border-transparent text-muted hover:text-ink hover:bg-muted/5"
          }`}
        >
          <Sparkles size={15} />
          <span>Language & Mechanics</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-muted/20 text-muted">
            {langIncludedCount}/{languageIssues.length}
          </span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 border-b border-border bg-panel space-y-2.5 shrink-0">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-2.5 text-muted" />
          <input
            type="text"
            placeholder="Filter by rule, fact, or page number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded border border-border bg-sunken text-ink focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Severity Filter */}
          <div className="flex-1">
            <label htmlFor="severity-filter" className="sr-only">Filter by Severity</label>
            <select
              id="severity-filter"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
              className="w-full text-xs py-1 px-2 rounded border border-border bg-sunken text-ink focus:outline-none focus:border-sky-500"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical Only</option>
              <option value="HIGH">High Only</option>
              <option value="MEDIUM">Medium Only</option>
              <option value="LOW">Low Only</option>
              <option value="INFO">Info Only</option>
            </select>
          </div>

          {/* Curation Filter */}
          <div className="flex-1">
            <label htmlFor="curation-filter" className="sr-only">Filter by Report Status</label>
            <select
              id="curation-filter"
              value={curationFilter}
              onChange={(e) => setCurationFilter(e.target.value as CurationFilter)}
              className="w-full text-xs py-1 px-2 rounded border border-border bg-sunken text-ink focus:outline-none focus:border-sky-500"
            >
              <option value="ALL">All Report Statuses</option>
              <option value="INCLUDED">Included in Report</option>
              <option value="EXCLUDED">Excluded from Report</option>
            </select>
          </div>
        </div>
      </div>

      {/* Issues List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-muted">
            <div className="animate-spin inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full mb-2" />
            <p>Loading document findings...</p>
          </div>
        ) : filteredIssues.length === 0 ? (
          <div className="py-12 text-center text-xs text-muted space-y-1">
            <Filter size={20} className="mx-auto text-muted/40 mb-2" />
            <p className="font-semibold text-ink">No findings match the current filter</p>
            <p>Try clearing filters or search terms.</p>
          </div>
        ) : (
          filteredIssues.map((issue) => {
            const isSelected = issue.id === selectedIssueId;
            return (
              <div
                key={issue.id}
                ref={isSelected ? activeCardRef : null}
              >
                <IssueCard
                  issue={issue}
                  isSelected={isSelected}
                  onSelect={() => onSelectIssue(issue.id)}
                  onCurate={onCurateIssue}
                  onJumpToPage={onJumpToPage}
                  onAddToDictionary={onAddToDictionary}
                />
              </div>
            );
          })
        )}
      </div>

      {/* Footer / Summary Status */}
      <footer className="p-2.5 px-4 border-t border-border bg-panel text-[11px] text-muted flex items-center justify-between shrink-0">
        <span>
          Showing {filteredIssues.length} of {currentTabIssues.length} findings
        </span>
        <span className="font-medium text-ink">
          {filteredIssues.filter((i) => i.included_in_report).length} included
        </span>
      </footer>
    </aside>
  );
}
