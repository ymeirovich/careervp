// spec_id: FE-UI-018
// Component: GapAnalysisContent (default export of gap-analysis/page.tsx)
// Route: /applications/[id]/gap-analysis
// ACs covered: AC-015  (verification_type: integration)
// Focus: per-question save triggers POST, local state updates, editingQuestionId resets

import React, { Suspense } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ─── API client mock (at module level, not hook level) ────────────────────────
jest.mock('../../../src/frontend/api/methods', () => ({
  api: {
    getGapQuestions: jest.fn(),
    getApplication: jest.fn(),
    saveGapResponses: jest.fn(),
  },
}));

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn() })),
  useSearchParams: jest.fn(() => ({ get: (_k: string) => null })),
  useParams: jest.fn(() => ({ id: 'job-456' })),
}));

import { api } from '../../../src/frontend/api/methods';

const mockApi = api as {
  getGapQuestions: jest.Mock;
  getApplication: jest.Mock;
  saveGapResponses: jest.Mock;
};

// ─── Test fixtures ─────────────────────────────────────────────────────────────
const THREE_QUESTIONS = [
  { question_id: 'q1', question: 'Q1 text', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
  { question_id: 'q2', question: 'Q2 text', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
  { question_id: 'q3', question: 'Q3 text', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
];

const HUB_STUB = {
  application: { application_id: 'job-456', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job-456', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
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

// ─── Provider wrapper ─────────────────────────────────────────────────────────
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<div data-testid="suspense-fallback" />}>
        {children}
      </Suspense>
    </QueryClientProvider>
  );
};

async function renderPage() {
  const { default: GapPage } = await import('../../../src/frontend/app/applications/[id]/gap-analysis/page');
  const wrapper = createWrapper();
  return render(
    <wrapper.type>
      <GapPage params={Promise.resolve({ id: 'job-456' })} />
    </wrapper.type>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('GapAnalysisContent integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
    mockApi.getApplication.mockResolvedValue(HUB_STUB);
  });

  // ─── AC-015: per-question save → POST → state update → editingQuestionId reset

  it('test_renders_questions_when_api_succeeds', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert 3 question cards are rendered
    // TODO: assert screen.queryByTestId('error-banner') is null
  });

  it('test_shows_error_state_when_get_gap_questions_api_fails', async () => {
    mockApi.getGapQuestions.mockRejectedValue(new Error('500 Internal Server Error'));
    await renderPage();
    // TODO: await waitFor(() => screen.getByRole('alert'))
    // TODO: assert error banner is visible
    // TODO: assert screen.queryByTestId(/gap-question-card/) is null
  });

  it('test_post_gap_responses_called_with_single_question_payload_when_save_triggered', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: simulate GapQuestionCard calling onSave('q1', 'My response text')
    //        e.g. fireEvent.click(screen.getByTestId('save-btn-q1'))
    //        or invoke onSave prop directly via a test handle
    // TODO: await waitFor(() =>
    //   expect(mockApi.saveGapResponses).toHaveBeenCalledWith(
    //     'job-456',
    //     [{ question_id: 'q1', response: 'My response text' }],
    //   )
    // )
  });

  it('test_editing_question_id_resets_to_null_after_successful_save', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: put card-0 into editing state (simulate onRequestEdit call)
    // TODO: assert card-0 data-is-editing === 'true'
    // TODO: trigger onSave on card-0
    // TODO: await waitFor(() => card-0 data-is-editing === 'false')
  });

  it('test_local_response_state_updates_after_successful_save', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: trigger onSave('q1', 'Updated answer')
    // TODO: await waitFor(() =>
    //   screen.getByText('Updated answer')   -- or assert response prop on card-0 changed
    // )
  });

  it('test_error_banner_still_visible_and_save_not_called_when_api_initially_failed', async () => {
    mockApi.getGapQuestions.mockRejectedValue(new Error('Network error'));
    await renderPage();
    // TODO: await waitFor(() => screen.getByRole('alert'))
    // TODO: assert mockApi.saveGapResponses has not been called
    // TODO: assert no GapQuestionCard is in the document
  });

  // ─── State transition: loading → data ─────────────────────────────────────────

  it('test_transitions_from_loading_to_data_state_when_api_resolves', async () => {
    let resolveQuestions!: (value: typeof THREE_QUESTIONS) => void;
    mockApi.getGapQuestions.mockReturnValue(
      new Promise<typeof THREE_QUESTIONS>((resolve) => { resolveQuestions = resolve; }),
    );
    await renderPage();
    // TODO: assert loading skeletons visible initially (screen.getByTestId(/skeleton/))
    resolveQuestions(THREE_QUESTIONS);
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert skeletons are no longer present
  });

  // ─── State transition: data → error (retry path) ──────────────────────────────

  it('test_transitions_from_data_to_error_state_when_save_fails', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    mockApi.saveGapResponses.mockRejectedValue(new Error('Save failed'));
    await renderPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: trigger onSave on card-0
    // TODO: await waitFor(() => screen.getByRole('alert'))
    //        OR assert an inline save-error message is shown on the card
  });

  // ─── AC-015 edge: POST payload shape per API contract ─────────────────────────

  it('test_post_payload_contains_question_id_and_response_fields_when_save_called', async () => {
    mockApi.getGapQuestions.mockResolvedValue(THREE_QUESTIONS);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: trigger onSave('q2', 'Answer for q2')
    // TODO: await waitFor(() => expect(mockApi.saveGapResponses).toHaveBeenCalledWith(
    //   'job-456',
    //   expect.arrayContaining([
    //     expect.objectContaining({ question_id: 'q2', response: 'Answer for q2' }),
    //   ]),
    // ))
  });

});
