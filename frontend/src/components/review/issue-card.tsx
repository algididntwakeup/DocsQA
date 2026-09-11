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

  const severityBadgeClass: Record<string, string> = {
    BLOCKER: "bg-rose-100 text-rose-800 border-rose-200 font-extrabold",
    CRITICAL: "bg-rose-50 text-rose-700 border-rose-200",
    MAJOR: "bg-amber-50 text-amber-700 border-amber-200",
    MINOR: "bg-slate-100 text-slate-700 border-slate-200",
    INFO: "bg-blue-50 text-blue-700 border-blue-200",
    HIGH: "bg-amber-50 text-amber-700 border-amber-200",
    MEDIUM: "bg-slate-100 text-slate-700 border-slate-200",
    LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  const badgeStyle = severityBadgeClass[issue.severity] ?? "bg-slate-100 text-slate-700 border-slate-200";

  return (
    <article
      data-issue-id={issue.id}
      className={`rounded-xl border transition-all duration-150 ${
        isSelected
          ? "border-blue-600 bg-white ring-2 ring-blue-500/20 shadow-xs"
          : "border-slate-200 bg-white hover:border-slate-300"
      } ${!issue.included_in_report ? "opacity-75 bg-slate-50/50" : ""}`}
      onClick={onSelect}
    >
      {/* Header */}
      <header className="flex items-start justify-between gap-2 border-b border-slate-100 p-3">
        <div className="flex flex-wrap items-center gap-1.5 min-w-0">
          <span
            className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded border uppercase ${badgeStyle}`}
          >
            {issue.severity}
          </span>
          <span className="text-xs font-mono font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 truncate max-w-[200px]">
            {issue.type}
          </span>

          {/* Curation state pill */}
          {issue.included_in_report ? (
            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
              <Check size={10} />
              <span>In Report</span>
            </span>
          ) : (
            <span className="text-[10px] font-medium text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full flex items-center gap-1">
              <XCircle size={10} />
              <span>Excluded</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {location.page_number && onJumpToPage && (
            <button
              type="button"
              className="text-[11px] font-semibold text-slate-600 hover:text-slate-900 px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 transition-colors flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onJumpToPage(location.page_number!);
              }}
              title={`Jump to page ${location.page_number}`}
            >
              <MapPin size={11} className="text-blue-600" />
              <span>p. {location.page_number}</span>
            </button>
          )}

          <button
            type="button"
            className="p-1 text-slate-400 hover:text-slate-600 rounded transition-colors"
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
      <div className="p-3 space-y-2.5">
        {/* Message */}
        <p className="text-xs text-slate-800 leading-relaxed font-medium">
          {issue.message}
        </p>

        {isExpanded && (
          <div className="space-y-2.5 pt-1">
            {/* Table Math Evidence */}
            {evidence.kind === "TABLE_MATH" && (
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-600 text-[10px] uppercase tracking-wider">
                  <FileSpreadsheet size={13} className="text-blue-600" />
                  <span>Calculation Details</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                  <div>
                    <span className="text-slate-400 text-[10px] block">Stated value:</span>
                    <span className="text-slate-800 font-semibold">{String(evidence.stated_value ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] block">Computed sum:</span>
                    <span className="text-slate-800 font-semibold">{String(evidence.computed_value ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] block">Discrepancy (delta):</span>
                    <span className="text-rose-600 font-semibold">{String(evidence.delta ?? "—")}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] block">Allowed tolerance:</span>
                    <span className="text-slate-500">{String(evidence.tolerance ?? "0.01")}</span>
                  </div>
                </div>
              </div>
            )}

            {evidence.kind === "LAYOUT" && (
              <div className="p-2.5 rounded-lg bg-sky-50/60 border border-sky-200 space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-sky-800 text-[10px] uppercase tracking-wider">
                  <MapPin size={13} />
                  <span>Layout Inspection</span>
                </div>
                <p className="text-slate-700"><span className="text-slate-500">Anomaly:</span> {String(evidence.anomaly_type ?? "—")}</p>
                {Boolean(evidence.snippet) && (
                  <p className="rounded bg-white border border-slate-200 p-2 font-mono text-[11px] text-slate-800 whitespace-pre-wrap">
                    {String(evidence.snippet)}
                  </p>
                )}
                {Boolean(evidence.suggested_fix) && (
                  <p className="text-slate-700"><span className="text-slate-500">Suggested fix:</span> {String(evidence.suggested_fix)}</p>
                )}
              </div>
            )}

            {evidence.kind === "BUDINSKI" && (
              <div className="p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-200 space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-indigo-800 text-[10px] uppercase tracking-wider">
                  <CheckCircle2 size={13} />
                  <span>Technical Writing Rule Audit {evidence.rule_number ? `· ${String(evidence.rule_number)}` : ""}</span>
                </div>
                {Boolean(evidence.measure) && <p className="text-slate-700"><span className="text-slate-500 font-medium">Measure:</span> {String(evidence.measure)}</p>}
                {Boolean(evidence.where_location) && <p className="text-slate-700"><span className="text-slate-500 font-medium">Where:</span> {String(evidence.where_location)}</p>}
                {Boolean(evidence.what_it_says) && <p className="text-slate-700"><span className="text-slate-500 font-medium">Standard says:</span> {String(evidence.what_it_says)}</p>}
                {Boolean(evidence.what_body_has) && <p className="text-slate-700"><span className="text-slate-500 font-medium">Document has:</span> {String(evidence.what_body_has)}</p>}
                {Boolean(evidence.what_would_fix_it) && <p className="text-slate-700"><span className="text-slate-500 font-medium">Fix:</span> {String(evidence.what_would_fix_it)}</p>}
              </div>
            )}

            {typeof evidence.snippet === "string" && evidence.snippet && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs">
                <span className="block mb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">Evidence excerpt</span>
                <p className="text-slate-700">{evidence.snippet}</p>
              </div>
            )}
            {typeof evidence.suggested_fix === "string" && evidence.suggested_fix && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-2.5 text-xs">
                <span className="block mb-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700">Recommended fix</span>
                <p className="text-slate-800">{evidence.suggested_fix}</p>
              </div>
            )}

            {/* Linguistic Evidence & Dictionary Action */}
            {evidence.kind === "LINGUISTIC" && (
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider font-bold">
                    Linguistic Suggestion
                  </span>
                  {Boolean(evidence.original_text) && onAddToDictionary && (
                    <button
                      type="button"
                      className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 font-semibold"
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
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500">Recommendation:</span>
                    <span className="text-emerald-700 font-semibold">
                      {String(evidence.suggestion)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Reviewer Note Display / Inline Editor */}
            <div className="pt-2 border-t border-slate-100">
              {isEditingNote ? (
                <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                  <label className="block text-[11px] font-semibold text-slate-600">
                    Reviewer Note:
                  </label>
                  <textarea
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-blue-500 resize-y"
                    rows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add engineering clarification or reference..."
                    maxLength={4000}
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
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
                      className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
                      onClick={() => void handleSaveNote()}
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? "Saving..." : "Save Note"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2 text-xs">
                  <div className="min-w-0">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-0.5">
                      Reviewer Note:
                    </span>
                    {issue.reviewer_note ? (
                      <p className="text-xs text-slate-800 italic bg-slate-50 p-2 rounded-lg border border-slate-200">
                        &quot;{issue.reviewer_note}&quot;
                      </p>
                    ) : (
                      <span className="text-xs text-slate-400 italic">None attached.</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="text-[11px] font-semibold text-blue-600 hover:underline shrink-0 mt-0.5"
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
              <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-1.5">
                <AlertCircle size={14} className="shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Curation Action Button */}
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
              <span className="text-[11px] text-slate-500">
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
                aria-label={issue.included_in_report ? "Exclude from Report" : "Include in Report"}
                className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                  issue.included_in_report
                    ? "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {issue.included_in_report ? (
                  <>
                    <XCircle size={13} className="text-slate-400" />
                    <span>Ignore finding</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={13} />
                    <span>Accept finding</span>
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
