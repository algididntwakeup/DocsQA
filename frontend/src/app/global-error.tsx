"use client";

import { ErrorFallback } from "@/components/common/error-boundary";
import "./globals.css";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  retry: () => void;
}

export default function GlobalError({ error, retry }: GlobalErrorProps) {
  return (
    <html lang="id">
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <ErrorFallback error={error} onReload={retry} />
      </body>
    </html>
  );
}
