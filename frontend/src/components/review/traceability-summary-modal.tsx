"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  X,
  ShieldCheck,
  ShieldAlert,
  BarChart3,
} from "lucide-react";
import { getTraceabilitySummary, type TraceabilitySummary } from "@/lib/api";

interface TraceabilitySummaryModalProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function TraceabilitySummaryModal({
  documentId,
  isOpen,
  onClose,
}: TraceabilitySummaryModalProps) {
  const [summary, setSummary] = useState<TraceabilitySummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let active = true;

    getTraceabilitySummary(documentId)
      .then((data) => {
        if (active) {
          setSummary(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load traceability summary");
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [documentId, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="traceability-summary-title"
    >
      <div
        className="modal-container summary-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <ShieldCheck className="modal-icon text-blue-500" size={22} />
            <div>
              <h2 id="traceability-summary-title" className="modal-title">
                Traceability & Compliance Audit Summary
              </h2>
              <p className="modal-subtitle">
                Verification readiness per PRD §3.2 and Section A-10 acceptance gates.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close summary modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {isLoading ? (
            <div className="modal-loading-state">
              <div className="loading-spinner" />
              <p>Aggregating traceability verification data...</p>
            </div>
          ) : error ? (
            <div className="modal-error-state" role="alert">
              <p>{error}</p>
            </div>
          ) : !summary ? null : (() => {
            const totalFindings = Object.values(summary.counts_by_type).reduce((a, b) => a + b, 0);
            const openFindings = summary.unresolved_count;
            const isReady = openFindings === 0;

            return (
              <div className="summary-content">
                {/* Readiness Banner */}
                <div
                  className={`summary-readiness-banner ${
                    isReady ? "readiness-ready" : "readiness-pending"
                  }`}
                >
                  {isReady ? (
                    <>
                      <CheckCircle2 size={24} className="text-green-500" />
                      <div>
                        <strong>Document Ready for Final Sign-Off</strong>
                        <p>
                          All {totalFindings} traceability findings have been resolved (accepted
                          or justified exception granted).
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <ShieldAlert size={24} className="text-amber-500" />
                      <div>
                        <strong>Verification Incomplete: {openFindings} Open Finding(s)</strong>
                        <p>
                          Traceability findings require explicit individual human review before final
                          lead approval.
                        </p>
                      </div>
                    </>
                  )}
                </div>

                {/* KPI Grid */}
                <div className="summary-kpis">
                  <div className="kpi-card">
                    <span className="kpi-card-title">Total Traceability Findings</span>
                    <span className="kpi-card-val">{totalFindings}</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-card-title">Open / Unresolved</span>
                    <span
                      className={`kpi-card-val ${
                        openFindings > 0 ? "text-amber-600 font-bold" : "text-green-600"
                      }`}
                    >
                      {openFindings}
                    </span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-card-title">Critical Severity</span>
                    <span
                      className={`kpi-card-val ${
                        summary.critical_count > 0 ? "text-rose-500 font-bold" : "text-slate-400"
                      }`}
                    >
                      {summary.critical_count}
                    </span>
                  </div>
                </div>

                {/* Breakdown by Rule */}
                <div className="summary-section">
                  <h3 className="section-title">
                    <BarChart3 size={16} /> Findings by Verification Type
                  </h3>
                  <div className="summary-table-wrap">
                    <table className="summary-table">
                      <thead>
                        <tr>
                          <th>Finding Type</th>
                          <th className="text-right">Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.keys(summary.counts_by_type).length === 0 ? (
                          <tr>
                            <td colSpan={2} className="text-muted text-center">
                              No traceability findings identified.
                            </td>
                          </tr>
                        ) : (
                          Object.entries(summary.counts_by_type).map(([rule, count]) => (
                            <tr key={rule}>
                              <td className="font-mono text-sm">{rule}</td>
                              <td className="text-right font-semibold">{count}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Severity Breakdown */}
                <div className="summary-section">
                  <h3 className="section-title">Findings by Severity</h3>
                  <div className="summary-table-wrap">
                    <table className="summary-table">
                      <thead>
                        <tr>
                          <th>Severity</th>
                          <th className="text-right">Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(summary.counts_by_severity).map(([sev, count]) => (
                          <tr key={sev}>
                            <td>{sev}</td>
                            <td className="text-right font-semibold">{count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
