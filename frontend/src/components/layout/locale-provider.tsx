"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { detectLocale, LOCALE_STORAGE_KEY, normalizeLocale, translate, type Locale, type TranslationKey } from "@/lib/i18n";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
}

const LocaleContext = createContext<LocaleContextValue>({ locale: "en", setLocale: () => undefined, t: (key, vars) => translate("en", key, vars) });

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const syncLocale = () => {
      try {
        const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
        setLocaleState(stored === null ? detectLocale() : normalizeLocale(stored));
      } catch {
        setLocaleState(detectLocale());
      }
    };
    syncLocale();
    window.addEventListener("storage", syncLocale);
    window.addEventListener("matqc-locale-change", syncLocale);
    return () => {
      window.removeEventListener("storage", syncLocale);
      window.removeEventListener("matqc-locale-change", syncLocale);
    };
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
      window.dispatchEvent(new CustomEvent("matqc-locale-change", { detail: next }));
    } catch {
      // Keep the selected locale in memory when storage is unavailable.
    }
  };

  const value = useMemo<LocaleContextValue>(() => ({ locale, setLocale, t: (key, vars) => translate(locale, key, vars) }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useLocale must be used within LocaleProvider");
  return context;
}
