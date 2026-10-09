"use client";

import { ErrorFallback } from "@/components/common/error-boundary";

interface RouteErrorProps {
  error: Error & { digest?: string };
  retry: () => void;
}

export default function RouteError({ error, retry }: RouteErrorProps) {
  return <ErrorFallback error={error} onReload={retry} />;
}
