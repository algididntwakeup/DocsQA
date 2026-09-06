"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Plus,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import {
  approveDictionaryTerm,
  createDictionaryTerm,
  listDictionaryTerms,
  type DictionaryTermItem,
} from "@/lib/api";

interface DictionaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTerm?: string;
  onTermCreated?: (term: string) => void;
}

export function DictionaryModal({
  isOpen,
  onClose,
  initialTerm,
  onTermCreated,
}: DictionaryModalProps) {
  const [terms, setTerms] = useState<DictionaryTermItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"list" | "create">(initialTerm ? "create" : "list");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Form states
  const [newTerm, setNewTerm] = useState<string>(initialTerm ?? "");
  const [newScope, setNewScope] = useState<string>("organization");
  const [newRationale, setNewRationale] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null
  );

  // Sync state from prop changes during render per React 19 guidelines
  const [prevInitialTerm, setPrevInitialTerm] = useState(initialTerm);
  if (initialTerm !== prevInitialTerm) {
    setPrevInitialTerm(initialTerm);
    if (initialTerm) {
      setNewTerm(initialTerm);
      setActiveTab("create");
    }
  }

  const loadTerms = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await listDictionaryTerms(undefined, statusFilter === "all" ? undefined : statusFilter);
      setTerms(res.terms);
    } catch {
      setFeedback({ type: "error", text: "Failed to load dictionary terms." });
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (!isOpen) return;
    let isCancelled = false;
    listDictionaryTerms(undefined, statusFilter === "all" ? undefined : statusFilter)
      .then((res) => {
        if (!isCancelled) {
          setTerms(res.terms);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setFeedback({ type: "error", text: "Failed to load dictionary terms." });
          setIsLoading(false);
        }
      });
    return () => {
      isCancelled = true;
    };
  }, [isOpen, statusFilter]);

  const handleCreateTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTerm.trim()) {
      setFeedback({ type: "error", text: "Term cannot be empty." });
      return;
    }
    setIsSubmitting(true);
    setFeedback(null);
    try {
      await createDictionaryTerm({
        term: newTerm.trim(),
        scope: newScope,
        rationale: newRationale.trim() || undefined,
      });
      setFeedback({
        type: "success",
        text: `Term '${newTerm.trim()}' added successfully.`,
      });
      onTermCreated?.(newTerm.trim());
      setNewTerm("");
      setNewRationale("");
      await loadTerms();
      setActiveTab("list");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add term";
      setFeedback({ type: "error", text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async (termId: string, status: "APPROVED" | "REJECTED") => {
    try {
      await approveDictionaryTerm(termId, {
        status,
        rationale: `Reviewed and set to ${status}`,
      });
      await loadTerms();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update term status";
      setFeedback({ type: "error", text: msg });
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dictionary-modal-title"
    >
      <div
        className="w-full max-w-2xl bg-panel border border-line rounded-xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-line bg-sunken">
          <div className="flex items-center gap-2.5">
            <BookOpen className="w-5 h-5 text-accent-soft" />
            <div>
              <h2 id="dictionary-modal-title" className="text-base font-bold text-ink">
                Governed Engineering Dictionary
              </h2>
              <p className="text-xs text-muted">
                Standard terminology, metallurgical grades, and project exemptions
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted hover:text-ink hover:bg-chip transition-colors"
            title="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between px-6 py-2 border-b border-line bg-panel-raised">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("list")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === "list"
                  ? "bg-chip text-accent-soft border border-accent/40 font-bold"
                  : "text-muted hover:text-ink"
              }`}
            >
              Approved & Pending Terms ({terms.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("create")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1 ${
                activeTab === "create"
                  ? "bg-chip text-accent-soft border border-accent/40 font-bold"
                  : "text-muted hover:text-ink"
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              Add Term
            </button>
          </div>

          {activeTab === "list" && (
            <div className="flex items-center gap-2">
              <label htmlFor="filter-status" className="text-xs text-muted">
                Status:
              </label>
              <select
                id="filter-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-panel border border-line rounded px-2 py-1 text-xs text-ink-soft focus:outline-none focus:border-accent"
              >
                <option value="all">All</option>
                <option value="APPROVED">Approved</option>
                <option value="PENDING">Pending</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>
          )}
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`mx-6 mt-3 p-2.5 rounded text-xs flex items-center gap-2 border ${
              feedback.type === "success"
                ? "bg-emerald-950/60 border-emerald-800/40 text-emerald-300"
                : "bg-red-950/60 border-red-800/40 text-red-300"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <XCircle className="w-4 h-4 shrink-0 text-red-400" />
            )}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {activeTab === "create" ? (
            <form onSubmit={handleCreateTerm} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Term / Specification Symbol *
                </label>
                <input
                  type="text"
                  required
                  value={newTerm}
                  onChange={(e) => setNewTerm(e.target.value)}
                  placeholder="e.g. Inconel625, UNS-N06625, ASTM-A516"
                  className="w-full bg-sunken border border-line rounded-lg px-3 py-2 text-sm text-ink placeholder-muted focus:outline-none focus:border-accent"
                />
                <span className="text-[11px] text-muted mt-1 block">
                  Once approved, this token will be whitelisted across spellcheck and linguistic audits.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Governance Scope *
                </label>
                <select
                  value={newScope}
                  onChange={(e) => setNewScope(e.target.value)}
                  className="w-full bg-sunken border border-line rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-accent"
                >
                  <option value="organization">Organization (Global Whitelist)</option>
                  <option value="project:default">Project Default</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Technical Rationale / Justification
                </label>
                <textarea
                  value={newRationale}
                  onChange={(e) => setNewRationale(e.target.value)}
                  placeholder="Provide engineering standard, alloy specification, or client contract reference..."
                  rows={3}
                  className="w-full bg-sunken border border-line rounded-lg px-3 py-2 text-sm text-ink placeholder-muted focus:outline-none focus:border-accent"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("list")}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-muted hover:text-ink transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-accent text-white hover:bg-accent-soft transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Plus className="w-4 h-4" />
                  {isSubmitting ? "Submitting..." : "Submit to Dictionary"}
                </button>
              </div>
            </form>
          ) : (
            <div>
              {isLoading ? (
                <div className="py-8 text-center text-xs text-muted">Loading terms...</div>
              ) : terms.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted">
                  No dictionary terms found matching filter.
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {terms.map((term) => (
                    <div
                      key={term.id}
                      className="bg-sunken p-3 rounded-lg border border-line flex items-center justify-between gap-3"
                    >
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sm text-ink">{term.term}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              term.status === "APPROVED"
                                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                                : term.status === "PENDING"
                                ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                            }`}
                          >
                            {term.status}
                          </span>
                          <span className="text-[11px] text-muted">[{term.scope}]</span>
                        </div>
                        {term.rationale && (
                          <div className="text-xs text-muted italic">{term.rationale}</div>
                        )}
                        <div className="text-[10px] text-muted">
                          Added {new Date(term.created_at).toLocaleDateString()}
                          {term.approved_by && ` â€¢ Approved by ${term.approved_by}`}
                        </div>
                      </div>

                      {term.status === "PENDING" && (
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleApprove(term.id, "APPROVED")}
                            className="p-1.5 rounded bg-emerald-700/60 hover:bg-emerald-600 text-ink text-xs transition-colors flex items-center gap-1"
                            title="Approve Term"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => handleApprove(term.id, "REJECTED")}
                            className="p-1.5 rounded bg-rose-700/60 hover:bg-rose-600 text-ink text-xs transition-colors"
                            title="Reject Term"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
