"use client";

import { useLocale } from "./locale-provider";

export function LanguageToggle() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div className="flex items-center gap-1" role="group" aria-label={t("toggleLanguage")}>
      <button type="button" className={`button button-ghost btn-sm ${locale === "en" ? "font-semibold" : ""}`} aria-pressed={locale === "en"} onClick={() => setLocale("en")}>{t("language")}</button>
      <button type="button" className={`button button-ghost btn-sm ${locale === "id" ? "font-semibold" : ""}`} aria-pressed={locale === "id"} onClick={() => setLocale("id")}>{t("languageIndonesian")}</button>
    </div>
  );
}
