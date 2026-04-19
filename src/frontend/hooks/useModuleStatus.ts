'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import type { ModuleType, RawModuleData } from '../types/hub-state';

const POLL_INTERVAL_MS = 3_000;

const STATUS_ENDPOINTS: Record<ModuleType, ((jobId: string) => string) | null> = {
  vpr: (jobId) => `/vpr/${jobId}/status`,
  tailoredCV: (jobId) => `/cv-tailoring/${jobId}/status`,
  coverLetter: (jobId) => `/cover-letter/${jobId}/status`,
  interviewPrep: (jobId) => `/interview-prep/${jobId}/status`,
  companyResearch: null,
  gapAnalysis: null,
  baseCV: null,
};

const STATUS_QUERY_KEYS: Record<ModuleType, ((jobId: string) => readonly string[]) | null> = {
  vpr: queryKeys.vpr.status,
  tailoredCV: queryKeys.cvTailoring.status,
  coverLetter: queryKeys.coverLetter.status,
  interviewPrep: queryKeys.interviewPrep.status,
  companyResearch: null,
  gapAnalysis: null,
  baseCV: null,
};

function isActiveStatus(status: RawModuleData['status'] | undefined): boolean {
  return status === 'pending' || status === 'processing';
}

export function useModuleStatus(
  moduleType: ModuleType,
  jobId: string,
  enabled: boolean,
): {
  rawStatus: RawModuleData | null;
  isPolling: boolean;
} {
  const endpointFn = STATUS_ENDPOINTS[moduleType];
  const keyFn = STATUS_QUERY_KEYS[moduleType];
  const hasEndpoint = endpointFn !== null && keyFn !== null;

  const { data } = useQuery<RawModuleData>({
    queryKey: keyFn ? keyFn(jobId) : ['noop', moduleType, jobId],
    queryFn: async () => {
      const res = await apiClient.get<RawModuleData>(endpointFn!(jobId));
      return res.data;
    },
    enabled: enabled && hasEndpoint && jobId.length > 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return isActiveStatus(status) ? POLL_INTERVAL_MS : false;
    },
    staleTime: 0,
  });

  const rawStatus = data ?? null;
  const isPolling = hasEndpoint && enabled && isActiveStatus(rawStatus?.status);

  return { rawStatus, isPolling };
}
