"use client";

import { useLocale } from "./locale-provider";

export function LanguageToggle() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div
      className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs font-semibold text-slate-600"
      role="group"
      aria-label={t("toggleLanguage")}
    >
      <button
        type="button"
        className={`rounded-md px-2 py-0.5 text-[11px] transition-all ${
          locale === "en"
            ? "bg-white font-bold text-blue-600 shadow-xs ring-1 ring-slate-200/50"
            : "hover:text-slate-900"
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
            ? "bg-white font-bold text-blue-600 shadow-xs ring-1 ring-slate-200/50"
            : "hover:text-slate-900"
        }`}
        aria-pressed={locale === "id"}
        onClick={() => setLocale("id")}
      >
        ID
      </button>
    </div>
  );
}
