"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { ProjectViewMode } from "@/types/project";

const STORAGE_KEY = "prism_project_view_mode";
const CHANGE_EVENT = "prism-project-view-mode-change";
let fallbackMode: ProjectViewMode = "table";

function getSnapshot(): ProjectViewMode {
  if (typeof window === "undefined") return "table";

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "grid" || stored === "table" ? stored : "table";
  } catch {
    // Keep the in-memory default when browser storage is unavailable.
    return fallbackMode;
  }
}

function getServerSnapshot(): ProjectViewMode {
  return "table";
}

function subscribe(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(CHANGE_EVENT, onStoreChange);
  };
}

export function useViewMode(): [ProjectViewMode, (mode: ProjectViewMode) => void] {
  const viewMode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const setViewMode = useCallback((mode: ProjectViewMode) => {
    fallbackMode = mode;
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // The selected mode still works for this session if storage is disabled.
    }
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, []);

  return [viewMode, setViewMode];
}
