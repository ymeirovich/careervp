'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { GapQuestionCard } from '../../../../components/GapQuestionCard/GapQuestionCard';
import { ProgressBar } from '../../../../components/ui/ProgressBar';
import type { GapQuestion } from '../../../../lib/types';

type Locale = 'en' | 'he';

type Copy = {
  title: string;
  subtitle: string;
  back: string;
  progressLabel: (answered: number, total: number) => string;
  emptyStateMsg: string;
  backToHub: string;
  errorBanner: string;
  retry: string;
  guardMsg: (questionNumber: number) => string;
};

const TEXT: Record<Locale, Copy> = {
  en: {
    title: 'Gap Analysis Questions',
    subtitle: 'Answer some questions to fill in gaps between your CV and this role',
    back: '← Back',
    progressLabel: (answered, total) => `${answered} out of ${total} answered`,
    emptyStateMsg: 'There was an error, contact site administrator.',
    backToHub: 'Back to Hub',
    errorBanner: 'Failed to load questions.',
    retry: 'Retry',
    guardMsg: (n) => `Save or discard changes to question ${n}?`,
  },
  he: {
    title: 'שאלות ניתוח פערים',
    subtitle: 'ענה על כמה שאלות כדי למלא את הפערים בין קורות החיים שלך לתפקיד זה',
    back: '← חזרה',
    progressLabel: (answered, total) => `${answered} מתוך ${total} נענו`,
    emptyStateMsg: 'אירעה שגיאה, צור קשר עם מנהל האתר.',
    backToHub: 'חזרה למרכז',
    errorBanner: 'טעינת השאלות נכשלה.',
    retry: 'נסה שוב',
    guardMsg: (n) => `שמור או בטל שינויים לשאלה ${n}?`,
  },
};

function detectLocale(): Locale {
  if (typeof window !== 'undefined') {
    const locale = new URLSearchParams(window.location.search).get('locale');
    if (locale?.toLowerCase().startsWith('he')) return 'he';
  }
  if (typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he')) {
    return 'he';
  }
  return 'en';
}

type LocalResponse = {
  response: string;
  destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '';
};

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border-default shadow-sm p-4 bg-card animate-pulse">
      <div className="flex items-start gap-2">
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-surface-subtle rounded w-3/4" />
          <div className="h-3 bg-surface-subtle rounded w-1/2" />
        </div>
        <div className="h-8 w-16 bg-surface-subtle rounded-md shrink-0" />
      </div>
    </div>
  );
}

function GapAnalysisContent({ jobId }: { jobId: string }) {
  const locale = detectLocale();
  const copy = TEXT[locale];

  const [questions, setQuestions] = useState<GapQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, LocalResponse>>({});
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  const fetchQuestions = useCallback(async () => {
    setLoading(true);
    setFetchError(false);

    const [questionsResult, hubResult] = await Promise.allSettled([
      api.getGapQuestions(jobId),
      api.getApplication(jobId),
    ]);

    if (questionsResult.status === 'rejected') {
      setFetchError(true);
      setLoading(false);
      return;
    }

    const qs = questionsResult.value;
    const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;

    setQuestions(qs);

    const map: Record<string, LocalResponse> = {};
    for (const r of hub?.gap_analysis.responses ?? []) {
      const entry = r as Record<string, unknown>;
      map[r.question_id] = {
        response: String(entry.response ?? entry.answer ?? ''),
        destination: (entry.destination as 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY') ?? '',
      };
    }
    setResponses(map);
    setLoading(false);
  }, [jobId]);

  useEffect(() => {
    void fetchQuestions();
  }, [fetchQuestions]);

  const handleRequestEdit = (questionId: string) => {
    if (editingQuestionId !== null && editingQuestionId !== questionId) {
      const idx = questions.findIndex((q) => q.question_id === editingQuestionId);
      if (!window.confirm(copy.guardMsg(idx + 1))) return;
    }
    setEditingQuestionId(questionId);
  };

  const handleSave = async (data: {
    questionId: string;
    response: string;
    destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY';
  }) => {
    await api.saveGapResponses(jobId, [{ question_id: data.questionId, response: data.response }]);
    setResponses((prev) => ({
      ...prev,
      [data.questionId]: { response: data.response, destination: data.destination },
    }));
    setEditingQuestionId(null);
  };

  const handleCancel = () => {
    setEditingQuestionId(null);
  };

  const answeredCount = questions.filter((q) => responses[q.question_id]?.response?.trim()).length;
  const progressValue = questions.length > 0 ? (answeredCount / questions.length) * 100 : 0;
  const progressLabel = copy.progressLabel(answeredCount, questions.length);

  return (
    <div className="flex flex-col gap-6" data-testid="gap-analysis-page">
      <div className="flex flex-col gap-1">
        <Link
          href={`/applications/${jobId}`}
          className="text-sm text-text-secondary hover:text-text-primary w-fit"
          data-testid="back-link"
        >
          {copy.back}
        </Link>
        <h1 className="text-2xl font-bold text-text-primary" data-testid="page-title">
          {copy.title}
        </h1>
        <p className="text-sm text-text-muted" data-testid="page-subtitle">
          {copy.subtitle}
        </p>
      </div>

      {loading && (
        <div className="flex flex-col gap-4" data-testid="skeleton-cards">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!loading && fetchError && (
        <div
          className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 flex items-center justify-between gap-4"
          role="alert"
          data-testid="error-banner"
        >
          <span className="text-sm text-state-error">{copy.errorBanner}</span>
          <button
            onClick={() => void fetchQuestions()}
            className="text-sm font-medium text-state-error underline hover:no-underline shrink-0"
            data-testid="retry-button"
          >
            {copy.retry}
          </button>
        </div>
      )}

      {!loading && !fetchError && questions.length === 0 && (
        <div
          className="rounded-xl border border-border-default bg-card px-6 py-12 text-center"
          data-testid="empty-state"
        >
          <p className="text-sm text-text-muted mb-3" data-testid="empty-state-message">
            {copy.emptyStateMsg}
          </p>
          <Link
            href={`/applications/${jobId}`}
            className="text-sm font-medium text-primary-action hover:underline"
            data-testid="empty-back-link"
          >
            {copy.backToHub}
          </Link>
        </div>
      )}

      {!loading && !fetchError && questions.length > 0 && (
        <>
          <div className="flex flex-col gap-1" data-testid="progress-section">
            <span className="text-sm text-text-secondary" data-testid="progress-label">
              {progressLabel}
            </span>
            <ProgressBar value={progressValue} label={progressLabel} color="primary" />
          </div>

          <div className="flex flex-col gap-4" data-testid="questions-list">
            {questions.map((q, i) => {
              const r = responses[q.question_id];
              return (
                <GapQuestionCard
                  key={q.question_id}
                  question={q}
                  questionIndex={i}
                  response={r?.response ?? null}
                  destination={r?.destination ?? ''}
                  isEditing={editingQuestionId === q.question_id}
                  onRequestEdit={() => handleRequestEdit(q.question_id)}
                  onSave={handleSave}
                  onCancel={handleCancel}
                />
              );
            })}
          </div>
        </>
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
