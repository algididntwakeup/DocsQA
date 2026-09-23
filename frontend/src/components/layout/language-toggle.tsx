"use client";

import { useLocale } from "./locale-provider";

export function LanguageToggle() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div
      className="inline-flex items-center rounded-lg border border-border bg-muted p-0.5 text-xs font-semibold text-muted-foreground"
      role="group"
      aria-label={t("toggleLanguage")}
    >
      <button
        type="button"
        className={`rounded-md px-2 py-0.5 text-[11px] transition-all ${
          locale === "en"
            ? "bg-card font-bold text-accent-foreground shadow-xs ring-1 ring-border/50"
            : "hover:text-foreground"
        }`}
        aria-pressed={locale === "en"}
        onClick={() => setLocale("en")}
      >
        EN
      </button>
      <button
        type="button"
        className={`rounded-md px-2 py-0.5 text-[11px] transition-all ${
          locale === "id"
            ? "bg-card font-bold text-accent-foreground shadow-xs ring-1 ring-border/50"
            : "hover:text-foreground"
        }`}
        aria-pressed={locale === "id"}
        onClick={() => setLocale("id")}
      >
        ID
      </button>
    </div>
  );
}
