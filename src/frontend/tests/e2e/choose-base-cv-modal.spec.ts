// spec_id: FE-UI-011  component: ChooseBaseCVModal  tier: e2e
// routes: /applications/new (choice mode), /cv-center (upload-only mode)
// route-slugs: new-application, cv-center
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover complete user
// flows and visual regression baselines for both modal modes.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// shared auth helper
// ---------------------------------------------------------------------------
async function authenticateAndNavigate(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  route: string
) {
  // TODO: set auth cookies or localStorage token before navigation
  // TODO: await page.context().addCookies([{ name: 'session', value: '...', url: '...' }])
  await page.goto(route);
}

// ===========================================================================
// Choice Mode — /applications/new
// Triggered when showChoices=true (NewApplicationPage opens modal)
// ===========================================================================
test.describe('New Application Page — ChooseBaseCVModal (choice mode) @batch3', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie or localStorage token)
    // TODO: navigate to /applications/new
    await authenticateAndNavigate(page, '/applications/new');
    // TODO: click the "Change" or "Choose CV" button to open ChooseBaseCVModal
    // TODO: await expect(page.getByRole('dialog')).toBeVisible()
  });

  // ─── Primary flow: open modal, select an existing CV ─────────────────────
  test('test_user_can_open_choose_base_cv_modal_and_select_uploaded_cv', async ({ page }) => {
    // TODO: assert modal heading "Choose Base CV" is visible
    // TODO: assert "Select uploaded CV" and "Select generated CV" buttons are visible
    // TODO: assert "OR" divider is visible
    // TODO: click a CV row (or "Select uploaded CV" button) for an uploaded CV
    // TODO: assert modal closes and selected CV name appears on the page
    // TODO: await expect(page.getByRole('heading', { name: /choose base cv/i })).toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /select uploaded cv/i })).toBeVisible()
    // TODO: await expect(page.getByText(/^or$/i)).toBeVisible()
    // TODO: await page.getByRole('button', { name: /select uploaded cv/i }).click()
    //        or click a specific CV row
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Primary flow: open modal, upload a new CV ────────────────────────────
  test('test_user_can_upload_new_cv_from_choice_mode_modal', async ({ page }) => {
    // TODO: assert file input is present inside the modal
    // TODO: assert "Upload" button is disabled before file selection
    // TODO: set input files to a test PDF
    // TODO: assert filename displayed in modal
    // TODO: assert "Upload" button becomes enabled
    // TODO: click "Upload", assert modal closes and CV appears in list
    // TODO: await expect(page.locator('input[type="file"]')).toBeAttached()
    // TODO: await expect(page.getByRole('button', { name: /^upload$/i })).toBeDisabled()
    // TODO: await page.locator('input[type="file"]').setInputFiles('tests/fixtures/sample.pdf')
    // TODO: await expect(page.getByText('sample.pdf')).toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /^upload$/i })).toBeEnabled()
    // TODO: await page.getByRole('button', { name: /^upload$/i }).click()
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Close: X button ─────────────────────────────────────────────────────
  test('test_modal_closes_when_x_button_clicked_in_choice_mode', async ({ page }) => {
    // TODO: click X close button
    // TODO: assert modal is no longer in the DOM
    // TODO: await page.getByRole('button', { name: /close/i }).click()
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Close: Escape key ───────────────────────────────────────────────────
  test('test_modal_closes_when_escape_pressed_in_choice_mode', async ({ page }) => {
    // TODO: press Escape
    // TODO: assert modal is no longer in the DOM
    // TODO: await page.keyboard.press('Escape')
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Close: backdrop click ───────────────────────────────────────────────
  test('test_modal_closes_when_backdrop_clicked_in_choice_mode', async ({ page }) => {
    // TODO: click outside the modal card (on the backdrop overlay)
    // TODO: assert modal is no longer in the DOM
    // TODO: await page.locator('[data-testid="modal-backdrop"]').click({ position: { x: 10, y: 10 } })
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Accessibility: focus trap ────────────────────────────────────────────
  test('test_focus_trapped_within_modal_when_tab_pressed', async ({ page }) => {
    // TODO: focus X close button (first focusable element)
    // TODO: press Tab repeatedly through all focusable elements
    // TODO: assert focus wraps back to X close button without leaving the modal
    // TODO: await page.getByRole('button', { name: /close/i }).focus()
    // TODO: await page.keyboard.press('Tab') // cycle through all focusables
    // TODO: await expect(page.getByRole('button', { name: /close/i })).toBeFocused()
  });

  // ─── Empty state: buttons disabled when no CVs exist ─────────────────────
  test('test_choice_buttons_disabled_when_user_has_no_cvs', async ({ page }) => {
    // TODO: ensure test user has no CVs (seed DB or mock API to return [])
    // TODO: assert "Select uploaded CV" button is disabled
    // TODO: assert "Select generated CV" button is disabled
    // TODO: assert upload section is visually highlighted
    // TODO: await expect(page.getByRole('button', { name: /select uploaded cv/i })).toBeDisabled()
    // TODO: await expect(page.getByRole('button', { name: /select generated cv/i })).toBeDisabled()
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline — choice mode @slow', async ({ page }) => {
    // TODO: wait for modal to be fully rendered (CV list loaded, no spinners)
    // TODO: await page.waitForLoadState('networkidle')
    await expect(page).toHaveScreenshot('new-application-choose-base-cv-modal-baseline.png');
  });

});

// ===========================================================================
// Upload-Only Mode — /cv-center
// Triggered when showChoices=false (BaseCVsTable "+ Upload New CV" button)
// ===========================================================================
test.describe('CV Center — ChooseBaseCVModal (upload-only mode) @batch3', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate
    // TODO: navigate to /cv-center
    await authenticateAndNavigate(page, '/cv-center');
    // TODO: click "+ Upload New CV" button (on BaseCVsTable) to open ChooseBaseCVModal with showChoices=false
    // TODO: await expect(page.getByRole('dialog')).toBeVisible()
  });

  // ─── Primary flow: upload a CV from CV Center ─────────────────────────────
  test('test_user_can_upload_base_cv_from_cv_center', async ({ page }) => {
    // TODO: assert modal heading "Upload Base CV" is visible
    // TODO: assert "Select uploaded CV" and "Select generated CV" buttons are NOT in the DOM
    // TODO: set input files to a test PDF
    // TODO: assert filename displayed in modal
    // TODO: click "Upload" button
    // TODO: assert modal closes and new CV appears in the CV Center table
    // TODO: await expect(page.getByRole('heading', { name: /upload base cv/i })).toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /select uploaded cv/i })).not.toBeVisible()
    // TODO: await page.locator('input[type="file"]').setInputFiles('tests/fixtures/sample.pdf')
    // TODO: await expect(page.getByText('sample.pdf')).toBeVisible()
    // TODO: await page.getByRole('button', { name: /^upload$/i }).click()
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
    // TODO: await expect(page.getByText('sample.pdf')).toBeVisible() // now in table
  });

  // ─── Upload button disabled before file selection ─────────────────────────
  test('test_upload_button_disabled_before_file_selected_in_upload_only_mode', async ({ page }) => {
    // TODO: assert "Upload" submit button is disabled on modal open
    // TODO: await expect(page.getByRole('button', { name: /^upload$/i })).toBeDisabled()
  });

  // ─── OS file picker opens on "Upload New CV" click ────────────────────────
  test('test_file_picker_opens_when_upload_new_cv_area_clicked', async ({ page }) => {
    // TODO: listen for the filechooser event
    // TODO: click the file picker trigger (input or surrounding button)
    // TODO: assert filechooser event fires without intermediate dialog
    // TODO: const [fileChooser] = await Promise.all([
    //   page.waitForEvent('filechooser'),
    //   page.locator('input[type="file"]').click({ force: true }),
    // ])
    // TODO: expect(fileChooser).not.toBeNull()
  });

  // ─── Close: X button ─────────────────────────────────────────────────────
  test('test_modal_closes_when_x_button_clicked_in_upload_only_mode', async ({ page }) => {
    // TODO: click X close button
    // TODO: assert modal is no longer in the DOM
    // TODO: await page.getByRole('button', { name: /close/i }).click()
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Close: Escape key ───────────────────────────────────────────────────
  test('test_modal_closes_when_escape_pressed_in_upload_only_mode', async ({ page }) => {
    // TODO: press Escape
    // TODO: assert modal is no longer in the DOM
    // TODO: await page.keyboard.press('Escape')
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline — upload-only mode @slow', async ({ page }) => {
    // TODO: wait for modal to be fully rendered
    // TODO: await page.waitForLoadState('networkidle')
    await expect(page).toHaveScreenshot('cv-center-choose-base-cv-modal-baseline.png');
  });

});
