import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Document QC",
  description: "Document quality control and traceability audit",
};

const themeInitScript = `
(function () {
  try {
    var theme = localStorage.getItem("matqc-theme");
    if (theme !== "dark") theme = "light";
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "light") {
      document.documentElement.classList.add("light");
      document.body && document.body.classList.add("light");
    }
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body><AppShell>{children}</AppShell><Toaster position="bottom-right" richColors closeButton /></body>
    </html>
  );
}
