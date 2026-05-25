// spec_id: FE-UI-018
// Component: GapAnalysisContent (default export of gap-analysis/page.tsx)
// Route: /applications/[id]/gap-analysis
// ACs covered: AC-001 – AC-014, AC-016  (all verification_type: unit)

import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── Hoisted API mocks (must be before any static imports) ────────────────────
const apiMocks = vi.hoisted(() => ({
  getGapQuestions: vi.fn(),
  getApplication: vi.fn(),
  saveGapResponses: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job-123' }),
}));

vi.mock('../../../src/frontend/api/methods', () => ({
  api: apiMocks,
}));

// GapQuestionCard and ProgressBar are child components; mock them to isolate GapAnalysisContent
vi.mock('../../../src/frontend/components/GapQuestionCard/GapQuestionCard', () => ({
  GapQuestionCard: (props: {
    question: { question_id: string; question: string };
    questionIndex: number;
    response: string | null;
    isEditing: boolean;
    onRequestEdit: () => void;
    onSave: (id: string, text: string) => void;
    onCancel: () => void;
  }) => (
    <div
      data-testid={`gap-question-card-${props.questionIndex}`}
      data-question-id={props.question.question_id}
      data-is-editing={String(props.isEditing)}
    >
      <button onClick={props.onRequestEdit}>Answer</button>
      <button onClick={() => props.onSave(props.question.question_id, 'saved text')}>Save</button>
      <button onClick={props.onCancel}>Cancel</button>
    </div>
  ),
}));

vi.mock('../../../src/frontend/components/ui/ProgressBar', () => ({
  ProgressBar: (props: {
    value: number;
    label: string;
    color?: string;
    'aria-label'?: string;
  }) => (
    <div
      role="progressbar"
      aria-valuenow={props.value}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={props['aria-label'] ?? props.label}
      data-testid="progress-bar"
      data-value={props.value}
    >
      {props.label}
    </div>
  ),
}));

// ─── Shared mock push (declared before hoisted mocks reference it) ─────────────
const mockPush = vi.fn();

