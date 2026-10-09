import type { ErrorInfo } from "react";

export interface ClientErrorInfo {
  componentStack?: string | null;
}

interface ClientErrorPayload {
  message: string;
  stack: string | null;
  component_stack: string | null;
  url: string | null;
  user_agent: string | null;
  correlation_id: string;
  timestamp: string;
}

const correlationIds = new WeakMap<Error, string>();
const reportedErrors = new WeakSet<Error>();

function newCorrelationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `client-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function errorCorrelationId(error: Error): string {
  const providedId = (error as Error & { correlationId?: unknown }).correlationId;
  if (typeof providedId === "string" && providedId.length > 0) return providedId;

  const digest = (error as Error & { digest?: unknown }).digest;
  if (typeof digest === "string" && digest.length > 0) return digest;

  return correlationIds.get(error) ?? "";
}

export function getErrorCorrelationId(error: Error): string {
  return errorCorrelationId(error);
}

function clientLogUrl(): string {
  const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");
  if (!configuredBase) return "/api/v1/logs/client";
  const apiBase = configuredBase.endsWith("/api/v1") ? configuredBase : `${configuredBase}/api/v1`;
  return `${apiBase}/logs/client`;
}

function enqueueReport(payload: ClientErrorPayload): void {
  if (typeof window === "undefined") return;

  const url = clientLogUrl();
  const body = JSON.stringify(payload);
  try {
    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      const queued = navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
      if (queued) return;
    }
  } catch {
    // Fall back to keepalive fetch when the browser cannot queue a beacon.
  }

  try {
    void fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": payload.correlation_id,
      },
      body,
      credentials: "include",
      keepalive: true,
      cache: "no-store",
    }).catch(() => undefined);
  } catch {
    // Error reporting must never create a second UI error.
  }
}

function normalizeError(error: unknown): Error {
  if (error instanceof Error) return error;
  if (typeof error === "string") return new Error(error);
  return new Error("An unknown client error occurred.");
}

export const logger = {
  error(
    error: unknown,
    errorInfo?: ErrorInfo | ClientErrorInfo,
    preferredCorrelationId?: string,
  ): string {
    const normalizedError = normalizeError(error);
    const correlationId =
      errorCorrelationId(normalizedError) || preferredCorrelationId || newCorrelationId();
    correlationIds.set(normalizedError, correlationId);

    if (reportedErrors.has(normalizedError)) return correlationId;
    reportedErrors.add(normalizedError);

    const componentStack = errorInfo?.componentStack ?? null;
    const payload: ClientErrorPayload = {
      message: normalizedError.message,
      stack: normalizedError.stack ?? null,
      component_stack: componentStack,
      url:
        typeof window === "undefined"
          ? null
          : `${window.location.origin}${window.location.pathname}`,
      user_agent: typeof navigator === "undefined" ? null : navigator.userAgent,
      correlation_id: correlationId,
      timestamp: new Date().toISOString(),
    };
    enqueueReport(payload);
    return correlationId;
  },
};
