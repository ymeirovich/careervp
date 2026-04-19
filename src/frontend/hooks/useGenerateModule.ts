'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import { useApplicationStore } from '../store/useApplicationStore';
import type { ModuleType } from '../types/enums';

interface GenerateResponse {
  job_id: string;
}

type GenerateEndpointFn = (jobId: string) => { method: 'GET' | 'POST'; url: string };

const GENERATE_ENDPOINTS: Record<ModuleType, GenerateEndpointFn> = {
  vpr: () => ({ method: 'POST', url: '/vpr/generate' }),
  tailoredCV: () => ({ method: 'POST', url: '/cv-tailoring/generate' }),
  coverLetter: () => ({ method: 'POST', url: '/cover-letter/generate' }),
  interviewPrep: () => ({ method: 'POST', url: '/interview-prep/generate' }),
  companyResearch: (jobId) => ({ method: 'GET', url: `/company-research/${jobId}` }),
  gapAnalysis: (jobId) => ({ method: 'POST', url: `/jobs/${jobId}/gap-questions` }),
  baseCV: () => ({ method: 'POST', url: '/users/me/cv' }),
};

const INVALIDATION_KEYS: Partial<Record<ModuleType, (jobId: string) => readonly string[]>> = {
  vpr: queryKeys.vpr.status,
  tailoredCV: queryKeys.cvTailoring.status,
  coverLetter: queryKeys.coverLetter.status,
  interviewPrep: queryKeys.interviewPrep.status,
  gapAnalysis: queryKeys.gapAnalysis.detail,
  baseCV: queryKeys.cv.detail,
};

export function useGenerateModule(moduleType: ModuleType): {
  generate: (jobId: string) => Promise<{ newJobId: string }>;
  isGenerating: boolean;
  error: Error | null;
} {
  const queryClient = useQueryClient();
  const setActiveJob = useApplicationStore((s) => s.setActiveJob);

  const { mutateAsync, isPending, error } = useMutation<GenerateResponse, Error, string>({
    mutationFn: async (jobId: string) => {
      const { method, url } = GENERATE_ENDPOINTS[moduleType](jobId);
      const res =
        method === 'GET'
          ? await apiClient.get<GenerateResponse>(url)
          : await apiClient.post<GenerateResponse>(url, { job_id: jobId });
      return res.data;
    },
    onSuccess: (data, jobId) => {
      const newJobId = data.job_id;

      const keyFn = INVALIDATION_KEYS[moduleType];
      if (keyFn) {
        void queryClient.invalidateQueries({ queryKey: keyFn(newJobId) });
      }

      if (newJobId !== jobId) {
        setActiveJob(newJobId);
      }
    },
  });

  async function generate(jobId: string): Promise<{ newJobId: string }> {
    const data = await mutateAsync(jobId);
    return { newJobId: data.job_id };
  }

  return {
    generate,
    isGenerating: isPending,
    error,
  };
}
