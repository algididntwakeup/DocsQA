import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/components/layout/locale-provider";
import {
  bimaCatalogQueryKey,
  projectsQueryKey,
  useImportBimaProject,
} from "@/hooks/use-bima-projects";
import * as projectsApi from "@/lib/api/projects";

const push = vi.fn();
const success = vi.fn();
const error = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("sonner", () => ({
  toast: { success: (message: string) => success(message), error: (message: string) => error(message) },
}));

vi.mock("@/lib/api/projects", () => ({
  fetchBimaProjects: vi.fn(),
  importBimaProject: vi.fn(),
}));

function wrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <LocaleProvider>{children}</LocaleProvider>
      </QueryClientProvider>
    );
  };
}

const payload = {
  bima_project_id: 628,
  project_number: "13726486.02",
  name: "Piping Review",
  client_name: "Example Client",
};

describe("useImportBimaProject", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("invalidates the catalog and project queries, toasts, and routes to the new workspace", async () => {
    const imported = { id: "prism-project-9", name: "Piping Review" };
    vi.mocked(projectsApi.importBimaProject).mockResolvedValue(imported as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useImportBimaProject(), { wrapper: wrapper(queryClient) });
    await result.current.mutateAsync(payload);

    expect(projectsApi.importBimaProject).toHaveBeenCalledWith(payload);
    await waitFor(() => {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: bimaCatalogQueryKey });
      expect(invalidate).toHaveBeenCalledWith({ queryKey: projectsQueryKey });
    });
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/workspace/prism-project-9");
    });
    expect(success).toHaveBeenCalledWith("Project successfully imported to PRISM");
    expect(error).not.toHaveBeenCalled();
  });

  it("does not navigate when the import fails", async () => {
    vi.mocked(projectsApi.importBimaProject).mockRejectedValue(new Error("import failed"));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useImportBimaProject(), { wrapper: wrapper(queryClient) });

    await expect(result.current.mutateAsync(payload)).rejects.toThrow("import failed");
    expect(push).not.toHaveBeenCalled();
    expect(success).not.toHaveBeenCalled();
  });
});
