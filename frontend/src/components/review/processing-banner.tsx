"use client";

import { LoaderCircle } from "lucide-react";

interface ProcessingBannerProps {
  progressPct: number;
  currentStage: string;
}

export function ProcessingBanner({ progressPct, currentStage }: ProcessingBannerProps) {
  const boundedProgress = Math.min(99, Math.max(0, Math.round(progressPct)));

  return (
    <section
      className="shrink-0 rounded-xl border border-primary/20 bg-accent/70 px-4 py-3 text-accent-foreground shadow-sm"
      role="status"
      aria-live="polite"
      aria-label="Document analysis progress"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <p className="text-xs font-bold">Analisis dokumen sedang berjalan</p>
            <p className="truncate text-[11px] text-muted-foreground">{currentStage}</p>
          </div>
        </div>
        <span className="shrink-0 text-xs font-bold tabular-nums" aria-hidden="true">
          {boundedProgress}%
        </span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-background/70"
        role="progressbar"
        aria-label="Document analysis progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={boundedProgress}
        aria-valuetext={`${boundedProgress}% — ${currentStage}`}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-700 ease-out"
          style={{ width: `${boundedProgress}%` }}
        />
      </div>
    </section>
  );
}
