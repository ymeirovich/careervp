import { test, expect } from '@playwright/test';

// spec_id: FE-UI-004
// Component: AppHeader
// Route: all authenticated routes (AppHeader appears via AppShell on every auth route)
// Primary test route: /dashboard (representative authenticated page)

test.describe('AppHeader — credits label and account dropdown', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — e.g. set auth cookie / call login API / use storageState
    // TODO: navigate to /dashboard (representative route for AppHeader)
    // await page.goto('/dashboard');
  });

  // ─── AC-001 / AC-002: Credits label format ───────────────────────────────────

  test('test_credits_label_shows_credits_prefix_format', async ({ page }) => {
    // TODO: ensure user account has creditsUsed=1, creditsTotal=3
    // TODO: assert page.getByText(/Credits: \d+ \/ \d+/) is visible
  });

  // ─── AC-003: Unlimited credits label ─────────────────────────────────────────

  test('test_credits_label_shows_unlimited_for_unlimited_plan', async ({ page }) => {
    // TODO: ensure user account is on unlimited plan
    // TODO: assert page.getByText('Unlimited') is visible
  });

  // ─── AC-004: Dropdown opens with correct items ────────────────────────────────

  test('test_account_dropdown_opens_with_help_logout_upgrade_items', async ({ page }) => {
    // TODO: click the account button (locate by role or test-id)
    // TODO: assert page.getByText('Help') is visible
    // TODO: assert page.getByText('Log out') is visible
    // TODO: assert page.getByText('Upgrade') is visible
  });

  // ─── AC-007: Upgrade navigates to /billing ────────────────────────────────────

  test('test_upgrade_button_navigates_to_billing_when_clicked', async ({ page }) => {
    // TODO: click the account button to open dropdown
    // TODO: click 'Upgrade'
    // TODO: assert page.url() ends with '/billing'
  });

  // ─── AC-008: Outside click closes dropdown ────────────────────────────────────

  test('test_dropdown_closes_when_clicking_outside', async ({ page }) => {
    // TODO: click account button → dropdown opens
    // TODO: click somewhere outside the dropdown (e.g. page heading)
    // TODO: assert dropdown menu is no longer visible
  });

  // ─── AC-009–012: PAGE_TITLES for new and existing routes ─────────────────────

  test('test_page_title_shows_base_cvs_on_cv_center_route', async ({ page }) => {
    // TODO: navigate to /cv-center
    // TODO: assert page.getByRole('heading', { name: 'Base CVs' }) is visible
  });

  test('test_page_title_shows_tailored_cvs_on_tailored_cvs_route', async ({ page }) => {
    // TODO: navigate to /tailored-cvs
    // TODO: assert page.getByRole('heading', { name: 'Tailored CVs' }) is visible
  });

  test('test_page_title_shows_cover_letters_on_cover_letters_route', async ({ page }) => {
    // TODO: navigate to /cover-letters
    // TODO: assert page.getByRole('heading', { name: 'Cover Letters' }) is visible
  });

  test('test_page_title_shows_job_application_hub_on_application_detail_route', async ({ page }) => {
    // TODO: navigate to /applications/<valid-id>
    // TODO: assert page.getByRole('heading', { name: 'Job Application Hub' }) is visible
  });

  // ─── AC-013: Old "X / Y applications" text must not appear ──────────────────

  test('test_old_credits_format_with_applications_suffix_not_visible', async ({ page }) => {
    // TODO: assert page.getByText(/\d+ \/ \d+ applications/).count() resolves to 0
  });

  // ─── Visual regression baseline ──────────────────────────────────────────────

  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: ensure stable auth state and credits value before screenshot
    await expect(page).toHaveScreenshot('dashboard-appheader-baseline.png');
  });

  test('visual regression baseline — dropdown open @slow', async ({ page }) => {
    // TODO: click account button to open dropdown
    // TODO: wait for dropdown animation to settle
    await expect(page).toHaveScreenshot('dashboard-appheader-dropdown-open-baseline.png');
  });

});
