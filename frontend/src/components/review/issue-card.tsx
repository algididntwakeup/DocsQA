"use client";

import { useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  MapPin,
  XCircle,
} from "lucide-react";
import { getIssueLocation, type IssueItem } from "@/lib/api";

interface IssueCardProps {
  issue: IssueItem;
  isSelected?: boolean;
  onSelect?: () => void;
  onCurate: (
    issueId: string,
    payload: { included_in_report: boolean; reviewer_note?: string | null }
  ) => Promise<void>;
  onJumpToPage?: (page: number) => void;
  onAddToDictionary?: (term: string) => void;
}

export function IssueCard({
  issue,
  isSelected = false,
  onSelect,
  onCurate,
  onJumpToPage,
  onAddToDictionary,
}: IssueCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [isEditingNote, setIsEditingNote] = useState<boolean>(false);
  const [noteText, setNoteText] = useState<string>(issue.reviewer_note ?? "");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const evidence = (issue.evidence ?? {}) as Record<string, unknown>;
  const location = getIssueLocation(issue);

  const handleToggleInclude = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await onCurate(issue.id, {
        included_in_report: !issue.included_in_report,
        reviewer_note: issue.reviewer_note,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update report inclusion";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveNote = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const cleanNote = noteText.trim() || null;
      await onCurate(issue.id, {
        included_in_report: issue.included_in_report,
        reviewer_note: cleanNote,
      });
      setIsEditingNote(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save reviewer note";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const severityBadgeClass = {
    CRITICAL: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
    HIGH: "bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30",
    MEDIUM: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
    LOW: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    INFO: "bg-slate-500/15 text-slate-700 dark:text-slate-300 border-slate-500/30",
  }[issue.severity] ?? "bg-muted text-ink border-line";

  return (
    <article
      data-issue-id={issue.id}
      className={`border rounded-lg transition-all ${
        isSelected
          ? "border-sky-500 shadow-sm ring-1 ring-sky-500/30 bg-surface"
          : "border-line hover:border-line-strong bg-panel"
      } ${!issue.included_in_report ? "opacity-75 bg-muted/5" : ""}`}
      onClick={onSelect}
    >
      {/* Header */}
      <header className="p-3.5 pb-2.5 flex items-start justify-between gap-2 border-b border-line">
        <div className="flex flex-wrap items-center gap-1.5 min-w-0">
          <span
            className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded border uppercase ${severityBadgeClass}`}
          >
            {issue.severity}
          </span>
          <span className="text-xs font-mono font-medium text-ink bg-muted/20 px-2 py-0.5 rounded border border-line truncate max-w-[200px]">
            {issue.type}
          </span>

          {/* Curation state pill */}
          {issue.included_in_report ? (
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
              <Check size={10} />
              <span>In Report</span>
            </span>
          ) : (
            <span className="text-[10px] font-medium text-muted bg-muted/20 border border-line px-2 py-0.5 rounded-full flex items-center gap-1">
              <XCircle size={10} />
              <span>Excluded</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {location.page_number && onJumpToPage && (
            <button
              type="button"
              className="text-[11px] font-medium text-muted hover:text-ink px-2 py-1 rounded bg-muted/15 hover:bg-muted/30 transition-colors flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onJumpToPage(location.page_number!);
              }}
              title={`Jump to page ${location.page_number}`}
            >
              <MapPin size={11} className="text-sky-500" />
              <span>p. {location.page_number}</span>
            </button>
          )}

          <button
            type="button"
            className="p-1 text-muted hover:text-ink rounded transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            aria-label={isExpanded ? "Collapse finding details" : "Expand finding details"}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="p-3.5 space-y-3">
        {/* Message */}
        <p className="text-xs text-ink leading-relaxed">
          {issue.message}
        </p>

        {isExpanded && (
          <div className="space-y-3 pt-1">
            {/* Table Math Evidence */}
            {evidence.kind === "TABLE_MATH" && (
              <div className="p-2.5 rounded bg-muted/10 border border-line space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 font-medium text-muted text-[11px] uppercase tracking-wider">
                  <FileSpreadsheet size={13} className="text-sky-500" />
                  <span>Calculation Details</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                  <div>
                    <span className="text-muted text-[11px] block">Stated value:</span>
                    <span className="text-ink font-semibold">{String(evidence.stated_value ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-muted text-[11px] block">Computed sum:</span>
                    <span className="text-ink font-semibold">{String(evidence.computed_value ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-muted text-[11px] block">Discrepancy (delta):</span>
                    <span className="text-red-500 font-semibold">{String(evidence.delta ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-muted text-[11px] block">Allowed tolerance:</span>
                    <span className="text-muted">{String(evidence.tolerance ?? "0.01")}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Linguistic Evidence & Dictionary Action */}
            {evidence.kind === "LINGUISTIC" && (
              <div className="p-2.5 rounded bg-muted/10 border border-line space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted text-[11px] uppercase tracking-wider font-medium">
                    Linguistic Suggestion
                  </span>
                  {Boolean(evidence.original_text) && onAddToDictionary && (
                    <button
                      type="button"
                      className="text-[11px] text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddToDictionary(String(evidence.original_text));
                      }}
                    >
                      <BookOpen size={12} />
                      <span>Add &quot;{String(evidence.original_text)}&quot; to Dictionary</span>
                    </button>
                  )}
                </div>
                {Boolean(evidence.suggestion) && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted">Recommendation:</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                      {String(evidence.suggestion)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Reviewer Note Display / Inline Editor */}
            <div className="pt-2 border-t border-line">
              {isEditingNote ? (
                <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                  <label className="block text-[11px] font-medium text-muted">
                    Reviewer Note (appears in DOCX report and annotated PDF):
                  </label>
                  <textarea
                    className="w-full text-xs p-2 rounded border border-line bg-sunken text-ink focus:outline-none focus:border-sky-500 resize-y"
                    rows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add engineering clarification or reference..."
                    maxLength={4000}
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      className="button button-ghost btn-sm"
                      onClick={() => {
                        setNoteText(issue.reviewer_note ?? "");
                        setIsEditingNote(false);
                      }}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="button button-primary btn-sm"
                      onClick={() => void handleSaveNote()}
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? "Saving..." : "Save Note"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <span className="text-[11px] font-medium text-muted block mb-0.5">
                      Reviewer Note:
                    </span>
                    {issue.reviewer_note ? (
                      <p className="text-xs text-ink italic bg-muted/10 p-2 rounded border border-line">
                        &quot;{issue.reviewer_note}&quot;
                      </p>
                    ) : (
                      <span className="text-xs text-muted/70 italic">None attached.</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="text-[11px] text-sky-600 dark:text-sky-400 hover:underline shrink-0 mt-0.5"
                    onClick={(e) => {
                      e.stopPropagation();
                      setNoteText(issue.reviewer_note ?? "");
                      setIsEditingNote(true);
                    }}
                  >
                    {issue.reviewer_note ? "Edit Note" : "Add Note"}
                  </button>
                </div>
              )}
            </div>

            {/* Error banner */}
            {errorMessage && (
              <div className="p-2 rounded bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400 flex items-center gap-1.5">
                <AlertCircle size={14} className="shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Curation Action Button */}
            <div className="pt-2 border-t border-line flex items-center justify-between gap-2">
              <span className="text-[11px] text-muted">
                {issue.included_in_report
                  ? "Included in exported report"
                  : "Excluded from exported report"}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleToggleInclude();
                }}
                disabled={isSubmitting}
                className={`button btn-sm flex items-center gap-1.5 transition-colors ${
                  issue.included_in_report
                    ? "button-secondary text-muted hover:text-ink"
                    : "button-primary"
                }`}
              >
                {issue.included_in_report ? (
                  <>
                    <XCircle size={13} />
                    <span>Exclude from Report</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={13} />
                    <span>Include in Report</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
