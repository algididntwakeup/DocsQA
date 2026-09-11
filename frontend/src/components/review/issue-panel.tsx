"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import { ChevronLeft, ChevronRight, Filter, Layers, ListFilter, Search, ShieldCheck, Sparkles } from "lucide-react";
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

type TabType = "all" | "audit" | "budinski" | "standards" | "language";
type SeverityFilter =
  | "ALL"
  | "BLOCKER"
  | "CRITICAL"
  | "MAJOR"
  | "MINOR"
  | "INFO"
  | "HIGH"
  | "MEDIUM"
  | "LOW";
type CurationFilter = "ALL" | "INCLUDED" | "EXCLUDED";

const SEVERITY_ORDER: Record<string, number> = {
  BLOCKER: 0,
  CRITICAL: 1,
  MAJOR: 2,
  MINOR: 3,
  INFO: 4,
  HIGH: 2,
  MEDIUM: 3,
  LOW: 4,
};

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
  const tabStripRef = useRef<HTMLDivElement | null>(null);

  // Drag-to-scroll state
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [hasMoved, setHasMoved] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Group issues into tabs
  const sortIssues = (items: IssueItem[]) =>
    [...items].sort(
      (a, b) =>
        (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99) ||
        a.created_at.localeCompare(b.created_at)
    );

  const auditIssues = useMemo(
    () => sortIssues(issues.filter((issue) => getIssueTab(issue) === "audit")),
    [issues]
  );
  const standardsIssues = useMemo(
    () => sortIssues(issues.filter((issue) => getIssueTab(issue) === "standards")),
    [issues]
  );
  const languageIssues = useMemo(
    () => sortIssues(issues.filter((issue) => getIssueTab(issue) === "language")),
    [issues]
  );
  const budinskiIssues = useMemo(
    () => sortIssues(issues.filter((issue) => issue.category === "BUDINSKI")),
    [issues]
  );

  const currentTabIssues =
    activeTab === "all"
      ? sortIssues(issues)
      : activeTab === "audit"
      ? auditIssues
      : activeTab === "budinski"
      ? budinskiIssues
      : activeTab === "standards"
      ? standardsIssues
      : languageIssues;

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

  // Check scroll boundary
  const updateScrollButtons = () => {
    const el = tabStripRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  };

  useEffect(() => {
    updateScrollButtons();
    const el = tabStripRef.current;
    if (!el) return;
    el.addEventListener("scroll", updateScrollButtons, { passive: true });
    window.addEventListener("resize", updateScrollButtons);
    return () => {
      el.removeEventListener("scroll", updateScrollButtons);
      window.removeEventListener("resize", updateScrollButtons);
    };
  }, []);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = tabStripRef.current;
    if (!el) return;
    setIsDragging(true);
    setStartX(e.pageX - el.offsetLeft);
    setScrollLeft(el.scrollLeft);
    setHasMoved(false);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const el = tabStripRef.current;
    if (!el) return;
    e.preventDefault();
    const x = e.pageX - el.offsetLeft;
    const walk = (x - startX) * 1.2;
    if (Math.abs(walk) > 4) {
      setHasMoved(true);
    }
    el.scrollLeft = scrollLeft - walk;
    updateScrollButtons();
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  const scrollByAmount = (amount: number) => {
    tabStripRef.current?.scrollBy({ left: amount, behavior: "smooth" });
  };

  const handleTabClick = (tab: TabType) => {
    if (!hasMoved) {
      setActiveTab(tab);
    }
  };

  const allIncludedCount = issues.filter((i) => i.included_in_report).length;
  const auditIncludedCount = auditIssues.filter((i) => i.included_in_report).length;
  const budinskiIncludedCount = budinskiIssues.filter((i) => i.included_in_report).length;
  const standardsIncludedCount = standardsIssues.filter((i) => i.included_in_report).length;
  const langIncludedCount = languageIssues.filter((i) => i.included_in_report).length;

  return (
    <aside
      className="flex flex-col h-full min-h-0 min-w-0 bg-white border-l border-slate-200 overflow-hidden font-sans select-none"
      aria-label="Findings Panel"
    >
      {/* Draggable & Scrollable Tab Bar Header */}
      <div className="relative group border-b border-slate-200 bg-slate-50/70 p-1 shrink-0">
        {/* Left scroll chevron */}
        {canScrollLeft && (
          <button
            type="button"
            onClick={() => scrollByAmount(-140)}
            className="absolute left-1 top-1/2 -translate-y-1/2 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white shadow-md text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition"
            aria-label="Scroll tabs left"
          >
            <ChevronLeft size={16} />
          </button>
        )}

        {/* Scrollable / Draggable container */}
        <div
          ref={tabStripRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          className={`flex items-center gap-1.5 overflow-x-auto py-1 px-1.5 no-scrollbar scroll-smooth cursor-grab active:cursor-grabbing ${
            isDragging ? "select-none" : ""
          }`}
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {/* Layout & Format Tab */}
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "audit"}
            onClick={() => handleTabClick("audit")}
            className={`shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
              activeTab === "audit"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <ShieldCheck size={13} />
            <span>Layout & Format</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                activeTab === "audit" ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {auditIncludedCount}/{auditIssues.length}
            </span>
          </button>

          {/* Budinski Compliance Tab */}
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "budinski"}
            onClick={() => handleTabClick("budinski")}
            className={`shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
              activeTab === "budinski"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <ShieldCheck size={13} className={activeTab === "budinski" ? "text-white" : "text-indigo-600"} />
            <span>Budinski Compliance</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                activeTab === "budinski" ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {budinskiIncludedCount}/{budinskiIssues.length}
            </span>
          </button>

          {/* Standards Audit Tab */}
          <button
            type="button"
            role="tab"
            aria-label="Standards Audit"
            aria-selected={activeTab === "standards"}
            onClick={() => handleTabClick("standards")}
            className={`shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
              activeTab === "standards"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <Layers size={13} />
            <span>Standards Audit</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                activeTab === "standards" ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {standardsIncludedCount}/{standardsIssues.length}
            </span>
          </button>

          {/* Language & Typos Tab */}
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "language"}
            onClick={() => handleTabClick("language")}
            className={`shrink-0 whitespace-nowrap inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
              activeTab === "language"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <Sparkles size={13} />
            <span>Language & Typos</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                activeTab === "language" ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {langIncludedCount}/{languageIssues.length}
            </span>
          </button>
        </div>

        {/* Right scroll chevron */}
        {canScrollRight && (
          <button
            type="button"
            onClick={() => scrollByAmount(140)}
            className="absolute right-1 top-1/2 -translate-y-1/2 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white shadow-md text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition"
            aria-label="Scroll tabs right"
          >
            <ChevronRight size={16} />
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 border-b border-slate-200 bg-white space-y-2 shrink-0">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Filter by rule, fact, or page number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
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
              className="w-full text-xs py-1 px-2 rounded-lg border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Severities</option>
              <option value="BLOCKER">Blocker Only</option>
              <option value="CRITICAL">Critical Only</option>
              <option value="MAJOR">Major Only</option>
              <option value="MINOR">Minor Only</option>
              <option value="INFO">Info Only</option>
              <option value="HIGH">Legacy High Only</option>
              <option value="MEDIUM">Legacy Medium Only</option>
              <option value="LOW">Legacy Low Only</option>
            </select>
          </div>

          {/* Curation Filter */}
          <div className="flex-1">
            <label htmlFor="curation-filter" className="sr-only">Filter by Report Status</label>
            <select
              id="curation-filter"
              value={curationFilter}
              onChange={(e) => setCurationFilter(e.target.value as CurationFilter)}
              className="w-full text-xs py-1 px-2 rounded-lg border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Report Statuses</option>
              <option value="INCLUDED">Included in Report</option>
              <option value="EXCLUDED">Excluded from Report</option>
            </select>
          </div>
        </div>
      </div>

      {/* Issues List */}
      <div className="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden p-3 space-y-3 bg-slate-50/50">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500">
            <div className="animate-spin inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full mb-2" />
            <p>Loading document findings...</p>
          </div>
        ) : filteredIssues.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 space-y-1">
            <Filter size={20} className="mx-auto text-slate-300 mb-2" />
            <p className="font-semibold text-slate-800">No findings match the current filter</p>
            <p>Try clearing filters or search terms.</p>
          </div>
        ) : (
          filteredIssues.map((issue) => {
            const isSelected = issue.id === selectedIssueId;
            return (
              <div key={issue.id} ref={isSelected ? activeCardRef : null}>
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
      <footer className="p-2.5 px-4 border-t border-slate-200 bg-white text-[11px] text-slate-500 flex items-center justify-between shrink-0">
        <span>
          Showing {filteredIssues.length} of {currentTabIssues.length} findings
        </span>
        <span className="font-semibold text-slate-800">
          {filteredIssues.filter((i) => i.included_in_report).length} included
        </span>
      </footer>
    </aside>
  );
}
