"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  History,
  User,
  X,
  ArrowRight,
  Filter,
} from "lucide-react";
import { listAuditEvents, type AuditEventItem } from "@/lib/api";
import { formatDate } from "@/lib/format";

interface AuditTrailModalProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function AuditTrailModal({ documentId, isOpen, onClose }: AuditTrailModalProps) {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("ALL");

  useEffect(() => {
    if (!isOpen) return;

    let active = true;

    listAuditEvents(documentId)
      .then((res) => {
        if (active) {
          setEvents(res.events);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load audit events");
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [documentId, isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredEvents = events.filter((ev) => {
    if (actionFilter === "ALL") return true;
    return ev.action === actionFilter;
  });

  const getActionBadgeClass = (action: string) => {
    switch (action) {
      case "DOCUMENT_DISPOSITION":
        return "audit-badge-document";
      case "ISSUE_DISPOSITION":
        return "audit-badge-disposition";
      case "ISSUE_DECISION":
        return "audit-badge-decision";
      case "BULK_DECISION":
        return "audit-badge-bulk";
      default:
        return "audit-badge-default";
    }
  };

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-modal-title"
    >
      <div
        className="modal-container audit-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <History className="modal-icon" size={20} />
            <div>
              <h2 id="audit-modal-title" className="modal-title">
                Document Audit Trail
              </h2>
              <p className="modal-subtitle">
                Immutable chronological log of all QA review decisions, lead dispositions, and approvals.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close audit trail"
          >
            <X size={18} />
          </button>
        </div>

        {/* Filter bar */}
        <div className="modal-filter-bar">
          <div className="filter-group">
            <Filter size={14} />
            <label htmlFor="audit-action-filter" className="sr-only">
              Filter by action
            </label>
            <select
              id="audit-action-filter"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="filter-select"
            >
              <option value="ALL">All Actions ({events.length})</option>
              <option value="ISSUE_DECISION">Decisions</option>
              <option value="ISSUE_DISPOSITION">Lead Dispositions</option>
              <option value="DOCUMENT_DISPOSITION">Document Dispositions</option>
              <option value="BULK_DECISION">Bulk Actions</option>
            </select>
          </div>
          <span className="audit-counter">
            Showing {filteredEvents.length} event{filteredEvents.length === 1 ? "" : "s"}
          </span>
        </div>

        {/* Content */}
        <div className="modal-body">
          {isLoading ? (
            <div className="modal-loading-state">
              <div className="loading-spinner" />
              <p>Retrieving immutable audit records...</p>
            </div>
          ) : error ? (
            <div className="modal-error-state" role="alert">
              <p>{error}</p>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsLoading(true);
                  setError(null);
                  listAuditEvents(documentId)
                    .then((res) => {
                      setEvents(res.events);
                      setIsLoading(false);
                    })
                    .catch((err: unknown) => {
                      setError(err instanceof Error ? err.message : "Failed to load audit events");
                      setIsLoading(false);
                    });
                }}
              >
                Retry
              </button>
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="modal-empty-state">
              <Clock size={32} className="empty-icon" />
              <p className="empty-title">No Audit Events Logged</p>
              <p className="empty-sub">
                No decisions or dispositions have been recorded for this document yet.
              </p>
            </div>
          ) : (
            <div className="audit-timeline">
              {filteredEvents.map((ev) => {
                const prevStatus = ev.previous_state?.status as string | undefined;
                const newStatus = ev.new_state?.status as string | undefined;
                const prevDisposition = ev.previous_state?.disposition as string | undefined;
                const newDisposition = ev.new_state?.disposition as string | undefined;

                return (
                  <div key={ev.id} className="timeline-entry">
                    <div className="timeline-marker" />
                    <div className="timeline-card">
                      <div className="timeline-header">
                        <span className={`audit-badge ${getActionBadgeClass(ev.action)}`}>
                          {ev.action.replace(/_/g, " ")}
                        </span>
                        <span className="timeline-time">{formatDate(ev.created_at)}</span>
                      </div>

                      <div className="timeline-actor">
                        <User size={13} />
                        <span className="actor-id">{ev.actor_id}</span>
                        <span className="actor-role">({ev.actor_role})</span>
                        {ev.issue_id && (
                          <span className="timeline-issue-ref">
                            Issue #{ev.issue_id.slice(0, 8)}
                          </span>
                        )}
                      </div>

                      {/* State transition if present */}
                      {(prevStatus || newStatus || prevDisposition || newDisposition) && (
                        <div className="timeline-transition">
                          {prevStatus && (
                            <span className="state-badge state-prev">{prevStatus}</span>
                          )}
                          {prevStatus && newStatus && (
                            <ArrowRight size={12} className="state-arrow" />
                          )}
                          {newStatus && (
                            <span className="state-badge state-new">{newStatus}</span>
                          )}

                          {newDisposition && (
                            <span className="state-badge state-disposition">
                              Disposition: {newDisposition}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Notes or Justification */}
                      {ev.notes && (
                        <div className="timeline-notes">
                          <p className="notes-label">Notes / Justification:</p>
                          <p className="notes-content">{ev.notes}</p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
