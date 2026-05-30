// spec_id: FE-UI-019
// Component: GapQuestionCard
// Route: /applications/[id]/gap-analysis
// Route slug: gap-question-card
// API endpoints: POST /jobs/{jobId}/gap-responses
//
// Note: All 16 ACs are verification_type: unit (no ACs are verification_type: live).
// This file covers the critical end-to-end user flows involving GapQuestionCard
// that require a real browser (rich text interaction, visual regression, ARIA in DOM).

import { test, expect } from '@playwright/test';

// ─── Helpers ───────────────────────────────────────────────────────────────────
// const TEST_APP_ID = process.env.E2E_TEST_APP_ID ?? 'test-app-id';
// const GAP_ANALYSIS_URL = `/applications/${TEST_APP_ID}/gap-analysis`;

test.describe('Gap Analysis — GapQuestionCard', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — set auth cookie or use Playwright storageState
    //   e.g. await page.context().addCookies([{ name: 'auth-token', value: process.env.E2E_AUTH_TOKEN!, ... }])
    // TODO: seed or locate a test application that has pre-generated gap questions
    //   (mix of answered and unanswered questions for full state coverage)
    // TODO: navigate to the gap analysis page
    //   await page.goto(GAP_ANALYSIS_URL);
    // TODO: await page.waitForSelector('[data-testid^="gap-question-card"]', { state: 'visible' })
  });

  // ─── Unanswered read state ────────────────────────────────────────────────────

  test('test_unanswered_card_shows_answer_button', async ({ page }) => {
    // TODO: identify a card with no saved response (data-answered='false')
    //   const card = page.locator('[data-testid="gap-question-card-0"]')
    // TODO: assert card.getByRole('button', { name: /answer/i }).isVisible()
    // TODO: assert card.getByRole('button', { name: /^edit$/i }).count() === 0
  });

  // ─── Answered read state ──────────────────────────────────────────────────────

  test('test_answered_card_shows_response_and_edit_button', async ({ page }) => {
    // TODO: identify a card that has a pre-seeded saved response
    // TODO: assert response text block is visible within the card
    // TODO: assert card.getByRole('button', { name: /^edit$/i }).isVisible()
    // TODO: assert card.getByRole('button', { name: /^answer$/i }).count() === 0
  });

  // ─── Editing state ────────────────────────────────────────────────────────────

  test('test_clicking_answer_opens_rich_text_editor', async ({ page }) => {
    // TODO: click "Answer" on the first unanswered card
    //   await page.locator('[data-testid="gap-question-card-0"] button', { hasText: /answer/i }).click()
    // TODO: await page.waitForSelector('[data-testid="rich-text-editor"]', { state: 'visible' })
    // TODO: assert Save and Cancel buttons are visible
  });

  test('test_clicking_edit_on_answered_card_prepopulates_editor', async ({ page }) => {
    // TODO: locate an answered card with known response text
    // TODO: click the Edit button
    // TODO: await page.waitForSelector('[data-testid="rich-text-editor"]')
    // TODO: assert editor content matches the previously saved response text
  });

  // ─── Save flow ────────────────────────────────────────────────────────────────

  test('test_save_flow_calls_post_and_returns_to_read_state', async ({ page }) => {
    // TODO: intercept POST /jobs/*/gap-responses and capture request body
    //   let capturedBody: unknown;
    //   await page.route('**/gap-responses', async (route) => {
    //     capturedBody = JSON.parse(route.request().postData() ?? '{}');
    //     await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    //   });
    // TODO: click Answer on first unanswered card
    // TODO: type response text into the RichTextEditor
    //   await page.locator('[data-testid="rich-text-editor"]').fill('E2E test response')
    // TODO: click Save
    //   await page.locator('button', { hasText: /save/i }).click()
    // TODO: await page.waitForSelector('[data-testid="rich-text-editor"]', { state: 'hidden' })
    // TODO: assert saved response text is visible in the card read view
    // TODO: assert capturedBody contains question_id and response fields
  });

  test('test_save_spinner_visible_during_slow_save @slow', async ({ page }) => {
    // TODO: intercept POST /jobs/*/gap-responses and delay 1500ms before fulfilling
    // TODO: click Answer, fill response, click Save
    // TODO: assert Save button has aria-busy=true or shows a spinner during the delay
    // TODO: after intercept resolves, assert spinner is gone and read view is shown
  });

  // ─── Error state ──────────────────────────────────────────────────────────────

  test('test_inline_error_shown_when_save_api_returns_500', async ({ page }) => {
    // TODO: intercept POST /jobs/*/gap-responses to return 500
    //   await page.route('**/gap-responses', (route) =>
    //     route.fulfill({ status: 500, body: 'Internal Server Error' })
    //   )
    // TODO: click Answer, fill response, click Save
    // TODO: await page.waitForSelector('text=Failed to save. Please try again.', { state: 'visible' })
    // TODO: assert Save button is re-enabled (not disabled)
  });

  // ─── Cancel ───────────────────────────────────────────────────────────────────

  test('test_cancel_returns_card_to_read_state_without_saving', async ({ page }) => {
    // TODO: click Answer on an unanswered card
    // TODO: type some text into the editor
    // TODO: click Cancel
    // TODO: await page.waitForSelector('[data-testid="rich-text-editor"]', { state: 'hidden' })
    // TODO: assert the typed text is NOT shown in the card (response block absent for unanswered card)
    // TODO: assert no POST /jobs/*/gap-responses was made
  });

  // ─── Impact/probability badges ────────────────────────────────────────────────

  test('test_impact_and_probability_badges_visible_in_all_states', async ({ page }) => {
    // TODO: assert at least one 'Impact:' badge is visible in read state
    //   await expect(page.locator('text=/Impact:/').first()).toBeVisible()
    // TODO: click Answer to enter editing state
    // TODO: assert the badge is still visible in the card header row during editing
  });

  // ─── Advanced options section ─────────────────────────────────────────────────

  test('test_advanced_section_expandable_and_shows_destination_radios', async ({ page }) => {
    // TODO: click Answer on an unanswered card to enter editing mode
    // TODO: assert "Advanced options" disclosure is present but collapsed
    //   (CV_IMPACT radio NOT visible)
    // TODO: click the "Advanced options" toggle
    // TODO: assert CV_IMPACT and INTERVIEW_MVP_ONLY radios are visible
    // TODO: assert CV_IMPACT radio is selected by default
  });

  // ─── Multi-editor guard ───────────────────────────────────────────────────────

  test('test_opening_second_card_edit_closes_first_card_edit @slow', async ({ page }) => {
    // TODO: await cards for at least 2 questions to be visible
    // TODO: click Answer on card 0
    // TODO: await rich-text-editor visible on card 0
    // TODO: click Answer on card 1
    // TODO: assert rich-text-editor on card 0 is no longer visible (or a save/discard prompt appeared)
    // TODO: assert rich-text-editor on card 1 is visible
  });

  // ─── Accessibility in browser ─────────────────────────────────────────────────

  test('test_editor_aria_labelledby_resolves_to_question_text_in_dom', async ({ page }) => {
    // TODO: click Answer on card 0 to enter editing state
    // TODO: const editor = page.locator('[data-testid="rich-text-editor"]')
    // TODO: const labelId = await editor.getAttribute('aria-labelledby')
    // TODO: assert labelId is not null
    // TODO: const labelEl = page.locator(`#${labelId}`)
    // TODO: assert await labelEl.isVisible()
    // TODO: assert (await labelEl.textContent()) contains the question text for card 0
  });

  // ─── Visual regression baselines ─────────────────────────────────────────────

  test('visual regression baseline — unanswered card read state @slow', async ({ page }) => {
    // TODO: await page.waitForSelector('[data-testid^="gap-question-card"]', { state: 'visible' })
    // TODO: await page.waitForSelector('[data-testid^="skeleton"]', { state: 'hidden' })
    await expect(page).toHaveScreenshot('gap-question-card-unanswered-baseline.png');
  });

  test('visual regression baseline — answered card read state @slow', async ({ page }) => {
    // TODO: navigate to page with a pre-seeded answered question
    // TODO: await page.waitForSelector('[data-answered="true"]', { state: 'visible' })
    await expect(page).toHaveScreenshot('gap-question-card-answered-baseline.png');
  });

  test('visual regression baseline — card in editing state @slow', async ({ page }) => {
    // TODO: click Answer on card 0
    // TODO: await page.waitForSelector('[data-testid="rich-text-editor"]', { state: 'visible' })
    await expect(page).toHaveScreenshot('gap-question-card-editing-baseline.png');
  });

  test('visual regression baseline — card error state @slow', async ({ page }) => {
    // TODO: intercept POST and return 500, trigger save failure
    // TODO: await page.waitForSelector('text=Failed to save. Please try again.', { state: 'visible' })
    await expect(page).toHaveScreenshot('gap-question-card-error-baseline.png');
  });

});
