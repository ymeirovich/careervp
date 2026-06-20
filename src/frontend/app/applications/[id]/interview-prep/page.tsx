'use client';

import React, { useState, useEffect, use, Suspense, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ArtifactAutosaveField } from '../../../../components/ArtifactAutosaveField';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { RichTextEditor } from '../../../../components/RichTextEditor/RichTextEditor';
import { Spinner } from '../../../../components/ui/Spinner';
import type { ArtifactAutosaveResult, ArtifactBaseVersion } from '../../../../hooks/useArtifactAutosave';
import type { JobDetail, PrepQuestion } from '../../../../lib/types';

type PrepResult = NonNullable<Awaited<ReturnType<typeof api.getInterviewPrep>>['result']>;

const TYPE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  behavioral: { bg: 'bg-state-info/10', text: 'text-state-info', label: 'Behavioral' },
  technical: { bg: 'bg-surface-subtle', text: 'text-text-primary', label: 'Technical' },
  situational: { bg: 'bg-state-warning/10', text: 'text-state-warning', label: 'Situational' },
  gap_focused: { bg: 'bg-primary-action/10', text: 'text-primary-action', label: 'Gap-Focused' },
};

function clonePrepResult(result: PrepResult): PrepResult {
  return JSON.parse(JSON.stringify(result)) as PrepResult;
}

function serializeSuggestedAnswer(answer?: PrepQuestion['suggested_answer']): string {
  if (!answer) return '';
  if (answer.full_text?.trim()) return answer.full_text.trim();

  const sections = [
    answer.situation ? `**Situation:** ${answer.situation}` : '',
    answer.task ? `**Task:** ${answer.task}` : '',
    answer.action ? `**Action:** ${answer.action}` : '',
    answer.result ? `**Result:** ${answer.result}` : '',
  ].filter(Boolean);

  return sections.join('\n\n');
}

function getQuestionAnswer(question: PrepQuestion): string {
  return question.answer?.trim() ? question.answer : serializeSuggestedAnswer(question.suggested_answer);
}

function getQuestionId(question: PrepQuestion): string {
  return question.id;
}

function updateQuestion(result: PrepResult, questionId: string, updater: (question: PrepQuestion) => void): PrepResult {
  const next = clonePrepResult(result);
  next.questions = next.questions?.map((question) => {
    if (getQuestionId(question) !== questionId) return question;
    const updatedQuestion = { ...question };
    updater(updatedQuestion);
    return updatedQuestion;
  }) ?? [];
  return next;
}

interface QuestionCardProps {
  artifactId: string | null;
  question: PrepQuestion;
  baselineQuestion: PrepQuestion;
  index: number;
  onQuestionChange: (questionId: string, answer: string) => void;
  onQuestionSaved: (questionId: string, answer: string, version: ArtifactBaseVersion, updatedAt: string | null) => void;
  fetchLatestQuestion: (questionId: string) => Promise<{ question: PrepQuestion; updatedAt: string | null }>;
}

