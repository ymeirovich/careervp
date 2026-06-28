import React, { Suspense } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const mockPush = vi.fn();

const apiMocks = vi.hoisted(() => ({
  getGapQuestions: vi.fn(),
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
    apiMocks.getGapQuestions.mockResolvedValue(QUESTIONS);

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-row-0')).toBeDefined();
      expect(screen.getByTestId('question-row-1')).toBeDefined();
      expect(screen.getByTestId('question-row-2')).toBeDefined();
    });
  });

  it('shows empty state when no questions are returned', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeDefined();
    });
  });

  it('shows error banner when getGapQuestions rejects', async () => {
    apiMocks.getGapQuestions.mockRejectedValue(new Error('Network error'));

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeDefined();
    });
  });
});
