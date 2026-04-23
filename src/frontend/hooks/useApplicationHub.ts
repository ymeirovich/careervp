'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import { mapApplicationDataToHubState } from '../adapters/mapApplicationDataToHubState';
import { getArtifact } from '../lib/artifactStorage';
import { useModuleStatus } from './useModuleStatus';
import type {
  RawApplicationData,
  RawCVData,
  RawGapAnalysisData,
  RawModuleData,
  HubState,
} from '../types/hub-state';
import type { HubArtifact, ArtifactStatus } from '../lib/types';
import type { ModuleType } from '../types/enums';

// The actual API response includes artifacts from spec-10
interface ApplicationResponse extends RawApplicationData {
  artifacts?: {
    vpr?: HubArtifact;
    cover_letter?: HubArtifact;
    interview_prep?: HubArtifact;
    cv_tailored?: HubArtifact;
    gap_analysis?: HubArtifact;
  };
}

function resolveTaskId(
  jobId: string,
  moduleType: ModuleType,
  artifact?: HubArtifact,
): string | null {
  // Priority 1: hub artifact_id when status is processing or completed
  if (
    artifact?.artifact_id &&
    (artifact.status === 'processing' || artifact.status === 'completed')
  ) {
    return artifact.artifact_id;
  }
  // Priority 2: localStorage fallback
  return getArtifact(jobId, moduleType);
}

function buildModuleData(
  jobId: string,
  hubArtifact: HubArtifact | undefined,
  pollingStatus: ArtifactStatus | null,
): RawModuleData | undefined {
  // Polling result takes priority over hub data
  if (pollingStatus) {
    return { job_id: jobId, status: pollingStatus, created_at: '', updated_at: '' };
  }
  // Hub artifact status only when there's a real artifact ID (null = not started)
  if (hubArtifact?.artifact_id && hubArtifact.status) {
    return { job_id: jobId, status: hubArtifact.status, created_at: '', updated_at: '' };
  }
  return undefined;
}

export function useApplicationHub(jobId: string): {
  hubState: HubState | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const enabled = jobId.length > 0;

  const applicationQuery = useQuery<ApplicationResponse>({
    queryKey: queryKeys.applications.detail(jobId),
    queryFn: async () => {
      const res = await apiClient.get<ApplicationResponse>(`/applications/${jobId}`);
      return res.data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });

  const cvQuery = useQuery<RawCVData>({
    queryKey: queryKeys.cv.detail(),
    queryFn: async () => {
      const res = await apiClient.get<RawCVData>('/users/me/cv');
      return res.data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });

  const gapQuery = useQuery<RawGapAnalysisData>({
    queryKey: queryKeys.gapAnalysis.detail(jobId),
    queryFn: async () => {
      const res = await apiClient.get<RawGapAnalysisData>(`/jobs/${jobId}/gap-questions`);
      return res.data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });

  const appData = applicationQuery.data;
  const artifacts = appData?.artifacts;

  // Two-source reconciliation: hub artifact_id → localStorage → null
  const vprTaskId = enabled ? resolveTaskId(jobId, 'vpr', artifacts?.vpr) : null;
  const coverLetterTaskId = enabled ? resolveTaskId(jobId, 'coverLetter', artifacts?.cover_letter) : null;
  const interviewPrepTaskId = enabled ? resolveTaskId(jobId, 'interviewPrep', artifacts?.interview_prep) : null;
  const tailoredCVTaskId = enabled ? resolveTaskId(jobId, 'tailoredCV', artifacts?.cv_tailored) : null;

  const vprStatus = useModuleStatus('vpr', jobId, vprTaskId, enabled);
  const coverLetterStatus = useModuleStatus('coverLetter', jobId, coverLetterTaskId, enabled);
  const interviewPrepStatus = useModuleStatus('interviewPrep', jobId, interviewPrepTaskId, enabled);
  const tailoredCVStatus = useModuleStatus('tailoredCV', jobId, tailoredCVTaskId, enabled);

  const isLoading =
    applicationQuery.isLoading ||
    cvQuery.isLoading ||
    gapQuery.isLoading;

  const error =
    (applicationQuery.error as Error | null) ??
    (cvQuery.error as Error | null) ??
    (gapQuery.error as Error | null);

  let hubState: HubState | null = null;

  if (appData) {
    // Polling status overrides hub artifact status for live updates
    const moduleData: Partial<Record<ModuleType, RawModuleData>> = {};

    const vprData = buildModuleData(jobId, artifacts?.vpr, vprStatus.status);
    if (vprData) moduleData.vpr = vprData;

    const coverLetterData = buildModuleData(jobId, artifacts?.cover_letter, coverLetterStatus.status);
    if (coverLetterData) moduleData.coverLetter = coverLetterData;

    const interviewPrepData = buildModuleData(jobId, artifacts?.interview_prep, interviewPrepStatus.status);
    if (interviewPrepData) moduleData.interviewPrep = interviewPrepData;

    const tailoredCVData = buildModuleData(jobId, artifacts?.cv_tailored, tailoredCVStatus.status);
    if (tailoredCVData) moduleData.tailoredCV = tailoredCVData;

    hubState = mapApplicationDataToHubState(
      appData,
      moduleData,
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
