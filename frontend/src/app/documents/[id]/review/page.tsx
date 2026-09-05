import { ReviewWorkspaceView } from "@/components/review/review-workspace-view";

export default async function ReviewPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <ReviewWorkspaceView id={id} />;
}
