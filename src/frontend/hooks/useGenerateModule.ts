'use client';

import { useState, useRef } from 'react';
import { api } from '../api/methods';
import { persistArtifact, clearArtifact } from '../lib/artifactStorage';
import type { ModuleType } from '../types/enums';

export interface GenerateOptions {
  cvId?: string;
  vprId?: string;
  gapResponseIds?: string[];
  companyResearchId?: string;
  force?: boolean;
}

const CANCEL_FN_MAP: Partial<Record<ModuleType, (id: string) => Promise<unknown>>> = {
  vpr: (id) => api.cancelVpr(id),
  coverLetter: (id) => api.cancelCoverLetter(id),
  interviewPrep: (id) => api.cancelInterviewPrep(id),
  tailoredCV: (id) => api.cancelCvTailoring(id),
  companyResearch: (id) => api.cancelCompanyResearch(id),
};

export function useGenerateModule(
  moduleType: ModuleType,
  jobId: string,
): {
  generate: (options?: GenerateOptions) => Promise<void>;
  cancel: (taskId: string) => Promise<void>;
  isGenerating: boolean;
  isCancelling: boolean;
  taskId: string | null;
  error: string | null;
} {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  async function generate(options: GenerateOptions = {}): Promise<void> {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsGenerating(true);
    setError(null);
    try {
      let response;
      switch (moduleType) {
        case 'vpr':
          response = await api.generateVPR({
            application_id: jobId,
            cv_id: options.cvId!,
            gap_response_ids: options.gapResponseIds ?? [],
            force: options.force ?? false,
          });
          break;
        case 'coverLetter':
          response = await api.generateCoverLetter({
            application_id: jobId,
            cv_id: options.cvId!,
            vpr_id: options.vprId!,
            gap_response_ids: options.gapResponseIds ?? [],
            company_research_id: options.companyResearchId,
          });
          break;
        case 'interviewPrep':
          response = await api.generateInterviewPrep({
            vpr_id: options.vprId!,
            gap_response_ids: options.gapResponseIds ?? [],
            application_id: jobId,
          });
          break;
        case 'tailoredCV':
          response = await api.generateCV({
            cv_id: options.cvId!,
            job_id: jobId,
            vpr_id: options.vprId ?? null,
          });
          break;
        case 'companyResearch':
          response = await api.fetchCompanyResearch({
            job_id: jobId,
            retry: options.force ?? false,
          });
          break;
        default:
          throw new Error(`Unsupported module type: ${moduleType}`);
      }

      // Check if cancelled before taskId was resolved
      if (controller.signal.aborted) return;

      const resolvedTaskId = response.request_id ?? response.job_id ?? null;
      setTaskId(resolvedTaskId);
      if (resolvedTaskId) {
        persistArtifact(jobId, moduleType, resolvedTaskId);
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'Generation failed';
      setError(message);
      throw err;
    } finally {
      abortControllerRef.current = null;
      setIsGenerating(false);
    }
  }

  async function cancel(cancelTaskId: string): Promise<void> {
    // Abort any in-flight request (pre-taskId window)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsCancelling(true);
    try {
      const cancelFn = CANCEL_FN_MAP[moduleType];
      if (cancelFn && cancelTaskId) {
        // TODO FE-UI-027 / AC-018: SQS workers do not check CANCELLED status before writing
        // results. A worker that started before this cancel arrived may overwrite CANCELLED →
        // COMPLETED on the next hub load. Worker-side guard is deferred to V2.
        await cancelFn(cancelTaskId).catch(() => {
          // 409 (already terminal) is acceptable — still clear local state
        });
      }
    } finally {
      setTaskId(null);
      clearArtifact(jobId, moduleType);
      setIsCancelling(false);
    }
  }

  return { generate, cancel, isGenerating, isCancelling, taskId, error };
}
