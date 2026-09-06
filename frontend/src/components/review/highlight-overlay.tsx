"use client";

import type { components } from "@/lib/api-schema";
import { getIssueLocation, type IssueItem } from "@/lib/api";

export type BoundingBox = components["schemas"]["BoundingBox"];

export interface HighlightBoxItem {
  box: BoundingBox;
  label?: string;
  variant?: "primary" | "operand" | "target" | "focus";
}

interface HighlightOverlayProps {
  highlights?: HighlightBoxItem[];
  pageIndex?: number;
  activeIssue?: IssueItem | null;
  currentPage?: number;
  onSelect?: () => void;
}

export function HighlightOverlay({
  highlights = [],
  pageIndex,
  activeIssue,
  currentPage,
  onSelect,
}: HighlightOverlayProps) {
  // If activeIssue and currentPage are supplied, derive highlights
  const effectiveHighlights: HighlightBoxItem[] = [...(highlights ?? [])];
  const effectivePageIndex =
    pageIndex !== undefined ? pageIndex : currentPage !== undefined ? currentPage - 1 : 0;

  if (activeIssue && currentPage !== undefined) {
    const loc = getIssueLocation(activeIssue);
    const issuePage = loc.page_number;
    const bbox = loc.bbox;

    // Check if issue is on current page
    const isOnPage =
      issuePage === currentPage ||
      (bbox?.page_index !== undefined && bbox.page_index === effectivePageIndex);

    if (isOnPage && bbox) {
      effectiveHighlights.push({
        box: {
          ...bbox,
          page_index: bbox.page_index ?? effectivePageIndex,
        },
        label: activeIssue.type,
        variant: "primary",
      });
    }

    // Check operands and dual-locations in evidence
    const ev = activeIssue.evidence;
    if (ev && ev.kind === "TABLE_MATH" && Array.isArray(ev.operand_locations)) {
      for (const opBox of ev.operand_locations) {
        if (opBox.page_index === effectivePageIndex) {
          effectiveHighlights.push({
            box: opBox,
            label: "Operand",
            variant: "operand",
          });
        }
      }
    } else if (ev && ev.kind === "REFERENCE_DRIFT") {
      if (ev.target_location && ev.target_location.page_index === effectivePageIndex) {
        effectiveHighlights.push({
          box: ev.target_location,
          label: "Target",
          variant: "target",
        });
      }
    } else if (ev && ev.kind === "STANDARD") {
      if (ev.bibliography_location && ev.bibliography_location.page_index === effectivePageIndex) {
        effectiveHighlights.push({
          box: ev.bibliography_location,
          label: "Bibliography",
          variant: "target",
        });
      }
    }
  }

  const pageHighlights = effectiveHighlights.filter(
    (h) => h.box.page_index === effectivePageIndex
  );

  if (pageHighlights.length === 0) {
    return null;
  }

  return (
    <div
      className="absolute inset-0 pointer-events-none highlight-container"
      style={{ width: "100%", height: "100%" }}
      data-testid={`highlight-overlay-page-${effectivePageIndex + 1}`}
    >
      {pageHighlights.map((item, index) => {
        const { box, label, variant = "primary" } = item;
        const leftPct = (box.x0 / box.page_width) * 100;
        const topPct = (box.y0 / box.page_height) * 100;
        const widthPct = Math.max(((box.x1 - box.x0) / box.page_width) * 100, 1);
        const heightPct = Math.max(((box.y1 - box.y0) / box.page_height) * 100, 1);

        let variantClass = "highlight-primary border-red-500 bg-red-500/20";
        if (variant === "operand") {
          variantClass = "highlight-operand border-amber-400 bg-amber-400/20 border-dashed";
        } else if (variant === "target") {
          variantClass = "highlight-target border-sky-400 bg-sky-400/25";
        } else if (variant === "focus") {
          variantClass = "highlight-focus border-cyan-400 bg-cyan-400/30 ring-2 ring-cyan-300";
        }

        return (
          <div
            key={`highlight-${effectivePageIndex}-${index}`}
            className={`absolute border-2 rounded transition-all duration-150 pointer-events-auto cursor-pointer highlight-box ${variantClass}`}
            style={{
              left: `${leftPct}%`,
              top: `${topPct}%`,
              width: `${widthPct}%`,
              height: `${heightPct}%`,
            }}
            onClick={onSelect}
            title={label ? `${label} (Finding Anchor)` : "Finding Anchor"}
          >
            {label && (
              <span className="absolute -top-4 left-0 bg-[#ef4444] text-[10px] text-white font-mono px-1 py-0.2 rounded shadow whitespace-nowrap highlight-tag">
                {label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
