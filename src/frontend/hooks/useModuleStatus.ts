'use client';

import { useEffect, useState } from 'react';
import { api } from '../api/methods';
import { persistArtifact, getArtifact } from '../lib/artifactStorage';
import type { ArtifactStatus } from '../lib/types';
import type { ModuleType } from '../types/enums';

type PollFn = (taskId: string) => Promise<{ status: ArtifactStatus; result?: unknown }>;

// Some status response types use `status: string` — cast to ArtifactStatus since the
// backend only ever returns values within that union.
const POLL_FN_MAP: Partial<Record<ModuleType, PollFn>> = {
  vpr: (taskId) => api.pollVPRStatus(taskId),
  coverLetter: (taskId) =>
    api.pollCoverLetterStatus(taskId) as Promise<{ status: ArtifactStatus; result?: unknown }>,
  interviewPrep: (taskId) =>
    api.pollInterviewPrepStatus(taskId) as Promise<{ status: ArtifactStatus; result?: unknown }>,
  tailoredCV: (taskId) => api.pollCVTailored(taskId),
};

export function useModuleStatus(
  moduleType: ModuleType,
  jobId: string,
  initialTaskId: string | null,
  enabled: boolean,
): {
  status: ArtifactStatus | null;
  result: unknown | null;
  taskId: string | null;
  isPolling: boolean;
} {
  // Resolve taskId: prop first, then localStorage fallback
  const taskId = initialTaskId ?? getArtifact(jobId, moduleType);

  const [status, setStatus] = useState<ArtifactStatus | null>(null);
  const [result, setResult] = useState<unknown | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (!enabled || !taskId) return;

    const pollFn = POLL_FN_MAP[moduleType];
    if (!pollFn) return;

    setIsPolling(true);

    const interval = setInterval(async () => {
      try {
        const response = await pollFn(taskId);
        setStatus(response.status);
        setResult(response.result ?? null);

        if (response.status === 'completed' || response.status === 'failed') {
          clearInterval(interval);
          setIsPolling(false);
          if (response.status === 'completed') {
            persistArtifact(jobId, moduleType, taskId);
          }
        }
      } catch {
        // transient network error — continue polling
      }
    }, 3000);

    return () => {
      clearInterval(interval);
      setIsPolling(false);
    };
  }, [taskId, enabled, moduleType, jobId]);

  return { status, result, taskId, isPolling };
}
