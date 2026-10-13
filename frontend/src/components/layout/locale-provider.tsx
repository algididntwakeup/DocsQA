"use client";

import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";
import { DEFAULT_LOCALE, translate, type Locale, type TranslationKey } from "@/lib/i18n";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
}

/**
 * PRISM renders English only.
 *
 * The bilingual dictionary still exists in `@/lib/i18n`, but the UI is pinned
 * to `en` so no mixed-language strings can reach the screen. `setLocale` is
 * intentionally a no-op: the language toggle was removed, and keeping the
 * switch inert means a stale `matqc-locale` value in a returning user's
 * localStorage cannot flip the interface back to Indonesian.
 */
const LocaleContext = createContext<LocaleContextValue>({
  locale: DEFAULT_LOCALE,
  setLocale: () => undefined,
  t: (key, vars) => translate(DEFAULT_LOCALE, key, vars),
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.lang = DEFAULT_LOCALE;
  }, []);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale: DEFAULT_LOCALE,
      setLocale: () => undefined,
      t: (key, vars) => translate(DEFAULT_LOCALE, key, vars),
    }),
    [],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useLocale must be used within LocaleProvider");
  return context;
}
