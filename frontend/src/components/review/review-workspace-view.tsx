"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, RotateCw } from "lucide-react";
import { getDocument, listDocumentIssues, ApiError, type DocumentItem, type IssueItem } from "@/lib/api";
import { SplitScreenViewer } from "./split-screen-viewer";

export function ReviewWorkspaceView({ id }: { id: string }) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        const [docData, issuesData] = await Promise.all([
          getDocument(id),
          listDocumentIssues(id),
        ]);
        if (active) {
          setDocument(docData);
          setIssues(issuesData.issues);
          setError(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : err instanceof Error
              ? err.message
              : "Could not load review workspace."
          );
          setIsLoading(false);
        }
      }
    };

    void fetchData();

    return () => {
      active = false;
    };
  }, [id, reloadKey]);

  if (isLoading) {
    return (
      <div className="panel loading-state" role="status">
        <div className="loading-spinner" />
        <p>Loading document and QA inspection telemetry...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="review-error-container">
        <Link className="back-link" href={`/documents/${id}`}>
          <ArrowLeft size={15} /> Back to inspection status
        </Link>
        <div className="alert alert-error" role="alert">
          <AlertTriangle />
          <div>
            <strong>Unable to initialize review workspace</strong>
            <p>{error ?? "Document not found."}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setIsLoading(true);
              setReloadKey((k) => k + 1);
            }}
          >
            <RotateCw size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return <SplitScreenViewer document={document} initialIssues={issues} />;
}
