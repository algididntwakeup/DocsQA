import { DocumentStatusView } from "@/components/document/document-status-view";

export default async function DocumentPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <DocumentStatusView id={id} />;
}