// ─── Test fixtures ─────────────────────────────────────────────────────────────
const FIVE_QUESTIONS = [
  { question_id: 'q1', question: 'Q1 text', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
  { question_id: 'q2', question: 'Q2 text', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
  { question_id: 'q3', question: 'Q3 text', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
  { question_id: 'q4', question: 'Q4 text', impact: 'HIGH' as const, probability: 'LOW' as const, gap_score: 7, tags: [] },
  { question_id: 'q5', question: 'Q5 text', impact: 'MEDIUM' as const, probability: 'HIGH' as const, gap_score: 4, tags: [] },
];

const TWO_RESPONSES = [
  { question_id: 'q1', response: 'My answer 1' },
  { question_id: 'q2', response: 'My answer 2' },
];

const HUB_STUB = {
  application: { application_id: 'job-123', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job-123', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
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

// ─── Render helper ─────────────────────────────────────────────────────────────
async function renderPage() {
  const { default: GapPage } = await import('../../../src/frontend/app/applications/[id]/gap-analysis/page');
  return render(
    <Suspense fallback={<div data-testid="suspense-fallback" />}>
      <GapPage params={Promise.resolve({ id: 'job-123' })} />
    </Suspense>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('GapAnalysisContent', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(HUB_STUB);
  });

  // ─── AC-001: Loading state — skeleton cards, no centered spinner ─────────────

  describe('loading state', () => {
    it('test_shows_skeleton_cards_when_data_is_fetching', async () => {
      // TODO: mock getGapQuestions to never resolve (pending promise) so loading state persists
      apiMocks.getGapQuestions.mockReturnValue(new Promise(() => {}));
      await renderPage();
      // TODO: assert 3 or 4 elements with data-testid matching /skeleton-card/i are in the document
      // TODO: assert screen.queryByTestId('spinner') is null (no centered spinner)
    });

    it('test_no_centered_spinner_when_loading', async () => {
      apiMocks.getGapQuestions.mockReturnValue(new Promise(() => {}));
      await renderPage();
      // TODO: assert screen.queryByRole('status') or data-testid="spinner" is not present
    });
  });

  // ─── AC-002: Page title styling ──────────────────────────────────────────────

  describe('page title', () => {
    it('test_renders_gap_analysis_questions_title_when_questions_loaded', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByText('Gap Analysis Questions'))
      // TODO: assert element has classes text-2xl and font-bold (or check heading level)
    });

    it('test_title_uses_bold_large_styling_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('heading', { name: /Gap Analysis Questions/ }))
      // TODO: assert element.className includes 'text-2xl' and 'font-bold'
    });
  });

  // ─── AC-003: Subtitle text ───────────────────────────────────────────────────

  describe('subtitle', () => {
    it('test_renders_correct_subtitle_when_questions_loaded', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() =>
      //   screen.getByText('Answer some questions to fill in gaps between your CV and this role')
      // )
    });
  });

  // ─── AC-004: Back link ───────────────────────────────────────────────────────

  describe('back link', () => {
    it('test_renders_back_link_when_questions_loaded', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('link', { name: /← Back/ }))
      // TODO: assert link is visible
    });

    it('test_back_link_navigates_to_applications_job_id_when_clicked', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('link', { name: /← Back/ }))
      // TODO: assert link.getAttribute('href') === '/applications/job-123'
      //        OR fireEvent.click(backLink) and assert mockPush('/applications/job-123')
    });
  });

  // ─── AC-005: Progress bar value and label ────────────────────────────────────

  describe('progress bar', () => {
    it('test_progress_bar_value_is_40_when_2_of_5_questions_answered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      // TODO: mock getApplication to return responses for q1 and q2
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS, responses: TWO_RESPONSES },
      });
      await renderPage();
      // TODO: await waitFor(() => screen.getByTestId('progress-bar'))
      // TODO: assert progressBar.getAttribute('aria-valuenow') === '40'
    });

    it('test_progress_bar_label_reads_2_out_of_5_answered_when_2_of_5_answered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS, responses: TWO_RESPONSES },
      });
      await renderPage();
      // TODO: await waitFor(() => screen.getByText('2 out of 5 answered'))
    });

    it('test_progress_bar_shows_zero_when_no_questions_answered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      apiMocks.getApplication.mockResolvedValue({ ...HUB_STUB, gap_analysis: { questions: FIVE_QUESTIONS, responses: [] } });
      await renderPage();
      // TODO: await waitFor(() => screen.getByTestId('progress-bar'))
      // TODO: assert aria-valuenow === '0'
      // TODO: assert text '0 out of 5 answered' is visible
    });
  });

  // ─── AC-006: Global Edit/Save/Cancel bar is absent ───────────────────────────

  describe('removed global edit bar', () => {
    it('test_no_sticky_header_edit_bar_when_page_renders', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      await waitFor(() => screen.getAllByTestId(/gap-question-card/));
      // TODO: assert screen.queryByTestId('save-responses') is null
      // TODO: assert screen.queryByRole('button', { name: /^Edit$/ }) is null
      // TODO: assert screen.queryByRole('button', { name: /^Cancel$/ }) is null (global Cancel)
    });
  });

  // ─── AC-007: Generate Questions button is absent ─────────────────────────────

  describe('removed generate button', () => {
    it('test_no_generate_questions_button_when_questions_loaded', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      await waitFor(() => screen.getAllByTestId(/gap-question-card/));
      // TODO: assert screen.queryByTestId('generate-gap-questions') is null
      // TODO: assert screen.queryByRole('button', { name: /Generate Questions/i }) is null
    });

    it('test_no_generate_questions_button_when_questions_empty', async () => {
      apiMocks.getGapQuestions.mockResolvedValue([]);
      await renderPage();
      // TODO: wait for empty state to appear
      // TODO: assert screen.queryByRole('button', { name: /Generate Questions/i }) is null
    });
  });

  // ─── AC-008: Empty state ─────────────────────────────────────────────────────

  describe('empty state', () => {
    it('test_shows_error_message_when_api_returns_empty_questions', async () => {
      apiMocks.getGapQuestions.mockResolvedValue([]);
      await renderPage();
      // TODO: await waitFor(() =>
      //   screen.getByText('There was an error, contact site administrator.')
      // )
    });

    it('test_empty_state_shows_link_to_hub_when_no_questions', async () => {
      apiMocks.getGapQuestions.mockResolvedValue([]);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('link', { name: /hub/i }))
      // TODO: assert link.getAttribute('href') === '/applications/job-123'
    });
  });

  // ─── AC-009: Error state — API failure ───────────────────────────────────────

  describe('error state', () => {
    it('test_shows_inline_error_banner_when_api_fetch_fails', async () => {
      apiMocks.getGapQuestions.mockRejectedValue(new Error('Network error'));
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('alert'))
      // TODO: assert error banner is present (data-testid="error-banner" or role="alert")
    });

    it('test_error_banner_contains_retry_button_when_fetch_fails', async () => {
      apiMocks.getGapQuestions.mockRejectedValue(new Error('Network error'));
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('button', { name: /Retry/i }))
    });
  });

  // ─── AC-010: Retry button re-fetches ─────────────────────────────────────────

  describe('retry behaviour', () => {
    it('test_retry_calls_get_gap_questions_again_when_clicked', async () => {
      apiMocks.getGapQuestions
        .mockRejectedValueOnce(new Error('fail'))
        .mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('button', { name: /Retry/i }))
      // TODO: fireEvent.click(screen.getByRole('button', { name: /Retry/i }))
      // TODO: await waitFor(() => expect(apiMocks.getGapQuestions).toHaveBeenCalledTimes(2))
    });

    it('test_error_banner_replaced_with_questions_after_successful_retry', async () => {
      apiMocks.getGapQuestions
        .mockRejectedValueOnce(new Error('fail'))
        .mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('button', { name: /Retry/i }))
      // TODO: fireEvent.click(retryButton)
      // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
      // TODO: assert screen.queryByRole('alert') is null
    });
  });

  // ─── AC-011: Multi-editor guard ──────────────────────────────────────────────

  describe('multi-editor guard', () => {
    it('test_confirmation_dialog_shown_when_switching_from_one_editing_question_to_another', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
      // TODO: spy on window.confirm and make it return true or false
      // TODO: click "Answer" on card-2 to set editingQuestionId to 'q3'
      // TODO: click "Answer" on card-4 (question 5) while card-2 is editing
      // TODO: assert window.confirm was called once
      // TODO: assert the confirm message references the currently-editing question number
    });

    it('test_second_question_opens_when_user_confirms_switch', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
      await renderPage();
      // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
      // TODO: open card-2 for editing, then click "Answer" on card-4
      // TODO: assert confirmSpy was called
      // TODO: assert card-4's data-is-editing attribute becomes 'true'
      confirmSpy.mockRestore();
    });

    it('test_editing_question_stays_open_when_user_cancels_switch', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
      await renderPage();
      // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
      // TODO: open card-2 for editing, then attempt to open card-4
      // TODO: assert card-4's data-is-editing is still 'false'
      // TODO: assert card-2's data-is-editing is still 'true'
      confirmSpy.mockRestore();
    });
  });

  // ─── AC-012: GapQuestionCard receives correct props ──────────────────────────

  describe('GapQuestionCard delegation', () => {
    it('test_renders_gap_question_card_for_each_question_when_loaded', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
      // TODO: assert exactly 5 GapQuestionCard elements are in the document
    });

    it('test_gap_question_card_receives_correct_question_prop_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS.slice(0, 1));
      await renderPage();
      // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
      // TODO: assert card.getAttribute('data-question-id') === 'q1'
    });

    it('test_gap_question_card_receives_is_editing_false_by_default_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS.slice(0, 1));
      await renderPage();
      // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
      // TODO: assert card.getAttribute('data-is-editing') === 'false'
    });

    it('test_gap_question_card_receives_existing_response_when_api_has_saved_answer', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS.slice(0, 1));
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS.slice(0, 1), responses: [{ question_id: 'q1', response: 'prior answer' }] },
      });
      await renderPage();
      // TODO: await waitFor(() => screen.getByTestId('gap-question-card-0'))
      // TODO: assert the response prop passed to GapQuestionCard equals 'prior answer'
      //        (verify via a data attribute on the mock or by querying rendered text)
    });
  });

  // ─── AC-013: Hebrew locale strings ───────────────────────────────────────────

  describe('i18n — Hebrew locale', () => {
    it('test_title_renders_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      // TODO: set locale to Hebrew — mock i18n context or next-intl provider with locale="he"
      await renderPage();
      // TODO: await waitFor(() => screen.getByText(/<Hebrew translation of "Gap Analysis Questions">/))
    });

    it('test_subtitle_renders_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      // TODO: set locale to Hebrew
      await renderPage();
      // TODO: await waitFor(() => screen.getByText(/<Hebrew subtitle translation>/))
    });

    it('test_progress_label_renders_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS, responses: TWO_RESPONSES },
      });
      // TODO: set locale to Hebrew
      await renderPage();
      // TODO: await waitFor(() => screen.getByText(/<Hebrew "2 out of 5 answered">/))
    });

    it('test_back_link_text_renders_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      // TODO: set locale to Hebrew
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('link', { name: /<Hebrew "← Back">/ }))
    });

    it('test_empty_state_message_renders_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockResolvedValue([]);
      // TODO: set locale to Hebrew
      await renderPage();
      // TODO: await waitFor(() => screen.getByText(/<Hebrew "There was an error, contact site administrator.">/))
    });

    it('test_error_banner_and_retry_button_render_in_hebrew_when_locale_is_he', async () => {
      apiMocks.getGapQuestions.mockRejectedValue(new Error('fail'));
      // TODO: set locale to Hebrew
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('button', { name: /<Hebrew "Retry">/ }))
    });
  });

  // ─── AC-014: Mobile viewport — vertical stack, no horizontal overflow ─────────

  describe('responsive layout', () => {
    it('test_question_cards_stack_vertically_when_viewport_is_mobile', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      await waitFor(() => screen.getAllByTestId(/gap-question-card/));
      // TODO: assert the question list container has a flex-col or block layout class
      // TODO: assert no element has overflow-x at a mobile viewport width
      // Hint: check that the container does NOT have a grid with multiple columns or flex-row
    });
  });

  // ─── AC-016: ProgressBar ARIA attributes ─────────────────────────────────────

  describe('accessibility — progress bar', () => {
    it('test_progress_bar_has_role_progressbar_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('progressbar'))
    });

    it('test_progress_bar_has_aria_valuenow_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS, responses: TWO_RESPONSES },
      });
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('progressbar'))
      // TODO: assert element.getAttribute('aria-valuenow') === '40'
    });

    it('test_progress_bar_has_aria_valuemin_0_and_aria_valuemax_100_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('progressbar'))
      // TODO: assert element.getAttribute('aria-valuemin') === '0'
      // TODO: assert element.getAttribute('aria-valuemax') === '100'
    });

    it('test_progress_bar_has_aria_label_matching_answered_count_when_rendered', async () => {
      apiMocks.getGapQuestions.mockResolvedValue(FIVE_QUESTIONS);
      apiMocks.getApplication.mockResolvedValue({
        ...HUB_STUB,
        gap_analysis: { questions: FIVE_QUESTIONS, responses: TWO_RESPONSES },
      });
      await renderPage();
      // TODO: await waitFor(() => screen.getByRole('progressbar'))
      // TODO: assert element.getAttribute('aria-label') === '2 out of 5 answered'
    });
  });

});
