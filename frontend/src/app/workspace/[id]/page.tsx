"use client";

import ProjectDetailPage from "@/app/projects/[id]/page";
import { ErrorBoundary } from "@/components/common/error-boundary";

export default function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <ErrorBoundary>
      <ProjectDetailPage params={params} />
    </ErrorBoundary>
  );
}
