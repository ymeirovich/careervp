'use client';

import { useState, useEffect } from 'react';
import { api } from '../api/methods';
import type { GapQuestion, GapResponse } from '../lib/types';

export function useGapAnalysis(jobId: string): {
  questions: GapQuestion[];
  responses: Record<string, { answer: string; destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '' }>;
  savedResponses: Record<string, unknown>;
  isLoading: boolean;
  isGenerating: boolean;
  isSaving: boolean;
  generateQuestions: (cvId: string) => Promise<void>;
  saveResponses: (responses: GapResponse[]) => Promise<void>;
  error: string | null;
} {
  const [questions, setQuestions] = useState<GapQuestion[]>([]);
  const [responses, setResponses] = useState<
    Record<string, { answer: string; destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '' }>
  >({});
  const [savedResponses, setSavedResponses] = useState<Record<string, unknown>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    api
      .getGapQuestions(jobId)
      .then((qs) => {
        if (!cancelled) setQuestions(qs);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load questions');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  async function generateQuestions(cvId: string): Promise<void> {
    setIsGenerating(true);
    setError(null);
    try {
      const result = await api.generateGapQuestions({ job_id: jobId, cv_id: cvId });
      setQuestions(result.questions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate questions');
    } finally {
      setIsGenerating(false);
    }
  }

  async function saveResponses(gapResponses: GapResponse[]): Promise<void> {
    setIsSaving(true);
    setError(null);
    try {
      await api.saveGapResponses(jobId, gapResponses);
      const saved: Record<string, unknown> = {};
      gapResponses.forEach((r) => {
        saved[r.question_id] = r;
      });
      setSavedResponses(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save responses');
    } finally {
      setIsSaving(false);
    }
  }

  return {
    questions,
    responses,
    savedResponses,
    isLoading,
    isGenerating,
    isSaving,
    generateQuestions,
    saveResponses,
    error,
  };
}
