"use client";

import Image from "next/image";
import { useRef, useState } from "react";
import type { HeaderPlacement, HeaderTemplateConfig } from "@/lib/api";

const placementOptions: { id: HeaderPlacement; title: string; description: string }[] = [
  { id: "split_standard", title: "Split", description: "Left: Reksolindo · Right: Client" },
  { id: "split_inverted", title: "Inverted split", description: "Left: Client · Right: Reksolindo" },
  { id: "both_left", title: "Both on the left", description: "Paired logos on the left" },
  { id: "both_right", title: "Both on the right", description: "Paired logos on the right" },
];

interface HeaderTemplateConfigProps {
  value: HeaderTemplateConfig;
  onChange: (value: HeaderTemplateConfig) => void;
}

function HeaderLogo({ src, alt }: { src?: string | null; alt: string }) {
  return src ? <Image src={src} alt={alt} width={160} height={64} unoptimized className="max-h-8 max-w-20 object-contain" /> : <span className="text-[8px] text-muted-foreground">{alt}</span>;
}

export function HeaderTemplateConfigEditor({ value, onChange }: HeaderTemplateConfigProps) {
  const companyInput = useRef<HTMLInputElement>(null);
  const clientInput = useRef<HTMLInputElement>(null);
  const [logoError, setLogoError] = useState<string | null>(null);
  const updateLogo = (key: "company_logo" | "client_logo", file?: File) => {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setLogoError("Ukuran logo maksimal 2 MB.");
      return;
    }
    setLogoError(null);
    const reader = new FileReader();
    reader.onload = () => onChange({ ...value, [key]: String(reader.result) });
    reader.readAsDataURL(file);
  };
  const shownCompanyLogo = value.company_logo || "/reksolindo-logo.png";
  const logoColumn = value.placement === "split_inverted" ? "client-left" : value.placement === "both_left" ? "both-left" : value.placement === "both_right" ? "both-right" : "standard";

  return (
    <section className="space-y-4 rounded-xl border border-line bg-card p-4" aria-label="Konfigurasi header dokumen">
      <label className="flex items-center gap-2 text-sm font-semibold text-ink">
        <input type="checkbox" checked={value.enabled} onChange={(event) => onChange({ ...value, enabled: event.target.checked })} />
        Aktifkan Custom Header / Letterhead
      </label>
      {value.enabled && <>
        <label className="block space-y-1 text-xs font-medium text-ink">
          <span>Center title</span>
          <input className="w-full rounded-md border border-line bg-background px-3 py-2" value={value.title} maxLength={180} onChange={(event) => onChange({ ...value, title: event.target.value })} />
        </label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="space-y-1">
            <span className="text-xs font-medium text-ink">Logo Reksolindo</span>
            <input ref={companyInput} type="file" accept="image/png,image/jpeg,image/gif" className="block w-full text-xs" onChange={(event) => updateLogo("company_logo", event.target.files?.[0])} />
          </div>
          <div className="space-y-1">
            <span className="text-xs font-medium text-ink">Logo klien</span>
            <input ref={clientInput} type="file" accept="image/png,image/jpeg,image/gif" className="block w-full text-xs" onChange={(event) => updateLogo("client_logo", event.target.files?.[0])} />
          </div>
        </div>
        {logoError && <p className="text-xs text-rose-600" role="alert">{logoError}</p>}
        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold text-ink">Posisi logo</legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {placementOptions.map((option) => <label key={option.id} className={`cursor-pointer rounded-lg border p-2 ${value.placement === option.id ? "border-primary bg-primary/5" : "border-line"}`}>
              <input className="sr-only" type="radio" name="header-placement" value={option.id} checked={value.placement === option.id} onChange={() => onChange({ ...value, placement: option.id })} />
              <span className="block text-xs font-semibold text-ink">{option.title}</span>
              <span className="text-[10px] text-muted-foreground">{option.description}</span>
            </label>)}
          </div>
        </fieldset>
        <label className="flex items-center gap-2 text-xs text-ink">
          <input type="checkbox" checked={value.show_divider} onChange={(event) => onChange({ ...value, show_divider: event.target.checked })} />
          Tampilkan garis pemisah bawah
        </label>
        <div className="rounded-lg border border-line bg-muted/10 p-3" aria-label="Header preview">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Live preview</p>
          <div className="grid min-h-12 grid-cols-[1fr_2fr_1fr] items-center gap-2">
            <div className="flex items-center justify-start gap-1">{(logoColumn === "both-left") ? <><HeaderLogo src={shownCompanyLogo} alt="Reksolindo" /><HeaderLogo src={value.client_logo} alt="Client" /></> : logoColumn === "both-right" ? null : logoColumn === "client-left" ? <HeaderLogo src={value.client_logo} alt="Client" /> : <HeaderLogo src={shownCompanyLogo} alt="Reksolindo" />}</div>
            <div className="break-words text-center text-[9px] font-bold text-ink">{value.title || "Document title"}</div>
            <div className="flex items-center justify-end gap-1">{logoColumn === "both-right" ? <><HeaderLogo src={shownCompanyLogo} alt="Reksolindo" /><HeaderLogo src={value.client_logo} alt="Client" /></> : logoColumn === "both-left" ? null : logoColumn === "client-left" ? <HeaderLogo src={shownCompanyLogo} alt="Reksolindo" /> : <HeaderLogo src={value.client_logo} alt="Client" />}</div>
          </div>
          {value.show_divider && <div className="mt-2 border-b border-slate-300" />}
        </div>
      </>}
    </section>
  );
}
