import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { LocaleProvider } from "@/components/layout/locale-provider";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "sonner";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PRISM - Document Assurance Platform",
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

const themeBootstrap = `
(function () {
  try {
    var theme = localStorage.getItem("matqc-theme") === "dark" ? "dark" : "light";
    var root = document.documentElement;
    root.setAttribute("data-theme", theme);
    root.classList.toggle("dark", theme === "dark");
    root.classList.toggle("light", theme === "light");
    document.body && document.body.classList.toggle("dark", theme === "dark");
  } catch (error) {
    /* Storage unavailable: keep the server-rendered light theme. */
  }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${plusJakartaSans.variable} h-full antialiased light`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased font-sans">
        <LocaleProvider>
          <AppShell>{children}</AppShell>
        </LocaleProvider>
        <Toaster position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
