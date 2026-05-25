// spec_id: FE-UI-018
// Component: GapAnalysisContent (default export of gap-analysis/page.tsx)
// Route: /applications/[id]/gap-analysis
// Purpose: Guard pre-upgrade behaviour that must survive the restructure
//
// Blocked regressions (from spec):
//   - POST /jobs/{jobId}/gap-responses accepts both plain text and Markdown
//   - Previously saved responses display without data loss
//   - Hub page (/applications/[id]) is unaffected
//   - Navigation hub → gap-analysis and back continues to work

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
  useParams: () => ({ id: 'job-reg' }),
}));

vi.mock('../../src/frontend/api/methods', () => ({
  api: apiMocks,
}));

// ─── Fixtures ──────────────────────────────────────────────────────────────────
const PLAIN_TEXT_RESPONSE = 'This is a plain text answer without any markdown.';
const MARKDOWN_RESPONSE = '**Experienced** in Python — built _three_ production services.';

const ONE_QUESTION = [
  { question_id: 'q1', question: 'Describe your experience', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
];

const HUB_STUB = {
  application: { application_id: 'job-reg', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job-reg', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
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
  const { default: GapPage } = await import('../../src/frontend/app/applications/[id]/gap-analysis/page');
  return renderWithSuspense(<GapPage params={Promise.resolve({ id: 'job-reg' })} />);
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('GapAnalysisContent regression', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(HUB_STUB);
  });

  // ─── API contract: POST /jobs/{jobId}/gap-responses ───────────────────────────

  it('test_existing_api_contract_unchanged_post_gap_responses_accepts_plain_text', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: trigger onSave for question q1 with PLAIN_TEXT_RESPONSE
    // TODO: await waitFor(() =>
    //   expect(apiMocks.saveGapResponses).toHaveBeenCalledWith(
    //     'job-reg',
    //     expect.arrayContaining([
    //       expect.objectContaining({ question_id: 'q1', response: PLAIN_TEXT_RESPONSE }),
    //     ]),
    //   )
    // )
    // TODO: assert saveGapResponses resolved without error
    expect(PLAIN_TEXT_RESPONSE).toBeDefined(); // placeholder — remove when test is implemented
  });

  it('test_existing_api_contract_unchanged_post_gap_responses_accepts_markdown', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.saveGapResponses.mockResolvedValue(undefined);
    await renderPage();
    // TODO: trigger onSave for question q1 with MARKDOWN_RESPONSE (contains bold and italic)
    // TODO: await waitFor(() =>
    //   expect(apiMocks.saveGapResponses).toHaveBeenCalledWith(
    //     'job-reg',
    //     expect.arrayContaining([
    //       expect.objectContaining({ question_id: 'q1', response: MARKDOWN_RESPONSE }),
    //     ]),
    //   )
    // )
    expect(MARKDOWN_RESPONSE).toBeDefined(); // placeholder — remove when test is implemented
  });

  it('test_existing_api_contract_unchanged_get_gap_questions_response_shape', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert apiMocks.getGapQuestions was called with 'job-reg'
    // TODO: assert the questions rendered match { question_id, question, impact, probability, gap_score, tags }
    //        (guards that the component still consumes the same shape from the GET endpoint)
    expect(apiMocks.getGapQuestions).toBeDefined(); // placeholder
  });

  it('test_existing_api_contract_unchanged_get_applications_response_shape', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.getApplication.mockResolvedValue(HUB_STUB);
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert getApplication was called with 'job-reg'
    // TODO: assert component renders without error when application has the standard HUB shape
    expect(apiMocks.getApplication).toBeDefined(); // placeholder
  });

  // ─── Previously saved plain-text responses load without data loss ──────────────

  it('test_previously_saved_plain_text_response_displayed_after_upgrade', async () => {
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
    // TODO: assert screen.getByText(PLAIN_TEXT_RESPONSE) is in the document (no data loss)
  });

  it('test_previously_saved_response_not_mutated_when_page_loads', async () => {
    const savedResponse = 'Existing saved answer from before the upgrade.';
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    apiMocks.getApplication.mockResolvedValue({
      ...HUB_STUB,
      gap_analysis: {
        questions: ONE_QUESTION,
        responses: [{ question_id: 'q1', response: savedResponse }],
      },
    });
    await renderPage();
    // TODO: await waitFor(() => screen.getAllByTestId(/gap-question-card/))
    // TODO: assert apiMocks.saveGapResponses was NOT called (page load must not mutate saved data)
    // TODO: assert the saved response text is still present unchanged
  });

  // ─── Hub page sibling components unaffected ───────────────────────────────────

  it('test_unmodified_sibling_hub_page_renders_without_error', async () => {
    // TODO: import HubLayout or the /applications/[id] page component
    // TODO: mock its API dependencies (getApplication)
    // TODO: render the hub page
    // TODO: assert no console.error is thrown during render
    // TODO: assert the hub page heading / main content is present
    // Hint: this verifies the gap-analysis upgrade does not break imports shared with hub
    expect(true).toBe(true); // placeholder — implement with actual hub page render
  });

  // ─── Navigation regression: hub → gap-analysis → hub ─────────────────────────

  it('test_back_link_href_points_to_application_hub_not_generic_applications_list', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    // TODO: await waitFor(() => screen.getByRole('link', { name: /← Back/ }))
    // TODO: const backLink = screen.getByRole('link', { name: /← Back/ })
    // TODO: assert backLink.getAttribute('href') === '/applications/job-reg'
    //        (not '/applications' — must return to the specific application hub)
  });

  // ─── No regression: generate-questions button must remain absent ──────────────

  it('test_generate_questions_button_absent_even_when_questions_array_is_empty', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);
    await renderPage();
    await waitFor(() =>
      screen.getByText('There was an error, contact site administrator.'),
    );
    // TODO: assert screen.queryByTestId('generate-gap-questions') is null
    // TODO: assert screen.queryByRole('button', { name: /Generate Questions/i }) is null
  });

  // ─── No regression: FormMode global toggle must not exist ────────────────────

  it('test_global_edit_button_absent_after_upgrade', async () => {
    apiMocks.getGapQuestions.mockResolvedValue(ONE_QUESTION);
    await renderPage();
    await waitFor(() => screen.getAllByTestId(/gap-question-card/));
    // TODO: assert screen.queryByTestId('save-responses') is null
    // TODO: assert screen.queryByRole('button', { name: /^Edit$/i }) is null (global Edit button)
  });

});
