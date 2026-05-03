import React, { Suspense } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockPush = vi.fn();

const apiMocks = vi.hoisted(() => ({
  getGapQuestions: vi.fn(),
  getApplication: vi.fn(),
  getCV: vi.fn(),
  generateGapQuestions: vi.fn(),
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

function renderWithSuspense(ui: React.ReactElement) {
  return render(<Suspense fallback={<div data-testid="suspense-fallback" />}>{ui}</Suspense>);
}

const QUESTIONS = [
  { question_id: 'q1', question: 'Describe your Python experience', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
  { question_id: 'q2', question: 'How have you handled deadlines?', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
  { question_id: 'q3', question: 'Describe a leadership situation', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
];

const HUB_WITH_CV = {
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
    apiMocks.getApplication.mockResolvedValue(HUB_WITH_CV);
    apiMocks.getCV.mockResolvedValue({ cv_id: 'cv1', user_id: 'u1', full_name: 'Jane', language: 'en', contact_info: {}, experience: [], education: [], skills: [], certifications: [], top_achievements: [], languages: [] });
  });

  it('renders 3 question rows with impact badges', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(QUESTIONS);

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-row-0')).toBeDefined();
      expect(screen.getByTestId('question-row-1')).toBeDefined();
      expect(screen.getByTestId('question-row-2')).toBeDefined();
    });

    // HIGH impact badge should be visible
    const badges = screen.getAllByText(/Impact: HIGH/);
    expect(badges.length).toBeGreaterThan(0);
  });

  it('save button calls saveGapResponses with filled responses', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(QUESTIONS.slice(0, 2));
    apiMocks.saveGapResponses.mockResolvedValue(undefined);

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    // Wait for questions to render (page starts in edit mode when no saved responses)
    await waitFor(() => {
      expect(screen.getByTestId('question-row-0')).toBeDefined();
    });

    // Fill in answers
    const textareas = screen.getAllByPlaceholderText('Your answer…');
    fireEvent.change(textareas[0], { target: { value: 'Answer 1' } });
    fireEvent.change(textareas[1], { target: { value: 'Answer 2' } });

    // Click Save
    fireEvent.click(screen.getByTestId('save-responses'));

    await waitFor(() => {
      expect(apiMocks.saveGapResponses).toHaveBeenCalledWith('job1', expect.arrayContaining([
        expect.objectContaining({ question_id: 'q1', response: 'Answer 1' }),
        expect.objectContaining({ question_id: 'q2', response: 'Answer 2' }),
      ]));
    });
  });

  it('shows generate button when no questions and CV exists', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);

    const { default: GapPage } = await import('../../app/applications/[id]/gap-analysis/page');
    renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('generate-gap-questions')).toBeDefined();
    });
  });
});
