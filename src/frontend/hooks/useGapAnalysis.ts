'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import type { GapQuestion, GapResponse, RawGapAnalysisData } from '../types/hub-state';

export function useGapAnalysis(jobId: string): {
  questions: GapQuestion[];
  responses: GapResponse[];
  submitResponses: (responses: GapResponse[]) => Promise<void>;
  isSubmitting: boolean;
} {
  const queryClient = useQueryClient();
  const enabled = jobId.length > 0;

  const { data } = useQuery<RawGapAnalysisData>({
    queryKey: queryKeys.gapAnalysis.detail(jobId),
    queryFn: async () => {
      const res = await apiClient.get<RawGapAnalysisData>(`/jobs/${jobId}/gap-questions`);
      return res.data;
    },
    enabled,
  });

  const { mutateAsync, isPending } = useMutation<void, Error, GapResponse[]>({
    mutationFn: async (responses: GapResponse[]) => {
      await apiClient.post(`/jobs/${jobId}/gap-questions/responses`, { responses });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.gapAnalysis.detail(jobId),
      });
    },
  });

  return {
    questions: data?.questions ?? [],
    responses: data?.responses ?? [],
    submitResponses: mutateAsync,
    isSubmitting: isPending,
  };
}
