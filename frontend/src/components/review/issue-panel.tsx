"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  Filter,
  Layers,
  Search,
  Sparkles,
  ShieldCheck,
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

type TabType = "audit" | "standards" | "language";
type SeverityFilter = "ALL" | "BLOCKER" | "CRITICAL" | "MAJOR" | "MINOR" | "INFO" | "HIGH" | "MEDIUM" | "LOW";
type CurationFilter = "ALL" | "INCLUDED" | "EXCLUDED";

function getIssueTab(issue: IssueItem): TabType {
  if (issue.category === "BUDINSKI" || issue.category === "LAYOUT") return "audit";
  const rule = issue.type.toUpperCase();
  if (issue.category === "TRACEABILITY" && rule.includes("STANDARD")) return "standards";
  return issue.category === "LINGUISTIC" || issue.category === "SPELLING" || issue.category === "GRAMMAR" || issue.category === "DICTIONARY"
    ? "language"
    : "standards";
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
  const [activeTab, setActiveTab] = useState<TabType>("audit");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [curationFilter, setCurationFilter] = useState<CurationFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const activeCardRef = useRef<HTMLDivElement | null>(null);

  // Group issues into tabs
  const auditIssues = useMemo(() => issues.filter((issue) => getIssueTab(issue) === "audit"), [issues]);
  const standardsIssues = useMemo(() => issues.filter((issue) => getIssueTab(issue) === "standards"), [issues]);
  const languageIssues = useMemo(() => issues.filter((issue) => getIssueTab(issue) === "language"), [issues]);

  const currentTabIssues = activeTab === "audit" ? auditIssues : activeTab === "standards" ? standardsIssues : languageIssues;

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

  const auditIncludedCount = auditIssues.filter((i) => i.included_in_report).length;
  const standardsIncludedCount = standardsIssues.filter((i) => i.included_in_report).length;
  const langIncludedCount = languageIssues.filter((i) => i.included_in_report).length;

  return (
    <aside
      className="flex flex-col h-full bg-surface border-l border-line overflow-hidden"
      aria-label="Findings Panel"
    >
      {/* Tab Switcher */}
      <div className="flex items-center border-b border-line bg-panel shrink-0">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "audit"}
          onClick={() => setActiveTab("audit")}
          className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              activeTab === "audit"
              ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-surface"
              : "border-transparent text-muted hover:text-ink hover:bg-muted/5"
          }`}
        >
          <ShieldCheck size={15} />
          <span>Budinski & Layout Audit</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-muted/20 text-muted">
            {auditIncludedCount}/{auditIssues.length}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "standards"}
          onClick={() => setActiveTab("standards")}
          className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              activeTab === "standards"
              ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-surface"
              : "border-transparent text-muted hover:text-ink hover:bg-muted/5"
          }`}
        >
          <Layers size={15} />
          <span>Standards Audit</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-muted/20 text-muted">
            {standardsIncludedCount}/{standardsIssues.length}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "language"}
          onClick={() => setActiveTab("language")}
          className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
            activeTab === "language" ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-surface" : "border-transparent text-muted hover:text-ink hover:bg-muted/5"
          }`}
        >
          <Sparkles size={15} />
          <span>Language</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-muted/20 text-muted">
            {languageIssues.filter((i) => i.included_in_report).length}/{languageIssues.length}
          </span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 border-b border-line bg-panel space-y-2.5 shrink-0">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-2.5 text-muted" />
          <input
            type="text"
            placeholder="Filter by rule, fact, or page number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded border border-line bg-sunken text-ink focus:outline-none focus:border-sky-500 transition-colors"
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
              className="w-full text-xs py-1 px-2 rounded border border-line bg-sunken text-ink focus:outline-none focus:border-sky-500 transition-colors"
            >
              <option value="ALL">All Severities</option>
              <option value="BLOCKER">Blocker Only</option>
              <option value="CRITICAL">Critical Only</option>
              <option value="MAJOR">Major Only</option>
              <option value="MINOR">Minor Only</option>
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
              className="w-full text-xs py-1 px-2 rounded border border-line bg-sunken text-ink focus:outline-none focus:border-sky-500 transition-colors"
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
      <footer className="p-2.5 px-4 border-t border-line bg-panel text-[11px] text-muted flex items-center justify-between shrink-0">
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
