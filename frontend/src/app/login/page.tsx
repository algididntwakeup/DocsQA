"use client";

import { ArrowRight, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useLocale } from "@/components/layout/locale-provider";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { ReksolindoLogo } from "@/components/layout/reksolindo-logo";

export default function LoginPage() {
  const { t } = useLocale();
  const [submitting, setSubmitting] = useState(false);
  function startSso() {
    const redirectUri = `${window.location.origin}/auth/sso/callback`;
    const clientId = process.env.NEXT_PUBLIC_BIMA_CLIENT_ID ?? "prism";
    const bimaBase = (process.env.NEXT_PUBLIC_BIMA_BASE_URL ?? "https://bima.reksolindo.co.id").replace(/\/+$/, "");
    // This is an external BIMA SSO redirect, not navigation to an internal Next.js route.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- BIMA requires a full-page external redirect.
    window.location.href = `${bimaBase}/sso/authorize?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=profile%20roles%20permissions%20email%20department`;
  }

  function handleSsoClick() {
    setSubmitting(true);
    startSso();
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-background p-4 sm:p-6 font-sans">
      <div className="absolute right-6 top-6 flex items-center gap-2">
        <ThemeToggle />
        <LanguageToggle />
      </div>

      <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border bg-card shadow-2xl shadow-slate-950/10 md:min-h-[560px] md:grid-cols-[1.05fr_0.95fr]">
        <section className="relative flex flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 p-8 text-white sm:p-12">
          <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full border border-white/10 bg-blue-400/10 blur-3xl" />
          <div className="relative"><ReksolindoLogo variant="dark" /></div>

          <div className="relative my-12 max-w-lg space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-300/20 bg-blue-300/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-blue-200">
              <span className="size-1.5 rounded-full bg-emerald-400 shadow-[0_0_12px_2px_rgba(52,211,153,.5)]" />
              {t("loginKicker")}
            </div>
            <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">{t("loginTitle")}</h1>
            <p className="max-w-sm text-sm leading-7 text-slate-300">{t("loginDescription")}</p>
          </div>

          <div className="relative flex items-center gap-3 border-t border-white/10 pt-5 text-xs font-medium text-slate-300">
            <ShieldCheck size={17} className="text-emerald-400" />
            <span>{t("roleAware")}</span>
          </div>
        </section>

        <section className="flex flex-col justify-center p-8 sm:p-12">
          <div className="mb-8 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">{t("secureWorkspace")}</p>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">{t("welcomeBack")}</h2>
            <p className="text-sm leading-6 text-muted-foreground">{t("ssoOnlyDescription")}</p>
          </div>

          <button
            type="button"
            onClick={handleSsoClick}
            disabled={submitting}
            className="group flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-primary px-5 py-4 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-60"
          >
            <span>{t("bimaSso")}</span>
            <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" />
          </button>

          <p className="mt-5 text-center text-xs leading-5 text-muted-foreground">{t("ssoSecurityNote")}</p>

          <div className="mt-10 flex items-center justify-center gap-2 text-[11px] text-muted-foreground">
            <ShieldCheck size={14} className="text-emerald-600" />
            {t("secureWorkspace")}
          </div>
        </section>
      </div>
    </div>
  );
}
