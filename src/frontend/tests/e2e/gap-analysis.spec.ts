// spec_id: FE-UI-018
// Component: GapAnalysisContent
// Route: /applications/[id]/gap-analysis
// Route slug: gap-analysis
// ACs covered: AC-001, AC-002, AC-003, AC-004, AC-005, AC-008, AC-009, AC-011, AC-015, AC-016
//   (all verification_type: live — full browser flows and visual regression)
// API endpoints tested: GET /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses

import { test, expect } from '@playwright/test';

// ─── Helpers ───────────────────────────────────────────────────────────────────
// TODO: import or define test fixtures (application ID, authenticated user)
// const TEST_APP_ID = process.env.E2E_TEST_APP_ID ?? 'test-app-id';
// const GAP_ANALYSIS_URL = `/applications/${TEST_APP_ID}/gap-analysis`;

test.describe('Gap Analysis — GapAnalysisContent @batch5', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — set auth cookie or use Playwright storageState
    //   e.g. await page.context().addCookies([{ name: 'auth-token', value: process.env.E2E_AUTH_TOKEN!, ... }])
    //   or:  await page.goto('/login'); fill credentials; await page.waitForURL('**/dashboard')
    // TODO: seed or locate a test application that has pre-generated gap questions
    // TODO: navigate to the gap analysis page
    //   await page.goto(GAP_ANALYSIS_URL);
  });

  // ─── AC-001: Loading — skeleton cards, no centered spinner ───────────────────

  test('test_skeleton_cards_visible_during_initial_load', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions and delay response by 2000ms
    //   await page.route('**/gap-questions', async (route) => {
    //     await new Promise((r) => setTimeout(r, 2000));
    //     await route.continue();
    //   });
    // TODO: navigate to gap analysis page
    // TODO: assert at least 3 elements matching [data-testid^="skeleton-card"] are visible
    // TODO: assert no element with data-testid="spinner" or role="status" is visible
  });

  // ─── AC-002 + AC-003: Title and subtitle render correctly ────────────────────

  test('test_page_title_and_subtitle_render_when_questions_loaded', async ({ page }) => {
    // TODO: await page.waitForSelector('h1, h2', { state: 'visible' })
    // TODO: assert page.getByRole('heading', { name: 'Gap Analysis Questions' }) is visible
    // TODO: assert page.getByText('Answer some questions to fill in gaps between your CV and this role') is visible
  });

  // ─── AC-004: Back link position and navigation ────────────────────────────────

  test('test_back_link_navigates_to_hub_when_clicked', async ({ page }) => {
    // TODO: await page.waitForSelector('[data-testid="back-link"]', { state: 'visible' })
    // TODO: const backLink = page.getByRole('link', { name: /← Back/ })
    // TODO: assert await backLink.isVisible()
    // TODO: await backLink.click()
    // TODO: await page.waitForURL(`**/applications/${TEST_APP_ID}`)
    // TODO: assert page.url() matches /\/applications\/[^/]+$/
  });

  // ─── AC-005: Progress bar value and label ────────────────────────────────────

  test('test_progress_bar_shows_correct_count_when_some_questions_answered', async ({ page }) => {
    // TODO: use a test application where exactly 2 of 5 questions have saved responses
    // TODO: await page.waitForSelector('[role="progressbar"]', { state: 'visible' })
    // TODO: assert page.getByRole('progressbar').getAttribute('aria-valuenow') === '40'
    // TODO: assert page.getByText('2 out of 5 answered').isVisible()
  });

  // ─── AC-008: Empty state message and hub link ────────────────────────────────

  test('test_empty_state_shown_with_hub_link_when_api_returns_no_questions', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions to return { questions: [] }
    //   await page.route('**/gap-questions', (route) =>
    //     route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    //   );
    // TODO: navigate to gap analysis page
    // TODO: assert page.getByText('There was an error, contact site administrator.').isVisible()
    // TODO: assert page.getByRole('link', { name: /hub/i }).getAttribute('href') matches /\/applications\/[^/]+$/
  });

  // ─── AC-009 + AC-010: Error state with Retry ─────────────────────────────────

  test('test_error_banner_with_retry_button_shown_when_api_fails', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions and return 500
    //   await page.route('**/gap-questions', (route) =>
    //     route.fulfill({ status: 500, body: 'Internal Server Error' })
    //   );
    // TODO: navigate to gap analysis page
    // TODO: assert page.getByRole('alert').isVisible()
    // TODO: assert page.getByRole('button', { name: /Retry/i }).isVisible()
  });

  test('test_retry_re_fetches_questions_and_replaces_error_banner', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions — first call returns 500, second returns questions
    //   let callCount = 0;
    //   await page.route('**/gap-questions', (route) => {
    //     callCount++;
    //     if (callCount === 1) return route.fulfill({ status: 500 });
    //     return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(QUESTIONS) });
    //   });
    // TODO: navigate to page, wait for error, click Retry
    // TODO: await page.getByRole('button', { name: /Retry/i }).click()
    // TODO: await page.waitForSelector('[data-testid^="gap-question-card"]', { state: 'visible' })
    // TODO: assert page.getByRole('alert').count() === 0
  });

  // ─── AC-011: Multi-editor guard dialog ───────────────────────────────────────

  test('test_confirmation_dialog_appears_when_switching_editing_question @slow', async ({ page }) => {
    // TODO: wait for question cards to load
    // TODO: click "Answer" on question card 1 to open it for editing
    // TODO: listen for dialog event: page.on('dialog', async (dialog) => { await dialog.dismiss() })
    // TODO: click "Answer" on question card 3
    // TODO: assert dialog was triggered (capture dialog message)
    // TODO: assert dialog.message() contains reference to question 1
  });

  // ─── AC-015: Per-question save calls POST and updates UI ────────────────────

  test('test_save_on_question_card_calls_post_gap_responses_with_correct_payload', async ({ page }) => {
    // TODO: intercept POST /jobs/*/gap-responses and capture request body
    //   let capturedBody: unknown;
    //   await page.route('**/gap-responses', async (route) => {
    //     capturedBody = JSON.parse(route.request().postData() ?? '{}');
    //     await route.fulfill({ status: 200 });
    //   });
    // TODO: wait for questions to load
    // TODO: click "Answer" on question card 0 to enter edit mode
    // TODO: fill in the answer textarea / rich text editor with 'E2E test answer'
    // TODO: click "Save" on the card
    // TODO: assert capturedBody.responses has length 1
    // TODO: assert capturedBody.responses[0].question_id === expected question_id
    // TODO: assert capturedBody.responses[0].response === 'E2E test answer'
  });

  test('test_question_card_exits_edit_mode_after_successful_save', async ({ page }) => {
    // TODO: intercept POST /jobs/*/gap-responses to return 200
    // TODO: wait for questions to load; click "Answer" on card 0
    // TODO: fill in answer and click "Save"
    // TODO: assert the card no longer shows the edit textarea
    // TODO: assert the saved response text is visible in the card's read view
  });

  // ─── AC-016: ProgressBar ARIA (in-browser) ───────────────────────────────────

  test('test_progress_bar_has_correct_aria_attributes_in_browser', async ({ page }) => {
    // TODO: wait for page to load with questions
    // TODO: const progressBar = page.getByRole('progressbar')
    // TODO: assert await progressBar.getAttribute('aria-valuemin') === '0'
    // TODO: assert await progressBar.getAttribute('aria-valuemax') === '100'
    // TODO: assert await progressBar.getAttribute('aria-valuenow') is a number string between '0' and '100'
    // TODO: assert await progressBar.getAttribute('aria-label') matches /\d+ out of \d+ answered/
  });

  // ─── Visual regression baseline ──────────────────────────────────────────────

  test('visual regression baseline — read state @slow', async ({ page }) => {
    // TODO: wait for question cards to load fully (no skeleton, no loading indicator)
    // TODO: await page.waitForSelector('[data-testid^="gap-question-card"]', { state: 'visible' })
    await expect(page).toHaveScreenshot('gap-analysis-content-baseline.png');
  });

  test('visual regression baseline — empty state @slow', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions to return []
    // TODO: navigate and wait for empty state text
    await expect(page).toHaveScreenshot('gap-analysis-empty-state-baseline.png');
  });

  test('visual regression baseline — error state @slow', async ({ page }) => {
    // TODO: intercept GET /jobs/*/gap-questions to return 500
    // TODO: wait for error banner
    await expect(page).toHaveScreenshot('gap-analysis-error-state-baseline.png');
  });

});