function QuestionCard({
  artifactId,
  question,
  baselineQuestion,
  index,
  onQuestionChange,
  onQuestionSaved,
  fetchLatestQuestion,
}: QuestionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const questionId = getQuestionId(question);
  const answer = getQuestionAnswer(question);
  const baselineAnswer = getQuestionAnswer(baselineQuestion);
  const badge = TYPE_BADGE[question.question_type?.toLowerCase()] ?? {
    bg: 'bg-surface-subtle',
    text: 'text-text-muted',
    label: question.question_type,
  };

  return (
    <div className="flex flex-col rounded-md border border-border-default overflow-hidden" data-testid={`question-card-${index}`}>
      <button
        onClick={() => setExpanded((current) => !current)}
        className="flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-surface-subtle transition-colors"
        data-testid="expand-question"
      >
        <div className="flex items-start gap-2 min-w-0">
          <span className="shrink-0 text-sm font-medium text-text-muted">{index + 1}.</span>
          <span className="text-sm font-medium text-text-primary leading-snug">{question.text}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          <span className="text-xs text-text-muted">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-default px-4 py-4 flex flex-col gap-4 bg-surface-subtle">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
              {question.answer?.trim() ? 'STAR Answer' : 'Suggested STAR Answer'}
            </p>
            <button
              type="button"
              onClick={() => setIsEditing((current) => !current)}
              className="rounded-md border border-border-default px-3 py-1.5 text-sm text-text-primary hover:bg-card"
            >
              {isEditing ? 'Done' : 'Edit'}
            </button>
          </div>

          <ArtifactAutosaveField
            artifactType="interview_prep"
            artifactId={artifactId}
            fieldKey={`question.${questionId}.answer`}
            value={answer}
            baseline={baselineAnswer}
            onValueChange={(value) => onQuestionChange(questionId, value)}
            serverUpdatedAt={question.answer_updated_at ?? null}
            baseVersion={question.answer_version ?? null}
            save={async (value, context) => {
              if (!artifactId) {
                return {
                  value,
                  baseVersion: context.baseVersion,
                  updatedAt: question.answer_updated_at ?? null,
                };
              }

              const response = await api.patchInterviewPrep(artifactId, {
                question_id: questionId,
                answer: value,
                base_version: context.baseVersion,
              });

              return {
                value: response.answer ?? value,
                baseVersion: response.answer_version ?? context.baseVersion ?? null,
                updatedAt: response.answer_updated_at ?? new Date().toISOString(),
              };
            }}
            onSaved={(result) => {
              onQuestionSaved(questionId, result.value, result.baseVersion ?? null, result.updatedAt ?? null);
            }}
            fetchLatest={async () => {
              const latest = await fetchLatestQuestion(questionId);
              return {
                value: getQuestionAnswer(latest.question),
                baseVersion: latest.question.answer_version ?? null,
                updatedAt: latest.question.answer_updated_at ?? latest.updatedAt,
              };
            }}
            onReloaded={(result) => {
              onQuestionSaved(questionId, result.value, result.baseVersion ?? null, result.updatedAt ?? null);
            }}
            onRequestEdit={() => setIsEditing(true)}
            renderField={({ isSaving, onBlur }) => (
              isEditing ? (
                <div className="flex flex-col gap-3">
                  <RichTextEditor
                    content={answer}
                    onChange={(value) => onQuestionChange(questionId, value)}
                    onBlur={onBlur}
                    readOnly={isSaving}
                    placeholder="Write your STAR answer…"
                  />
                  <div className="flex items-center justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => undefined}
                      className="rounded-md border border-border-default px-3 py-1.5 text-sm text-text-primary hover:bg-card"
                    >
                      AI Assist
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onQuestionChange(questionId, baselineAnswer);
                        setIsEditing(false);
                      }}
                      className="text-sm text-text-muted hover:text-text-primary"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : answer ? (
                <RichTextEditor content={answer} onChange={() => undefined} readOnly />
              ) : (
                <p className="text-sm text-text-muted italic">No answer available yet.</p>
              )
            )}
          />
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
  const [baselinePrep, setBaselinePrep] = useState<PrepResult | null>(null);
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
        const cloned = clonePrepResult(data.result);
        setPrep(cloned);
        setBaselinePrep(clonePrepResult(data.result));
      } catch (loadError) {
        setError('Failed to load interview prep.');
        console.error(loadError);
        throw loadError;
      } finally {
        setLoading(false);
      }
    };

    void init();
  }, [jobId, queryId, router]);

  const onQuestionChange = useCallback((questionId: string, answer: string) => {
    setPrep((current) => (current ? updateQuestion(current, questionId, (question) => {
      question.answer = answer;
    }) : current));
  }, []);

  const onQuestionSaved = useCallback((questionId: string, answer: string, version: ArtifactBaseVersion, updatedAt: string | null) => {
    setPrep((current) => (current ? updateQuestion(current, questionId, (question) => {
      question.answer = answer;
      question.answer_version = typeof version === 'number' ? version : question.answer_version;
      question.answer_updated_at = updatedAt;
    }) : current));
    setBaselinePrep((current) => (current ? updateQuestion(current, questionId, (question) => {
      question.answer = answer;
      question.answer_version = typeof version === 'number' ? version : question.answer_version;
      question.answer_updated_at = updatedAt;
    }) : current));
  }, []);

  const fetchLatestQuestion = useCallback(async (questionId: string) => {
    if (!artifactId) {
      const fallback = prep?.questions?.find((question) => getQuestionId(question) === questionId);
      if (!fallback) {
        throw new Error('Question not found');
      }
      return {
        question: fallback,
        updatedAt: fallback.answer_updated_at ?? null,
      };
    }

    const latest = await api.getInterviewPrep(artifactId);
    const latestQuestion = latest.result?.questions?.find((question) => getQuestionId(question) === questionId);
    if (!latestQuestion) {
      throw new Error('Question not found');
    }

    return {
      question: latestQuestion,
      updatedAt: latest.updated_at ?? null,
    };
  }, [artifactId, prep]);

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
  const baselineQuestions = baselinePrep?.questions ?? [];
  const questionsToAsk = prep?.questions_to_ask ?? [];
  const checklist = prep?.pre_interview_checklist ?? [];
  const salaryGuidance = prep?.salary_guidance;
  const cardClassName = 'rounded-md border border-border-default bg-card p-6 flex flex-col gap-4';
  const titleClassName = 'text-base font-bold text-text-primary';

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
        <div className={cardClassName}>
          <h2 className={titleClassName}>Interview Questions</h2>
          <div className="flex flex-col gap-3">
            {questions.map((question, index) => (
              <QuestionCard
                key={getQuestionId(question)}
                artifactId={artifactId}
                baselineQuestion={baselineQuestions[index] ?? question}
                fetchLatestQuestion={fetchLatestQuestion}
                index={index}
                onQuestionChange={onQuestionChange}
                onQuestionSaved={onQuestionSaved}
                question={question}
              />
            ))}
          </div>
        </div>
      )}

      {questionsToAsk.length > 0 && (
        <div className={cardClassName}>
          <h2 className={titleClassName}>Questions to Ask the Interviewer</h2>
          <div className="flex flex-col gap-4">
            {questionsToAsk.map((item, index) => (
              <div key={`${item.question}-${index}`} className="flex flex-col gap-1">
                <p className="text-sm font-medium text-text-primary">{item.question}</p>
                {item.purpose && <p className="text-xs text-text-muted italic">{item.purpose}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {checklist.length > 0 && (
        <div className={cardClassName}>
          <h2 className={titleClassName}>Pre-Interview Checklist</h2>
          <div className="flex flex-col gap-2">
            {checklist.map((item, index) => (
              <label key={`${item}-${index}`} className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkedItems[index] ?? false}
                  onChange={() => setCheckedItems((current) => ({ ...current, [index]: !current[index] }))}
                  className="mt-0.5 accent-primary-action"
                />
                <span className={`text-sm transition-colors ${checkedItems[index] ? 'line-through text-text-muted' : 'text-text-primary'}`}>
                  {item}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {salaryGuidance && (
        <div className={cardClassName}>
          <h2 className={titleClassName}>Salary Guidance</h2>
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
