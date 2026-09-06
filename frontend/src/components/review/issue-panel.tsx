"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  AlertCircle,
  CheckCircle,
  CheckCheck,
  Filter,
  Info,
  Layers,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { getIssueLocation, type IssueItem, type IssueDecision, type IssueDisposition } from "@/lib/api";
import { IssueCard } from "./issue-card";

interface IssuePanelProps {
  issues: IssueItem[];
  selectedIssueId: string | null;
  onSelectIssue: (issueId: string) => void;
  onDecideIssue: (issueId: string, payload: IssueDecision) => Promise<void>;
  onDisposeIssue: (issueId: string, payload: IssueDisposition) => Promise<void>;
  onBulkDecideLanguage: () => Promise<void>;
  onJumpToPage?: (page: number) => void;
  onAddToDictionary?: (term: string) => void;
  isLoading?: boolean;
}

type TabType = "traceability" | "language";
type SeverityFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
type StatusFilter = "ALL" | "PENDING" | "ACCEPTED" | "REJECTED" | "FLAGGED" | "DISPOSED";

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
  onDecideIssue,
  onDisposeIssue,
  onBulkDecideLanguage,
  onJumpToPage,
  onAddToDictionary,
  isLoading = false,
}: IssuePanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("traceability");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isBulkSubmitting, setIsBulkSubmitting] = useState<boolean>(false);
  const [bulkFeedback, setBulkFeedback] = useState<string | null>(null);

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
      if (statusFilter !== "ALL") {
        if (statusFilter === "PENDING" && iss.decision) return false;
        if (statusFilter !== "PENDING" && iss.decision?.toUpperCase() !== statusFilter) return false;
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
  }, [currentTabIssues, severityFilter, statusFilter, searchQuery]);

  // Summary stats
  const totalCount = currentTabIssues.length;
  const pendingCount = currentTabIssues.filter((i) => !i.decision).length;
  const criticalCount = currentTabIssues.filter((i) => i.severity === "CRITICAL").length;
  const highCount = currentTabIssues.filter((i) => i.severity === "HIGH").length;

  // Scroll to active card when selectedIssueId changes
  useEffect(() => {
    if (selectedIssueId && activeCardRef.current?.scrollIntoView) {
      activeCardRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedIssueId]);

  const handleBulkAcceptLanguage = async () => {
    setIsBulkSubmitting(true);
    setBulkFeedback(null);
    try {
      await onBulkDecideLanguage();
      setBulkFeedback("High-confidence language issues accepted successfully.");
      setTimeout(() => setBulkFeedback(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to bulk accept language issues.";
      setBulkFeedback(`Error: ${msg}`);
    } finally {
      setIsBulkSubmitting(false);
    }
  };

  return (
    <aside className="issue-panel" aria-label="Review Issues Panel">
      {/* Category Tabs */}
      <div className="panel-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "traceability"}
          className={`tab-button ${activeTab === "traceability" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("traceability")}
        >
          <Layers size={16} />
          <span>Traceability & Compliance</span>
          <span className="tab-badge">{traceabilityIssues.length}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "language"}
          className={`tab-button ${activeTab === "language" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("language")}
        >
          <Sparkles size={16} />
          <span>Language & Style</span>
          <span className="tab-badge">{languageIssues.length}</span>
        </button>
      </div>

      {/* Summary KPI Strip */}
      <div className="panel-kpi-strip">
        <div className="kpi-item">
          <span className="kpi-label">Total</span>
          <span className="kpi-value">{totalCount}</span>
        </div>
        <div className="kpi-item">
          <span className="kpi-label">Pending</span>
          <span className={`kpi-value ${pendingCount > 0 ? "kpi-pending" : ""}`}>
            {pendingCount}
          </span>
        </div>
        {criticalCount > 0 && (
          <div className="kpi-item">
            <span className="kpi-label">Critical</span>
            <span className="kpi-value kpi-critical">{criticalCount}</span>
          </div>
        )}
        {highCount > 0 && (
          <div className="kpi-item">
            <span className="kpi-label">High</span>
            <span className="kpi-value kpi-high">{highCount}</span>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="panel-controls">
        <div className="search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Filter by rule, message, page..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
            aria-label="Filter issues"
          />
        </div>

        <div className="filter-dropdowns">
          <div className="filter-item">
            <Filter size={13} />
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
              aria-label="Filter by severity"
              className="filter-select"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>

          <div className="filter-item">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              aria-label="Filter by status"
              className="filter-select"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
              <option value="FLAGGED">Flagged</option>
              <option value="DISPOSED">Disposed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Bulk Action Area / Prohibited Banner */}
      {activeTab === "traceability" ? (
        <div className="bulk-prohibited-banner" role="status">
          <div className="banner-header">
            <ShieldAlert size={16} className="banner-icon" />
            <strong>Human Sign-Off Enforced (PRD §3.2)</strong>
          </div>
          <p className="banner-text">
            Per QA Requirement §3.2 and Scenario A-10, bulk acceptance is prohibited for
            traceability, table math, revision sync, and standard compliance findings. Each finding
            must be individually verified and decided.
          </p>
          <button
            type="button"
            disabled
            className="btn btn-bulk-disabled"
            title="Bulk acceptance is prohibited for traceability findings"
          >
            Bulk Acceptance Prohibited
          </button>
        </div>
      ) : (
        <div className="bulk-action-bar">
          <div className="bulk-info">
            <CheckCheck size={16} className="bulk-icon" />
            <span>Fast-track high-confidence grammatical and stylistic recommendations.</span>
          </div>
          <button
            type="button"
            onClick={handleBulkAcceptLanguage}
            disabled={isBulkSubmitting || pendingCount === 0}
            className="btn btn-bulk-accept"
          >
            {isBulkSubmitting ? "Accepting..." : "Accept All High-Confidence"}
          </button>
        </div>
      )}

      {bulkFeedback && (
        <div
          className={`bulk-feedback ${
            bulkFeedback.startsWith("Error") ? "feedback-error" : "feedback-success"
          }`}
          role="alert"
        >
          {bulkFeedback.startsWith("Error") ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
          <span>{bulkFeedback}</span>
        </div>
      )}

      {/* Issues List */}
      <div className="issues-list" role="feed" aria-busy={isLoading}>
        {isLoading ? (
          <div className="empty-panel-state">
            <div className="loading-spinner" />
            <p>Loading findings...</p>
          </div>
        ) : filteredIssues.length === 0 ? (
          <div className="empty-panel-state">
            <Info size={28} className="empty-icon" />
            <p className="empty-title">No matching findings</p>
            <p className="empty-sub">
              {issues.length === 0
                ? "No issues were identified for this document."
                : "No issues match the selected filters."}
            </p>
          </div>
        ) : (
          filteredIssues.map((issue) => {
            const isSelected = selectedIssueId === issue.id;
            return (
              <div
                key={issue.id}
                ref={isSelected ? activeCardRef : undefined}
                className={`issue-card-wrapper ${isSelected ? "card-wrapper-selected" : ""}`}
              >
                <IssueCard
                  issue={issue}
                  isSelected={isSelected}
                  onSelect={() => onSelectIssue(issue.id)}
                  onDecide={onDecideIssue}
                  onDispose={onDisposeIssue}
                  onJumpToPage={onJumpToPage}
                  onAddToDictionary={onAddToDictionary}
                />
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
