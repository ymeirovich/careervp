'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import { mapApplicationDataToHubState } from '../adapters/mapApplicationDataToHubState';
import { useModuleStatus } from './useModuleStatus';
import type {
  RawApplicationData,
  RawCVData,
  RawGapAnalysisData,
  HubState,
} from '../types/hub-state';
export function useApplicationHub(jobId: string): {
  hubState: HubState | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const enabled = jobId.length > 0;

  const applicationQuery = useQuery<RawApplicationData>({
    queryKey: queryKeys.applications.detail(jobId),
    queryFn: async () => {
      const res = await apiClient.get<RawApplicationData>(`/applications/${jobId}`);
      return res.data;
    },
    enabled,
  });

  const cvQuery = useQuery<RawCVData>({
    queryKey: queryKeys.cv.detail(),
    queryFn: async () => {
      const res = await apiClient.get<RawCVData>('/users/me/cv');
      return res.data;
    },
    enabled,
  });

  const gapQuery = useQuery<RawGapAnalysisData>({
    queryKey: queryKeys.gapAnalysis.detail(jobId),
    queryFn: async () => {
      const res = await apiClient.get<RawGapAnalysisData>(`/jobs/${jobId}/gap-questions`);
      return res.data;
    },
    enabled,
  });

  const vprStatus = useModuleStatus('vpr', jobId, enabled);
  const tailoredCVStatus = useModuleStatus('tailoredCV', jobId, enabled);
  const coverLetterStatus = useModuleStatus('coverLetter', jobId, enabled);
  const interviewPrepStatus = useModuleStatus('interviewPrep', jobId, enabled);

  const isLoading =
    applicationQuery.isLoading ||
    cvQuery.isLoading ||
    gapQuery.isLoading;

  const error =
    (applicationQuery.error as Error | null) ??
    (cvQuery.error as Error | null) ??
    (gapQuery.error as Error | null);

  let hubState: HubState | null = null;

  if (applicationQuery.data) {
    hubState = mapApplicationDataToHubState(
      applicationQuery.data,
      {
        vpr: vprStatus.rawStatus ?? undefined,
        tailoredCV: tailoredCVStatus.rawStatus ?? undefined,
        coverLetter: coverLetterStatus.rawStatus ?? undefined,
        interviewPrep: interviewPrepStatus.rawStatus ?? undefined,
      },
      gapQuery.data ?? null,
      cvQuery.data ?? null,
      null,
    );
  }

  function refetch() {
    void applicationQuery.refetch();
    void cvQuery.refetch();
    void gapQuery.refetch();
  }

  return { hubState, isLoading, error, refetch };
}
