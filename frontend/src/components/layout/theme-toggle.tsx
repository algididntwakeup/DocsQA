"use client";

import { useEffect, useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("matqc-theme-change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("matqc-theme-change", callback);
  };
}

function getSnapshot(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  const val = localStorage.getItem("matqc-theme");
  return val === "light" ? "light" : "dark";
}

function getServerSnapshot(): "dark" | "light" {
  return "dark";
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "light") {
      document.documentElement.classList.add("light");
      document.body.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
      document.body.classList.remove("light");
    }
  }, [theme]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    localStorage.setItem("matqc-theme", next);
    window.dispatchEvent(new Event("matqc-theme-change"));
  };

  return (
    <button
      type="button"
      className="icon-button theme-toggle-btn"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}
