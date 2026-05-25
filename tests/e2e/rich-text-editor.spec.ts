// spec_id: FE-UI-020 — RichTextEditor e2e tests
// Coverage target: 10% — complete user flows in a real browser
// Route: /applications/[id]/gap-analysis
// Route slug: gap-analysis

import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// No ACs carry verification_type: live in this spec — all are unit/integration.
// These e2e stubs cover the critical user flows that touch the editor within
// its real page context and capture a visual regression baseline.
// ---------------------------------------------------------------------------

test.describe('Gap Analysis — RichTextEditor', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate user (set session cookie or call login endpoint)
    //       e.g., await page.goto('/api/auth/test-login');
    // TODO: navigate to /applications/{testApplicationId}/gap-analysis
    //       replace {testApplicationId} with a seeded test fixture ID
    // TODO: await page.waitForSelector('[data-testid="gap-question-card"]')
  });

  // -------------------------------------------------------------------------
  // Primary flow: user types formatted content and saves
  // -------------------------------------------------------------------------
  test('test_user_can_type_and_bold_text_in_editor', async ({ page }) => {
    // TODO: locate the first RichTextEditor on the page
    // TODO: click inside the editor area to focus it
    // TODO: type some text
    // TODO: select the text (keyboard select-all or drag)
    // TODO: click the Bold toolbar button (aria-label="Bold")
    // TODO: assert the editor content contains bold-marked text
    // TODO: assert the Bold button shows active state
  });

  test('test_user_can_create_bullet_list_in_editor', async ({ page }) => {
    // TODO: focus editor
    // TODO: click Bullet list toolbar button (aria-label="Bullet list")
    // TODO: type list item text
    // TODO: assert the editor renders a <ul> with <li> items
  });

  test('test_editor_becomes_readonly_during_save_flow', async ({ page }) => {
    // TODO: focus editor and type content
    // TODO: trigger the save action (click Save / answer submit button)
    // TODO: assert toolbar is hidden while save is in progress
    // TODO: await save completion
    // TODO: assert editor returns to editable state
  });

  test('test_existing_plain_text_answer_loads_without_formatting_artifacts', async ({ page }) => {
    // TODO: seed or navigate to an application that already has a plain-text answer
    // TODO: assert the editor displays the plain text without extra Markdown symbols
    //       (e.g., no stray * or _ characters)
  });

  // -------------------------------------------------------------------------
  // Visual regression baseline
  // -------------------------------------------------------------------------
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: ensure the page is fully loaded and the first question card is visible
    await expect(page).toHaveScreenshot('gap-analysis-richtexteditor-baseline.png');
  });

  test('visual regression baseline — read-only state @slow', async ({ page }) => {
    // TODO: navigate to a question that already has a saved answer (read-only state)
    await expect(page).toHaveScreenshot('gap-analysis-richtexteditor-readonly-baseline.png');
  });

});
