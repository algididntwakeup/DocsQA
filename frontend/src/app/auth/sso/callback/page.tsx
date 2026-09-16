"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ApiError, exchangeSsoToken } from "@/lib/api";

function SsoCallbackContent() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    exchangeSsoToken(token)
      .then(() => router.replace("/projects"))
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "Sesi BIMA tidak dapat diverifikasi."));
  }, [router, token]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-10 text-center shadow-xl shadow-slate-900/5">
        {!token || error ? (
          <div role="alert" className="space-y-4">
            <p className="text-sm font-semibold text-rose-700">{error ?? "Token sesi BIMA tidak ditemukan."}</p>
            <button type="button" onClick={() => router.replace("/login")} className="text-xs font-bold text-blue-700 hover:underline">Kembali ke login</button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" aria-label="Memuat" />
            <p className="text-sm font-semibold text-slate-700">Memverifikasi sesi BIMA SSO...</p>
          </div>
        )}
      </section>
    </main>
  );
}

export default function SsoCallbackPage() {
  return (
    <Suspense fallback={<main className="flex min-h-screen items-center justify-center bg-slate-50 p-6"><p className="text-sm font-semibold text-slate-700">Memverifikasi sesi BIMA SSO...</p></main>}>
      <SsoCallbackContent />
    </Suspense>
  );
}
