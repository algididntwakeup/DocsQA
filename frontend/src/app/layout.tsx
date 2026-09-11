import type { Metadata } from "next";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reksolindo Docs QA ",
  description: "Engineering Document Inspection & QA Platform",
  icons: {
    icon: [
      { url: "/icon.png", sizes: "180x180", type: "image/png" },
      { url: "/favicon.ico" },
    ],
    apple: [
      { url: "/apple-icon.png", sizes: "180x180", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" className="h-full antialiased light" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased font-sans">
        <LocaleProvider>
          <AppShell>{children}</AppShell>
        </LocaleProvider>
        <Toaster position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
