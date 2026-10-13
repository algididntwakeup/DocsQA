"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  const { t } = useLocale();

  return useMutation({
    mutationFn: (payload: ImportBimaPayload) => importBimaProject(payload),
    onSuccess: async () => {
      // No navigation: the folder only appears on /projects once the user
      // chooses to open it, so the modal stays put and the row flips to the
      // "already in folder" badge via the invalidated catalog query.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: bimaCatalogQueryKey }),
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
      ]);
      toast.success(t("bimaImportSuccess"));
    },
  });
}
