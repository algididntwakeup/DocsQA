"use client";

import ProjectDetailPage from "@/app/projects/[id]/page";

export default function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  return <ProjectDetailPage params={params} />;
}
