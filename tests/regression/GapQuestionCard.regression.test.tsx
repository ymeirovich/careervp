// spec_id: FE-UI-019
// Component: GapQuestionCard
// File: src/frontend/components/GapQuestionCard/GapQuestionCard.tsx
// Route: /applications/[id]/gap-analysis
//
// Purpose: Guard pre-upgrade behaviour that must survive the FE-UI-019 restructure.
//
// Blocked regressions (from spec):
//   - POST /jobs/{jobId}/gap-responses accepts both plain text (legacy) and Markdown (new)
//   - Previously saved responses display correctly in the new GapQuestionCard read view
//   - Hub page (/applications/[id]) is unaffected by the GapQuestionCard introduction
//   - GapAnalysisContent sibling components (ProgressBar, back-link) remain unchanged
//   - Existing tests in src/frontend/tests/unit/gap-analysis-page.test.tsx still pass
//
// RT-001: Any blocking AC flips pass→fail post-deploy → revert component file
// RT-002: New non-2xx on POST /jobs/{jobId}/gap-responses → block deploy
// RT-003: Saved responses garbled after upgrade → revert, investigate TipTap plain-text rendering

import React, { Suspense } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── API mocks ─────────────────────────────────────────────────────────────────
const apiMocks = vi.hoisted(() => ({
  getGapQuestions: vi.fn(),
  getApplication: vi.fn(),
  saveGapResponses: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job-reg-019' }),
}));

vi.mock('../../../src/frontend/api/methods', () => ({
  api: apiMocks,
}));

// ─── Fixtures ──────────────────────────────────────────────────────────────────
const PLAIN_TEXT_RESPONSE = 'This is a plain text answer from before the rich-text upgrade.';
const MARKDOWN_RESPONSE = '**Experienced** in Python — built _three_ production services.\n\n- Item one\n- Item two';

const ONE_QUESTION = [
  {
    question_id: 'q1',
    question: 'Describe your experience',
    impact: 'HIGH' as const,
    probability: 'HIGH' as const,
    gap_score: 8,
    tags: [],
  },
];

