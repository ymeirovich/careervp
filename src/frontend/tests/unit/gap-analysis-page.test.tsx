import React, { Suspense } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';

const mockPush = vi.fn();

const apiMocks = vi.hoisted(() => ({
  getGapQuestionsStatus: vi.fn(),
  getApplication: vi.fn(),
  getCV: vi.fn(),
  saveGapResponses: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job1' }),
}));

vi.mock('../../api/methods', () => ({
  api: apiMocks,
}));

vi.mock('../../components/GapQuestionCard/GapQuestionCard', () => ({
  GapQuestionCard: (props: { question: { question_id: string; question: string }; questionIndex: number }) => (
    <div data-testid={`question-row-${props.questionIndex}`}>
      {props.question.question}
    </div>
  ),
}));

function renderWithSuspense(ui: React.ReactElement) {
  return render(<Suspense fallback={<div data-testid="suspense-fallback" />}>{ui}</Suspense>);
}

const QUESTIONS = [
  { question_id: 'q1', question: 'Describe your Python experience', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
  { question_id: 'q2', question: 'How have you handled deadlines?', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
  { question_id: 'q3', question: 'Describe a leadership situation', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
];

type GapStatus = 'pending' | 'processing' | 'completed' | 'failed';

function statusOf(questions: typeof QUESTIONS, status: GapStatus = 'completed') {
  return { job_id: 'job1', cv_id: 'cv1', status, questions };
}

const HUB_EMPTY = {
  application: { application_id: 'job1', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job1', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
  cv: { cv_id: 'cv1' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'pending' as const, artifact_id: null },
    cover_letter: { status: 'pending' as const, artifact_id: null },
    interview_prep: { status: 'pending' as const, artifact_id: null },
    cv_tailored: { status: 'pending' as const, artifact_id: null },
    gap_analysis: { status: 'pending' as const, artifact_id: null },
  },
};

describe('Gap Analysis page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(HUB_EMPTY);
  });

  it('renders 3 question rows after loading', async () => {
    apiMocks.getGapQuestionsStatus.mockResolvedValue(statusOf(QUESTIONS));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-row-0')).toBeDefined();
      expect(screen.getByTestId('question-row-1')).toBeDefined();
      expect(screen.getByTestId('question-row-2')).toBeDefined();
    });
  });

  it('shows empty state when generation completed with no questions', async () => {
    apiMocks.getGapQuestionsStatus.mockResolvedValue(statusOf([]));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeDefined();
    });
  });

  it('shows a generating state (not the empty state) while status is pending', async () => {
    apiMocks.getGapQuestionsStatus.mockResolvedValue(statusOf([], 'pending'));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('generating-state')).toBeDefined();
    });
    expect(screen.queryByTestId('empty-state')).toBeNull();
  });

  it('shows a failed banner when generation status is failed', async () => {
    apiMocks.getGapQuestionsStatus.mockResolvedValue(statusOf([], 'failed'));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('generation-failed-banner')).toBeDefined();
    });
    expect(screen.queryByTestId('empty-state')).toBeNull();
  });

  it('shows error banner when getGapQuestionsStatus rejects', async () => {
    apiMocks.getGapQuestionsStatus.mockRejectedValue(new Error('Network error'));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeDefined();
    });
  });

  // Regression for the 2026-09-22 production incident: a job that took longer
  // than one poll interval to leave 'processing' left the page stuck showing
  // "Generating..." forever, even though the backend had already finished.
  // Root cause: polling was re-armed by a useEffect keyed on generationStatus
  // state, which React does not re-run when consecutive polls return the SAME
  // status string — exactly what happens whenever a real LLM call outlives a
  // single 3s tick. gap-api logs showed 2 requests (both 'processing') then
  // silence for the rest of an 8-minute test window.
  it('keeps polling through repeated identical in-progress statuses until the job completes', async () => {
    vi.useFakeTimers();
    try {
      apiMocks.getGapQuestionsStatus
        .mockResolvedValueOnce(statusOf([], 'processing'))
        .mockResolvedValueOnce(statusOf([], 'processing')) // same value as the previous poll
        .mockResolvedValueOnce(statusOf([], 'processing')) // same value again — the trap
        .mockResolvedValueOnce(statusOf(QUESTIONS, 'completed'));

      const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
      await act(async () => {
        renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);
      });

      expect(apiMocks.getGapQuestionsStatus).toHaveBeenCalledTimes(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(apiMocks.getGapQuestionsStatus).toHaveBeenCalledTimes(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(apiMocks.getGapQuestionsStatus).toHaveBeenCalledTimes(3);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(apiMocks.getGapQuestionsStatus).toHaveBeenCalledTimes(4);

      expect(screen.getByTestId('questions-list')).toBeDefined();
      expect(screen.queryByTestId('generating-state')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});
