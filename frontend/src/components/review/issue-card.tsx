"use client";

import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  Flag,
  Layers,
  MapPin,
  MessageSquare,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { getIssueLocation, type IssueItem, type IssueDecision, type IssueDisposition } from "@/lib/api";

interface IssueCardProps {
  issue: IssueItem;
  isSelected?: boolean;
  onSelect?: () => void;
  onDecide: (issueId: string, payload: IssueDecision) => Promise<void>;
  onDispose: (issueId: string, payload: IssueDisposition) => Promise<void>;
  onJumpToPage?: (page: number) => void;
}

export function IssueCard({
  issue,
  isSelected = false,
  onSelect,
  onDecide,
  onDispose,
  onJumpToPage,
}: IssueCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [comment, setComment] = useState<string>("");
  const [showCommentInput, setShowCommentInput] = useState<boolean>(false);
  const [justification, setJustification] = useState<string>("");
  const [showLeadControls, setShowLeadControls] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const evidence = (issue.evidence ?? {}) as Record<string, unknown>;
  const location = getIssueLocation(issue);

  const handleDecision = async (decision: "ACCEPTED" | "REJECTED" | "FLAGGED") => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await onDecide(issue.id, {
        decision,
        expected_version: issue.version,
        comment: comment.trim() || undefined,
        actor_id: "reviewer@local",
        actor_role: "QA_ENGINEER",
      });
      setShowCommentInput(false);
      setComment("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record decision";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisposition = async (disposition: "JUSTIFIED_EXCEPTION" | "REQUIRES_CORRECTION") => {
    if (!justification.trim()) {
      setErrorMessage("A justification note is required for lead disposition.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await onDispose(issue.id, {
        disposition,
        expected_version: issue.version,
        justification: justification.trim(),
        actor_id: "lead_reviewer@local",
        actor_role: "LEAD_REVIEWER",
      });
      setShowLeadControls(false);
      setJustification("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record disposition";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Severity style mapping
  const severityBadgeClass = {
    CRITICAL: "bg-red-500/15 text-red-400 border-red-500/30",
    HIGH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    MEDIUM: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    LOW: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    INFO: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  }[issue.severity] || "bg-slate-500/15 text-slate-300 border-slate-500/30";

  return (
    <div
      onClick={onSelect}
      className={`rounded border transition-all duration-150 p-4 ${
        isSelected
          ? "bg-[#131d36] border-[#38bdf8] ring-1 ring-[#38bdf8]/40 shadow-lg"
          : "bg-[#0f172a] border-[#1e293b] hover:border-[#334155] hover:bg-[#111c34]"
      }`}
    >
      {/* Header Bar */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${severityBadgeClass}`}
          >
            {issue.severity}
          </span>

          <span className="font-mono text-xs font-bold text-white tracking-wide rule-id-badge">
            {issue.type || (issue as unknown as { rule_id?: string }).rule_id}
          </span>

          {location.page_number && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (onJumpToPage && location.page_number) {
                  onJumpToPage(location.page_number);
                }
              }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#1e293b] text-[#94a3b8] hover:text-white text-[11px] font-mono hover:bg-[#2563eb]/20 page-jump-badge"
              title="Jump to page"
            >
              <MapPin className="w-3 h-3 text-[#38bdf8]" />
              p. {location.page_number}
            </button>
          )}

          <span className="font-mono text-[10px] text-[#64748b]">v{issue.version}</span>
        </div>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="text-[#94a3b8] hover:text-white p-0.5"
          title={isExpanded ? "Collapse" : "Expand"}
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Message */}
      <p className="mt-2 text-sm text-[#e2e8f0] font-normal leading-relaxed">
        {issue.message}
      </p>

      {/* Existing Decision / Disposition Status */}
      {(issue.decision || issue.disposition) && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2 pt-2 border-t border-[#1e293b]">
          {issue.decision && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
                issue.decision === "ACCEPTED"
                  ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800/40"
                  : issue.decision === "REJECTED"
                  ? "bg-rose-950/60 text-rose-300 border border-rose-800/40"
                  : "bg-amber-950/60 text-amber-300 border border-amber-800/40"
              }`}
            >
              {issue.decision === "ACCEPTED" && <CheckCircle2 className="w-3 h-3" />}
              {issue.decision === "REJECTED" && <XCircle className="w-3 h-3" />}
              {issue.decision === "FLAGGED" && <Flag className="w-3 h-3" />}
              QA: {issue.decision}
            </span>
          )}

          {issue.decision_comment && (
            <span className="text-xs text-[#94a3b8] italic">
              &ldquo;{issue.decision_comment}&rdquo;
            </span>
          )}

          {issue.disposition && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-purple-950/60 text-purple-300 border border-purple-800/40">
              <ShieldCheck className="w-3 h-3 text-purple-400" />
              Lead: {issue.disposition}
            </span>
          )}

          {issue.disposition_justification && (
            <span className="text-xs text-[#c084fc] italic">
              [{issue.disposition_justification}]
            </span>
          )}
        </div>
      )}

      {/* Error Alert */}
      {errorMessage && (
        <div className="mt-2.5 p-2 rounded bg-red-950/60 border border-red-800/40 text-xs text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Expandable Evidence & Controls */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-[#1e293b] flex flex-col gap-3">
          {/* Typed Evidence Details */}
          {(evidence.kind === "TABLE_MATH" || issue.type?.includes("TABLE_MATH") || evidence.stated_value !== undefined) && (
            <div className="bg-[#0b1326] p-2.5 rounded border border-[#1e293b] text-xs font-mono">
              <div className="text-[#89ceff] font-bold mb-1.5 flex items-center gap-1.5">
                <FileSpreadsheet className="w-3.5 h-3.5" />
                Table Math Reconciliation:
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[#cbd5e1]">
                <div>Stated Total: <span className="text-white font-bold">{String(evidence.stated_value)}</span></div>
                <div>Computed Sum: <span className="text-white font-bold">{String(evidence.computed_value)}</span></div>
                <div>Arithmetic Delta: <span className="text-red-400 font-bold">{String(evidence.delta)}</span></div>
                <div>Tolerance: <span className="text-[#94a3b8]">±{String(evidence.tolerance)}</span></div>
              </div>
            </div>
          )}

          {evidence.kind === "REFERENCE_DRIFT" && (
            <div className="bg-[#0b1326] p-2.5 rounded border border-[#1e293b] text-xs font-mono">
              <div className="text-[#89ceff] font-bold mb-1.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" />
                Pagination Drift Details:
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[#cbd5e1]">
                <div>Entry Label: <span className="text-white font-bold">{String(evidence.label)}</span></div>
                <div>Page Delta: <span className="text-red-400 font-bold">{String(evidence.page_delta)} pages</span></div>
                <div>
                  ToC Ref Page:{" "}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      const entryBox = evidence.entry_location as { page_index?: number } | undefined;
                      if (onJumpToPage && entryBox?.page_index !== undefined) {
                        onJumpToPage(entryBox.page_index + 1);
                      }
                    }}
                    className="text-[#38bdf8] underline hover:text-white"
                  >
                    {String(evidence.referenced_page_label)}
                  </button>
                </div>
                <div>
                  Actual Body Page:{" "}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      const targetBox = evidence.target_location as { page_index?: number } | undefined;
                      if (onJumpToPage && targetBox?.page_index !== undefined) {
                        onJumpToPage(targetBox.page_index + 1);
                      }
                    }}
                    className="text-[#38bdf8] underline hover:text-white"
                  >
                    {String(evidence.actual_page_label)}
                  </button>
                </div>
              </div>
            </div>
          )}

          {evidence.kind === "REVISION" && (
            <div className="bg-[#0b1326] p-2.5 rounded border border-[#1e293b] text-xs font-mono">
              <div className="text-[#89ceff] font-bold mb-1.5">Three-Way Revision Sync:</div>
              <div className="flex flex-col gap-1 text-[#cbd5e1]">
                <div>Filename Rev: <span className="text-white">{String(evidence.filename_revision ?? "N/A")}</span></div>
                <div>Cover Page Rev: <span className="text-white">{String(evidence.cover_revision ?? "N/A")}</span></div>
                <div>Revision Sheet Rev: <span className="text-white">{String(evidence.revision_sheet_revision ?? "N/A")}</span></div>
              </div>
            </div>
          )}

          {evidence.kind === "STANDARD" && (
            <div className="bg-[#0b1326] p-2.5 rounded border border-[#1e293b] text-xs font-mono">
              <div className="text-[#89ceff] font-bold mb-1.5">Standard & Code Citation:</div>
              <div className="flex flex-col gap-1 text-[#cbd5e1]">
                <div>Standard: <span className="text-white font-bold">{String(evidence.cited_standard)}</span></div>
                <div>Body Year: <span className="text-white">{String(evidence.body_edition_year ?? "Not specified")}</span></div>
                <div>Bibliography Year: <span className="text-white">{String(evidence.bibliography_edition_year ?? "Not in bibliography")}</span></div>
              </div>
            </div>
          )}

          {evidence.kind === "LINGUISTIC" && Boolean(evidence.suggestion) && (
            <div className="bg-[#0b1326] p-2 rounded border border-[#1e293b] text-xs font-mono">
              <span className="text-[#94a3b8]">Suggested Replacement: </span>
              <span className="text-emerald-400 font-bold">{String(evidence.suggestion)}</span>
            </div>
          )}

          {evidence.kind === "STAGE_FAILURE" && (
            <div className="bg-red-950/40 p-2.5 rounded border border-red-800/40 text-xs font-mono text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
              <div>
                Stage <strong>{String(evidence.stage)}</strong> failed with error code{" "}
                <strong>{String(evidence.error_code)}</strong>.
              </div>
            </div>
          )}

          {/* QA Decision Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDecision("ACCEPTED");
                }}
                className="px-2.5 py-1 rounded bg-emerald-700/70 hover:bg-emerald-600 text-white text-xs font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                title="Accept finding"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Accept
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDecision("REJECTED");
                }}
                className="px-2.5 py-1 rounded bg-rose-700/70 hover:bg-rose-600 text-white text-xs font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                title="Reject finding"
              >
                <XCircle className="w-3.5 h-3.5" />
                Reject
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDecision("FLAGGED");
                }}
                className="px-2.5 py-1 rounded bg-amber-700/70 hover:bg-amber-600 text-white text-xs font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                title="Flag for lead review"
              >
                <Flag className="w-3.5 h-3.5" />
                Flag
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowCommentInput(!showCommentInput);
                }}
                className="p-1 rounded text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                title="Add reviewer comment"
              >
                <MessageSquare className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Lead Reviewer Toggle */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowLeadControls(!showLeadControls);
              }}
              className="text-[11px] font-mono text-[#c084fc] hover:underline flex items-center gap-1"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Lead Disposition
            </button>
          </div>

          {/* Comment Input Drawer */}
          {showCommentInput && (
            <div
              className="mt-1 flex flex-col gap-1.5"
              onClick={(e) => e.stopPropagation()}
            >
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Optional reviewer notes or justification..."
                className="w-full text-xs p-2 rounded bg-[#0b1326] border border-[#1e293b] text-white placeholder-[#64748b] focus:outline-none focus:border-[#2563eb]"
                rows={2}
              />
            </div>
          )}

          {/* Lead Reviewer Controls */}
          {showLeadControls && (
            <div
              className="mt-2 p-2.5 rounded bg-[#19112e] border border-purple-900/50 flex flex-col gap-2"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-300">
                <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                Lead Reviewer Compliance Override:
              </div>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Regulatory justification / audit notes (e.g. NCR reference, client waiver, verified source data)..."
                className="w-full text-xs p-2 rounded bg-[#0b1326] border border-purple-900/60 text-white placeholder-purple-400/40 focus:outline-none focus:border-purple-500"
                rows={2}
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleDisposition("JUSTIFIED_EXCEPTION")}
                  className="px-2.5 py-1 rounded bg-purple-700 hover:bg-purple-600 text-white text-xs font-medium disabled:opacity-40"
                >
                  Justified Exception
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleDisposition("REQUIRES_CORRECTION")}
                  className="px-2.5 py-1 rounded bg-rose-800 hover:bg-rose-700 text-white text-xs font-medium disabled:opacity-40"
                >
                  Requires Correction
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