const HUB_STUB = {
  application: { application_id: 'job-reg-019', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job-reg-019', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
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

function renderWithSuspense(ui: React.ReactElement) {
  return render(
    <Suspense fallback={<div data-testid="suspense-fallback" />}>{ui}</Suspense>,
  );
}

async function renderPage() {
  const { default: GapPage } = await import(
    '../../../src/frontend/app/applications/[id]/gap-analysis/page'
  );
  return renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job-reg-019' })} />);
}

// ─── Tests ─────────────────────────────────────────────────────────────────────
describe('GapQuestionCard regression', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(HUB_STUB);
  });

  // ─── RT-002: POST /jobs/{jobId}/gap-responses API contract ────────────────────

  it('test_existing_api_contract_unchanged_post_gap_responses_accepts_plain_text', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: trigger onSave for question q1 with PLAIN_TEXT_RESPONSE (no markdown)
    // TODO: await waitFor(() =>
    //   expect(apiMocks.saveGapResponses).toHaveBeenCalledWith(
    //     'job-reg-019',
    //     expect.arrayContaining([
    //       expect.objectContaining({ question_id: 'q1', response: PLAIN_TEXT_RESPONSE }),
    //     ]),
    //   )
    // )
    // TODO: assert saveGapResponses resolved without throwing
    expect(PLAIN_TEXT_RESPONSE).toBeDefined(); // placeholder — remove when implemented
  });

  it('test_existing_api_contract_unchanged_post_gap_responses_accepts_markdown', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: trigger onSave with MARKDOWN_RESPONSE (contains bold, italic, list syntax)
    // TODO: await waitFor(() =>
    //   expect(apiMocks.saveGapResponses).toHaveBeenCalledWith(
    //     'job-reg-019',
    //     expect.arrayContaining([
    //       expect.objectContaining({ question_id: 'q1', response: MARKDOWN_RESPONSE }),
    //     ]),
    //   )
    // )
    expect(MARKDOWN_RESPONSE).toBeDefined(); // placeholder — remove when implemented
  });

  it('test_existing_api_contract_unchanged_post_gap_responses_includes_destination_field', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: trigger onSave for q1 without opening Advanced section
    // TODO: assert saveGapResponses called with payload containing
    //   expect.objectContaining({ destination: 'CV_IMPACT' }) or equivalent field
    //   (guards that the new destination field does not break the existing API call shape)
    expect(apiMocks.saveGapResponses).toBeDefined(); // placeholder
  });

  it('test_save_api_call_does_not_add_unexpected_fields_to_payload', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: trigger onSave and capture the argument passed to saveGapResponses
    // TODO: assert each item in the payload has ONLY the known fields:
    //   { question_id, response, destination }
    //   (guards against field name changes that would silently break the Lambda handler)
    expect(true).toBe(true); // placeholder
  });

  // ─── RT-003: Previously saved responses display without data loss ─────────────

  it('test_previously_saved_plain_text_response_displayed_without_data_loss', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.getApplication.mockResolvedValue({
      ...HUB_STUB,
      gap_analysis: {
        questions: ONE_QUESTION,
        responses: [{ question_id: 'q1', response: PLAIN_TEXT_RESPONSE }],
      },
    });
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert screen.getByText(PLAIN_TEXT_RESPONSE) is in the document
    // TODO: assert no raw markdown or HTML artifacts are visible
  });

  it('test_previously_saved_response_not_mutated_on_page_load', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.getApplication.mockResolvedValue({
      ...HUB_STUB,
      gap_analysis: {
        questions: ONE_QUESTION,
        responses: [{ question_id: 'q1', response: PLAIN_TEXT_RESPONSE }],
      },
    });
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert apiMocks.saveGapResponses was NOT called during page load
    //   (guard against accidental mutation of existing data on mount)
    expect(apiMocks.saveGapResponses).toBeDefined(); // placeholder
  });

  // ─── Unmodified sibling components unaffected ─────────────────────────────────

  it('test_unmodified_sibling_hub_page_renders_without_error', async () => {
    // TODO: import the HubLayout or /applications/[id] page component
    // TODO: mock its API dependencies (getApplication)
    // TODO: render the hub page (separate from the gap analysis page)
    // TODO: assert no console.error during render
    // TODO: assert the hub page main content area is present
    // Hint: shared imports (e.g. types, api methods) must not have been broken by the new component
    expect(true).toBe(true); // placeholder — implement with actual hub page render
  });

  it('test_progress_bar_still_renders_in_gap_analysis_page_after_upgrade', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    // TODO: await waitFor(() => screen.getByRole('progressbar'))
    // TODO: assert progressbar is visible
    // TODO: assert aria-valuemin and aria-valuemax are present on the progressbar
  });

  it('test_back_link_still_points_to_application_hub_after_upgrade', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    // TODO: await waitFor(() => screen.getByRole('link', { name: /← Back/ }))
    // TODO: assert backLink.getAttribute('href') === '/applications/job-reg-019'
    //   (must return to specific application hub, not generic /applications list)
  });

  // ─── Existing gap-analysis-page tests must still pass ─────────────────────────
  //
  // The three tests in src/frontend/tests/unit/gap-analysis-page.test.tsx are:
  //   1. renders 3 question rows with impact badges
  //   2. save button calls saveGapResponses with filled responses
  //   3. shows generate button when no questions and CV exists
  //
  // These tests exercise GapAnalysisContent. After the upgrade, GapAnalysisContent
  // delegates per-question editing to GapQuestionCard. The following stubs assert
  // the equivalent outcomes still hold at the page level.

  it('test_three_question_cards_render_with_impact_badges_after_upgrade', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([
      { question_id: 'q1', question: 'Q1', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
      { question_id: 'q2', question: 'Q2', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
      { question_id: 'q3', question: 'Q3', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
    ]);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/).length >= 3)
    // TODO: assert screen.getAllByText(/Impact: HIGH/).length > 0
  });

  it('test_no_global_save_responses_button_exists_after_upgrade', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert screen.queryByTestId('save-responses') is null
    //   (global save button was removed in favour of per-card save)
  });

});
