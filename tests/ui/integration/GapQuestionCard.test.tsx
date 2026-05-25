// spec_id: FE-UI-019
// Component: GapQuestionCard
// File: src/frontend/components/GapQuestionCard/GapQuestionCard.tsx
// Route: /applications/[id]/gap-analysis
// Focus: component rendered within page context; state transitions; API interaction via parent

import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { GapQuestion } from '../../../src/frontend/lib/types';

// ─── API client mock (module level — not hook level) ──────────────────────────
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
  useParams: jest.fn(() => ({ id: 'job-int-01' })),
}));

// Mock RichTextEditor to keep integration tests focused on card behaviour
jest.mock('../../../src/frontend/components/RichTextEditor/RichTextEditor', () => ({
  RichTextEditor: ({
    value,
    readOnly,
    onChange,
    ariaLabelledBy,
  }: {
    value: string;
    readOnly?: boolean;
    onChange?: (v: string) => void;
    ariaLabelledBy?: string;
  }) => (
    <textarea
      data-testid="rich-text-editor"
      data-readonly={String(readOnly ?? false)}
      value={value}
      readOnly={readOnly}
      onChange={(e) => onChange?.(e.target.value)}
      aria-labelledby={ariaLabelledBy}
    />
  ),
}));

import { api } from '../../../src/frontend/api/methods';

const mockApi = api as {
  getGapQuestions: jest.Mock;
  getApplication: jest.Mock;
  saveGapResponses: jest.Mock;
};

// ─── Fixtures ──────────────────────────────────────────────────────────────────
const ONE_QUESTION: GapQuestion[] = [
  {
    question_id: 'q1',
    question: 'Describe your Python experience',
    impact: 'HIGH',
    probability: 'MEDIUM',
    gap_score: 8,
    tags: [],
  },
];

const HUB_STUB = {
  application: { application_id: 'job-int-01', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job-int-01', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
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

async function renderGapPage() {
  const { default: GapPage } = await import(
    '../../../src/frontend/app/applications/[id]/gap-analysis/page'
  );
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <GapPage params={Promise.resolve({ id: 'job-int-01' })} />
    </Wrapper>,
  );
}

// ─── Tests ─────────────────────────────────────────────────────────────────────
describe('GapQuestionCard integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
    mockApi.getApplication.mockResolvedValue(HUB_STUB);
  });

  // ─── State transition: loading → data rendered ────────────────────────────────

  it('test_renders_question_card_when_api_succeeds', async () => {
    mockApi.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: assert card is visible
    // TODO: assert screen.queryByRole('alert') is null
  });

  it('test_transitions_from_loading_to_data_when_api_resolves', async () => {
    let resolveQuestions!: (v: typeof ONE_QUESTION) => void;
    mockApi.getGapQuestions.mockReturnValue(
      new Promise<typeof ONE_QUESTION>((resolve) => { resolveQuestions = resolve; }),
    );
    await renderGapPage();
    // TODO: assert loading state is shown (skeleton or suspense fallback visible)
    resolveQuestions(ONE_QUESTION);
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: assert loading indicator is no longer present
  });

  // ─── State transition: API error → error state rendered ───────────────────────

  it('test_shows_error_state_when_get_gap_questions_api_fails', async () => {
    mockApi.getGapQuestions.mockRejectedValue(new Error('500 Internal Server Error'));
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByRole('alert'))
    // TODO: assert no gap-question-card elements are in the document
  });

  // ─── User action → API call triggered → UI updates ───────────────────────────

  it('test_save_action_on_card_calls_post_gap_responses_api', async () => {
    mockApi.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: click Answer button on card 0 to request edit (onRequestEdit)
    //   fireEvent.click(screen.getByRole('button', { name: /answer/i }))
    // TODO: await waitFor(() => screen.getByTestId('rich-text-editor'))
    // TODO: fireEvent.change editor to set value 'My integration answer'
    // TODO: fireEvent.click save button
    // TODO: await waitFor(() =>
    //   expect(mockApi.saveGapResponses).toHaveBeenCalledWith(
    //     'job-int-01',
    //     expect.arrayContaining([
    //       expect.objectContaining({ question_id: 'q1', response: 'My integration answer' }),
    //     ]),
    //   )
    // )
  });

  it('test_card_exits_edit_mode_after_successful_save', async () => {
    mockApi.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: request edit on card 0 and fill in a response
    // TODO: click save
    // TODO: await waitFor(() => screen.queryByTestId('rich-text-editor') === null)
    // TODO: assert saved response text is now shown in the read view
  });

  it('test_card_shows_inline_error_when_save_api_call_fails', async () => {
    mockApi.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    mockApi.saveGapResponses.mockRejectedValue(new Error('Save failed'));
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: request edit, fill response, click save
    // TODO: await waitFor(() => screen.getByText('Failed to save. Please try again.'))
    // TODO: assert the card remains in editing state (RichTextEditor still visible)
  });

  // ─── Multi-editor guard: only one card in edit mode at a time ─────────────────

  it('test_only_one_card_in_editing_state_at_a_time', async () => {
    const twoQuestions: GapQuestion[] = [
      { ...ONE_QUESTION[0] },
      { question_id: 'q2', question: 'Describe leadership experience', impact: 'MEDIUM', probability: 'LOW', gap_score: 5, tags: [] },
    ];
    mockApi.getGapQuestions.mockResolvedValue(twoQuestions);
    await renderGapPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: click Answer on card 0 (onRequestEdit for card 0)
    // TODO: assert card 0 is in editing state
    // TODO: click Answer on card 1 (onRequestEdit for card 1)
    // TODO: assert card 0 is NO LONGER in editing state (parent guard released it)
    // TODO: assert card 1 is in editing state
  });

  // ─── Destination default sent to API ─────────────────────────────────────────

  it('test_post_payload_includes_cv_impact_destination_when_advanced_never_opened', async () => {
    mockApi.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    mockApi.saveGapResponses.mockResolvedValue(undefined);
    await renderGapPage();
    // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
    // TODO: request edit, fill response, click save WITHOUT opening Advanced section
    // TODO: await waitFor(() =>
    //   expect(mockApi.saveGapResponses).toHaveBeenCalledWith(
    //     'job-int-01',
    //     expect.arrayContaining([
    //       expect.objectContaining({ destination: 'CV_IMPACT' }),
    //     ]),
    //   )
    // )
  });

});
