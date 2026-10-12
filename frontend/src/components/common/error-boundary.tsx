"use client";

import { Component, useEffect, useId, useState, type ErrorInfo, type ReactNode } from "react";
import { Check, Copy, RefreshCw, TriangleAlert } from "lucide-react";
import { getErrorCorrelationId, logger } from "@/lib/logger";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
  correlationId: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null, correlationId: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error, correlationId: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ correlationId: logger.error(error, errorInfo) });
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <ErrorFallback
          error={this.state.error}
          correlationId={this.state.correlationId ?? undefined}
          reportOnMount={false}
        />
      );
    }
    return this.props.children;
  }
}

interface ErrorFallbackProps {
  error: Error;
  correlationId?: string;
  onReload?: () => void;
  reportOnMount?: boolean;
}

export function ErrorFallback({
  error,
  correlationId: suppliedCorrelationId,
  onReload,
  reportOnMount = true,
}: ErrorFallbackProps) {
  const [copied, setCopied] = useState(false);
  const reactId = useId().replace(/:/g, "");
  const correlationId = suppliedCorrelationId || getErrorCorrelationId(error) || `client-${reactId}`;

  useEffect(() => {
    if (reportOnMount) logger.error(error, undefined, correlationId);
  }, [correlationId, error, reportOnMount]);

  async function copyCorrelationId() {
    try {
      if (!correlationId) return;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(correlationId);
        setCopied(true);
        return;
      }
    } catch {
      // Try the document-based fallback below.
    }

    const input = document.createElement("textarea");
    input.value = correlationId;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    const copiedToClipboard = document.execCommand("copy");
    input.remove();
    setCopied(copiedToClipboard);
  }

  return (
    <main className="flex min-h-[60vh] items-center justify-center bg-background px-5 py-12 text-foreground">
      <section
        aria-labelledby="technical-error-title"
        className="w-full max-w-lg rounded-2xl border border-border bg-card p-8 text-center shadow-xl sm:p-10"
        role="alert"
      >
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <TriangleAlert aria-hidden="true" size={28} />
        </div>
        <h1 id="technical-error-title" className="mt-5 text-xl font-bold tracking-tight">
          Terjadi Kendala Teknis
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Halaman ini mengalami kendala. Muat ulang halaman atau kirim kode pelacak berikut ke tim pengembang.
        </p>
        <p className="mt-5 rounded-lg bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
          Kode pelacak: <span className="select-all text-foreground">{correlationId}</span>
        </p>
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
            onClick={onReload ?? (() => window.location.reload())}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={16} />
            Muat Ulang Halaman
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-semibold transition hover:bg-muted"
            onClick={() => void copyCorrelationId()}
            disabled={!correlationId}
            type="button"
          >
            {copied ? <Check aria-hidden="true" size={16} /> : <Copy aria-hidden="true" size={16} />}
            {copied ? "Kode Pelacak Disalin" : "Salin Kode Pelacak"}
          </button>
        </div>
      </section>
    </main>
  );
}
