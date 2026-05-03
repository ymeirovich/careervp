'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../../components/ui/Spinner';
import type { GapQuestion, GapResponse, UserCV } from '../../../../lib/types';

type FormMode = 'view' | 'edit' | 'saving';

type LocalResponse = {
  answer: string;
  destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '';
};

function impactBadgeClass(v?: string): string {
  if (v === 'HIGH') return 'bg-state-active/10 text-state-active';
  if (v === 'MEDIUM') return 'bg-state-warning/10 text-state-warning';
  return 'bg-surface-subtle text-text-muted';
}

function GapAnalysisContent({ jobId }: { jobId: string }) {
  const router = useRouter();

  const [questions, setQuestions] = useState<GapQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, LocalResponse>>({});
  const [savedResponses, setSavedResponses] = useState<Record<string, LocalResponse>>({});
  const [mode, setMode] = useState<FormMode>('view');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToast, setSavedToast] = useState(false);
  const [cv, setCv] = useState<UserCV | null>(null);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [questionsResult, hubResult, cvResult] = await Promise.allSettled([
        api.getGapQuestions(jobId),
        api.getApplication(jobId),
        api.getCV(),
      ]);

      const qs = questionsResult.status === 'fulfilled' ? questionsResult.value : [];
      const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;
      const cvData = cvResult.status === 'fulfilled' ? cvResult.value : null;

      setCv(cvData);
      setQuestions(qs);

      const existingMap: Record<string, LocalResponse> = {};
      for (const r of hub?.gap_analysis.responses ?? []) {
        const entry = r as Record<string, unknown>;
        existingMap[r.question_id] = {
          answer: String(entry.response ?? entry.answer ?? ''),
          destination: (entry.destination as 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY') ?? '',
        };
      }
      setResponses(existingMap);
      setSavedResponses(existingMap);

      if (qs.length > 0 && Object.keys(existingMap).length === 0) {
        setMode('edit');
      }

      setLoading(false);
    };
    void init();
  }, [jobId]);

  const handleGenerate = async () => {
    if (!cv?.cv_id) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateGapQuestions({ job_id: jobId, cv_id: cv.cv_id });
      setQuestions(result.questions);
      setResponses({});
      setSavedResponses({});
      setMode('edit');
    } catch (err) {
      setError('Failed to generate questions. Please try again.');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    setMode('saving');
    setError(null);
    try {
      const payload: GapResponse[] = questions.flatMap((q) => {
        const r = responses[q.question_id];
        if (!r?.answer.trim()) return [];
        return [{ question_id: q.question_id, response: r.answer.trim() }];
      });
      await api.saveGapResponses(jobId, payload);
      setSavedResponses({ ...responses });
      setMode('view');
      setSavedToast(true);
      setTimeout(() => setSavedToast(false), 3000);
    } catch (err) {
      setError('Failed to save. Please try again.');
      console.error(err);
      setMode('edit');
    }
  };

  const setResponse = (qid: string, patch: Partial<LocalResponse>) => {
    setResponses((prev) => ({
      ...prev,
      [qid]: { ...{ answer: '', destination: '' }, ...prev[qid], ...patch },
    }));
  };

  const answeredCount = questions.filter((q) => responses[q.question_id]?.answer.trim()).length;
  const isEdit = mode === 'edit' || mode === 'saving';
  const isSaving = mode === 'saving';

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Gap Analysis…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6" data-testid="gap-analysis-page">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold text-text-primary">Gap Analysis</h1>
          <p className="text-sm text-text-muted">
            Answer questions to identify gaps between your CV and this role
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {questions.length === 0 && (
            <button
              onClick={() => void handleGenerate()}
              disabled={generating || !cv?.cv_id}
              className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
              data-testid="generate-gap-questions"
            >
              {generating ? 'Generating…' : 'Generate Questions'}
            </button>
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {savedToast && (
        <div className="rounded-md bg-state-active/10 border border-state-active px-4 py-3 text-sm font-medium text-state-active">
          Saved successfully
        </div>
      )}

      {error && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {error}
        </div>
      )}

      {questions.length === 0 && !generating && (
        <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center text-sm text-text-muted">
          No questions generated yet. Click &ldquo;Generate Questions&rdquo; to start.
        </div>
      )}

      {questions.length > 0 && (
        <div className="flex flex-col rounded-md border border-border-default bg-card overflow-hidden">
          <div className="sticky top-0 z-10 flex items-center justify-between bg-card border-b border-border-default px-6 py-3">
            <span className="text-sm text-text-muted">{answeredCount} of {questions.length} answered</span>
            <div className="flex gap-2">
              {isEdit ? (
                <>
                  <button
                    onClick={() => { setResponses({ ...savedResponses }); setMode('view'); }}
                    disabled={isSaving}
                    className="px-4 py-2 text-sm border border-border-default rounded-md text-text-primary hover:bg-surface-subtle disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void handleSave()}
                    disabled={isSaving}
                    className="px-4 py-2 text-sm bg-primary-action text-white rounded-md hover:opacity-90 disabled:opacity-50"
                    data-testid="save-responses"
                  >
                    {isSaving ? 'Saving…' : 'Save'}
                  </button>
                </>
              ) : (
                <button
                  onClick={() => { setResponses({ ...savedResponses }); setMode('edit'); }}
                  className="px-4 py-2 text-sm bg-primary-action text-white rounded-md hover:opacity-90"
                >
                  Edit
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-4 p-6">
            {questions.map((q, i) => {
              const r = responses[q.question_id] ?? { answer: '', destination: '' };
              return (
                <div
                  key={q.question_id || i}
                  className="flex flex-col gap-3 rounded-md border border-border-default p-4"
                  data-testid={`question-row-${i}`}
                >
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className="text-sm font-medium text-text-primary flex-1 min-w-0">
                      {i + 1}. {q.question}
                    </span>
                    <div className="flex gap-1 shrink-0">
                      {q.impact && (
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${impactBadgeClass(q.impact)}`}>
                          Impact: {q.impact}
                        </span>
                      )}
                      {q.probability && (
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${impactBadgeClass(q.probability)}`}>
                          Prob: {q.probability}
                        </span>
                      )}
                    </div>
                  </div>

                  {isEdit ? (
                    <>
                      <div className="flex gap-4 pl-4">
                        {(['CV_IMPACT', 'INTERVIEW_MVP_ONLY'] as const).map((dest) => (
                          <label key={dest} className="flex items-center gap-1.5 text-sm text-text-primary cursor-pointer">
                            <input
                              type="radio"
                              name={`dest-${q.question_id || i}`}
                              value={dest}
                              checked={r.destination === dest}
                              onChange={() => setResponse(q.question_id, { destination: dest })}
                              className="accent-primary-action"
                            />
                            {dest === 'CV_IMPACT' ? 'Include in CV' : 'Interview Only'}
                          </label>
                        ))}
                      </div>
                      <textarea
                        rows={4}
                        value={r.answer}
                        onChange={(e) => setResponse(q.question_id, { answer: e.target.value })}
                        placeholder="Your answer…"
                        className="w-full rounded border border-border-default px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action resize-none bg-card"
                      />
                    </>
                  ) : (
                    <p className={`pl-4 text-sm leading-relaxed ${r.answer ? 'text-text-primary' : 'text-text-muted italic'}`}>
                      {r.answer || 'No answer yet'}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GapAnalysisPage({ params: _params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = useParams<{ id: string }>();
  return (
    <ErrorBoundary cloudwatchKey="gap-analysis-page">
      <GapAnalysisContent jobId={jobId} />
    </ErrorBoundary>
  );
}
