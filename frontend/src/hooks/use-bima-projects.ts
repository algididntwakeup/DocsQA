"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchBimaProjects, importBimaProject } from "@/lib/api/projects";
import type { ImportBimaPayload } from "@/types/project";

export const bimaProjectsQueryKey = ["bima-projects"] as const;
export const projectsQueryKey = ["projects"] as const;

export function useBimaProjects(enabled = true) {
  return useQuery({
    queryKey: bimaProjectsQueryKey,
    queryFn: fetchBimaProjects,
    staleTime: 60_000,
    enabled,
  });
}

export function useImportBimaProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ImportBimaPayload) => importBimaProject(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: bimaProjectsQueryKey }),
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
      ]);
    },
  });
}
