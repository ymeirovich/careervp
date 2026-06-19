'use client';

import React, { useState, useEffect, use, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { Spinner } from '../../../../components/ui/Spinner';
import type { PrepQuestion, JobDetail } from '../../../../lib/types';

type PrepResult = NonNullable<Awaited<ReturnType<typeof api.getInterviewPrep>>['result']>;

const TYPE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  behavioral:  { bg: 'bg-state-info/10',    text: 'text-state-info',    label: 'Behavioral' },
  technical:   { bg: 'bg-purple-100',        text: 'text-purple-600',    label: 'Technical' },
  situational: { bg: 'bg-state-warning/10',  text: 'text-state-warning', label: 'Situational' },
  gap_focused: { bg: 'bg-primary-action/10',  text: 'text-primary-action', label: 'Gap-Focused' },
};

function QuestionCard({ q, index }: { q: PrepQuestion; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const sa = q.suggested_answer;
  const starKeys = ['situation', 'task', 'action', 'result'] as const;
  const hasStar = sa && starKeys.some((k) => sa[k]);
  const badge = TYPE_BADGE[q.question_type?.toLowerCase()] ?? { bg: 'bg-surface-subtle', text: 'text-text-muted', label: q.question_type };

  return (
    <div
      className="flex flex-col rounded-md border border-border-default overflow-hidden"
      data-testid={`question-card-${index}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-surface-subtle transition-colors"
        data-testid="expand-question"
      >
        <div className="flex items-start gap-2 min-w-0">
          <span className="shrink-0 text-sm font-medium text-text-muted">{index + 1}.</span>
          <span className="text-sm font-medium text-text-primary leading-snug">{q.text}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          <span className="text-xs text-text-muted">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-default px-4 py-4 flex flex-col gap-3 bg-surface-subtle">
          {hasStar ? (
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">Suggested STAR Answer</p>
              {starKeys.map((key) => {
                const val = sa?.[key as keyof typeof sa];
                if (!val) return null;
                return (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="shrink-0 font-semibold text-primary-action w-20 capitalize">{key}:</span>
                    <span className="text-text-primary leading-relaxed">{val as string}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-text-muted italic">No suggested answer provided.</p>
          )}
        </div>
      )}
    </div>
  );
}

function InterviewPrepContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');

  const [prep, setPrep] = useState<PrepResult | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, jobResult] = await Promise.allSettled([
        api.getApplication(jobId),
        api.getJob(jobId),
      ]);

      const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;
      const jobData = jobResult.status === 'fulfilled' ? jobResult.value : null;
      setJob(jobData);

      const resolvedArtifactId = hub?.artifacts.interview_prep?.artifact_id ?? queryId;
      const artifactStatus = hub?.artifacts.interview_prep?.status;

      if (!resolvedArtifactId || (artifactStatus && artifactStatus !== 'completed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      setArtifactId(resolvedArtifactId);

      try {
        const data = await api.getInterviewPrep(resolvedArtifactId);
        if (!data.result) {
          router.replace(`/applications/${jobId}`);
          return;
        }
        setPrep(data.result);
      } catch (err) {
        setError('Failed to load interview prep.');
        console.error(err);
        throw err;
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId, queryId, router]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Interview Prep…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
        {error}
      </div>
    );
  }

  const questions = prep?.questions ?? [];
  const questionsToAsk = prep?.questions_to_ask ?? [];
  const checklist = prep?.pre_interview_checklist ?? [];
  const salaryGuidance = prep?.salary_guidance;
  const CARD = 'rounded-md border border-border-default bg-card p-6 flex flex-col gap-4';
  const TITLE = 'text-base font-bold text-text-primary';

  return (
    <div className="flex flex-col gap-6" data-testid="interview-prep-page">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold text-text-primary">Interview Preparation</h1>
          {job && <p className="text-sm text-text-muted">{job.title} · {job.company_name}</p>}
          <p className="text-sm text-text-muted">{questions.length} question{questions.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {artifactId && (
            <ExportDropdown jobId={jobId} moduleType="interview_prep" artifactId={artifactId} companyName={job?.company_name ?? ''} jobTitle={job?.title ?? ''} />
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {questions.length > 0 && (
        <div className={CARD}>
          <h2 className={TITLE}>Interview Questions</h2>
          <div className="flex flex-col gap-2">
            {questions.map((q, i) => (
              <QuestionCard key={q.id ?? i} q={q} index={i} />
            ))}
          </div>
        </div>
      )}

      {questionsToAsk.length > 0 && (
        <div className={CARD}>
          <h2 className={TITLE}>Questions to Ask the Interviewer</h2>
          <div className="flex flex-col gap-4">
            {questionsToAsk.map((item, i) => (
              <div key={i} className="flex flex-col gap-1">
                <p className="text-sm font-medium text-text-primary">{item.question}</p>
                {item.purpose && <p className="text-xs text-text-muted italic">{item.purpose}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {checklist.length > 0 && (
        <div className={CARD}>
          <h2 className={TITLE}>Pre-Interview Checklist</h2>
          <div className="flex flex-col gap-2">
            {checklist.map((item, i) => (
              <label key={i} className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkedItems[i] ?? false}
                  onChange={() => setCheckedItems((prev) => ({ ...prev, [i]: !prev[i] }))}
                  className="mt-0.5 accent-primary-action"
                />
                <span className={`text-sm transition-colors ${checkedItems[i] ? 'line-through text-text-muted' : 'text-text-primary'}`}>
                  {item}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {salaryGuidance && (
        <div className={CARD}>
          <h2 className={TITLE}>Salary Guidance</h2>
          <p className="text-sm text-text-primary leading-relaxed">{salaryGuidance}</p>
        </div>
      )}

      {questions.length === 0 && questionsToAsk.length === 0 && checklist.length === 0 && (
        <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center text-sm text-text-muted">
          No interview prep content available.
        </div>
      )}
    </div>
  );
}

export default function InterviewPrepPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  return (
    <ErrorBoundary cloudwatchKey="interview-prep-page">
      <Suspense fallback={<div className="flex justify-center py-12"><Spinner size="lg" aria-label="Loading…" /></div>}>
        <InterviewPrepContent jobId={jobId} />
      </Suspense>
    </ErrorBoundary>
  );
}
