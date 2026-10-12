"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useLocale } from "@/components/layout/locale-provider";
import { fetchBimaProjects, importBimaProject } from "@/lib/api/projects";
import type { ImportBimaPayload } from "@/types/project";

export const bimaCatalogQueryKey = ["bima-catalog"] as const;
export const projectsQueryKey = ["projects"] as const;

export function useBimaProjects(enabled = true) {
  return useQuery({
    queryKey: bimaCatalogQueryKey,
    queryFn: fetchBimaProjects,
    staleTime: 60_000,
    enabled,
  });
}

export function useImportBimaProject() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { t } = useLocale();

  return useMutation({
    mutationFn: (payload: ImportBimaPayload) => importBimaProject(payload),
    onSuccess: async (project) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: bimaCatalogQueryKey }),
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
      ]);
      toast.success(t("bimaImportSuccess"));
      // The new project is owned by the caller, so drop them straight into it.
      router.push(`/workspace/${project.id}`);
    },
  });
}
