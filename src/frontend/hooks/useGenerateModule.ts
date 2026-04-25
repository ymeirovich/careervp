'use client';

import { useState } from 'react';
import { api } from '../api/methods';
import type { ModuleType } from '../types/enums';

export interface GenerateOptions {
  cvId?: string;
  vprId?: string;
  gapResponseIds?: string[];
  companyResearchId?: string;
}

export function useGenerateModule(
  moduleType: ModuleType,
  jobId: string,
): {
  generate: (options?: GenerateOptions) => Promise<void>;
  isGenerating: boolean;
  taskId: string | null;
  error: string | null;
} {
  const [isGenerating, setIsGenerating] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate(options: GenerateOptions = {}): Promise<void> {
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
          });
          break;
        case 'coverLetter':
          response = await api.generateCoverLetter({
            application_id: jobId,
            cv_id: options.cvId!,
            vpr_id: options.vprId!,
            gap_response_ids: options.gapResponseIds ?? [],
            company_research_id: options.companyResearchId ?? '',
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
        default:
          throw new Error(`Unsupported module type: ${moduleType}`);
      }
      setTaskId(response.request_id ?? response.job_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setIsGenerating(false);
    }
  }

  return { generate, isGenerating, taskId, error };
}
