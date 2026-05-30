// spec_id: FE-UI-010  component: NewApplicationPage  tier: e2e
// route: /applications/new   route-slug: new-application
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover the complete
// user flow and visual regression baseline.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// shared auth helper — fill in once real auth is in place
// ---------------------------------------------------------------------------
async function authenticateAndNavigate(page: Parameters<Parameters<typeof test>[1]>[0]['page'], route: string) {
  // TODO: set auth cookies or localStorage token
  // TODO: await page.goto(route)
  await page.goto(route);
}

// ===========================================================================
// New Application Page — /applications/new
// ===========================================================================
test.describe('New Application Page — NewApplicationPage', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: navigate to /applications/new
    await authenticateAndNavigate(page, '/applications/new');
  });

  // ─── AC-001: dashboard navigates to /applications/new ────────────────────
  test('test_plus_new_application_navigates_to_new_page_when_dashboard_button_clicked', async ({ page }) => {
    // TODO: navigate to /dashboard
    // TODO: click '+ New Application' button
    // TODO: expect(page).toHaveURL('/applications/new')
    await page.goto('/dashboard');
    // TODO: await page.getByRole('button', { name: /new application/i }).click()
    // TODO: await expect(page).toHaveURL('/applications/new')
  });

  // ─── AC-002 + AC-003: back link visible and functional ───────────────────
  test('test_back_link_navigates_to_dashboard_when_clicked', async ({ page }) => {
    // TODO: assert back link is visible
    // TODO: click back link
    // TODO: expect(page).toHaveURL('/dashboard')
    // TODO: await page.getByRole('link', { name: /back/i }).click()
    // TODO: await expect(page).toHaveURL('/dashboard')
  });

  // ─── AC-004: card layout, not modal overlay ───────────────────────────────
  test('test_form_renders_in_card_not_modal_overlay_when_page_loaded', async ({ page }) => {
    // TODO: assert no element with role="dialog" is visible
    // TODO: assert a card/container element with constrained max-width is visible
    await expect(page.getByRole('dialog')).toHaveCount(0);
    // TODO: assert card element has max-width style or class
  });

  // ─── AC-005 + AC-006 + AC-007: four fields and submit button disabled/enabled
  test('test_create_button_disabled_until_required_fields_filled', async ({ page }) => {
    // TODO: assert Create Application button is disabled on load
    // TODO: fill Job Title, Company Name, Job Description
    // TODO: assert Create Application button becomes enabled
    // TODO: assert Job URL field is present but not required
    const createBtn = page.getByRole('button', { name: /create application/i });
    // TODO: await expect(createBtn).toBeDisabled()
    // TODO: await page.getByLabel(/job title/i).fill('Software Engineer')
    // TODO: await page.getByLabel(/company name/i).fill('Acme Corp')
    // TODO: await page.getByLabel(/job description/i).fill('Build and maintain software.')
    // TODO: await expect(createBtn).toBeEnabled()
  });

  // ─── AC-008 + AC-009: Base CV section and Change button opens modal ────────
  test('test_choose_base_cv_modal_opens_when_change_clicked', async ({ page }) => {
    // TODO: assert "Base CV" section is visible
    // TODO: click "Change" button
    // TODO: assert modal dialog with "Choose Base CV" heading is visible
    // TODO: await page.getByRole('button', { name: /^change$/i }).click()
    // TODO: await expect(page.getByRole('dialog', { name: /choose base cv/i })).toBeVisible()
  });

  // ─── AC-011 + AC-012: loading state during submission ─────────────────────
  test('test_button_shows_creating_and_inputs_disabled_during_submission @slow', async ({ page }) => {
    // TODO: intercept POST /jobs to delay response (page.route with route.continue after delay)
    // TODO: fill required fields, click Create Application
    // TODO: immediately assert button text is "Creating..." and button is disabled
    // TODO: assert all form inputs are disabled
    // TODO: assert Cancel button is disabled
    await page.route('**/jobs', async (route) => {
      // TODO: await new Promise(resolve => setTimeout(resolve, 3000)); route.continue()
      await route.continue();
    });
    // TODO: fill and submit, assert loading state
  });

  // ─── AC-013: successful submission navigates to /applications/{job_id} ────
  test('test_navigates_to_application_page_when_submission_succeeds', async ({ page }) => {
    // TODO: intercept POST /jobs to return { job_id: 'test-job-1' }
    // TODO: fill required fields and submit
    // TODO: await expect(page).toHaveURL('/applications/test-job-1')
    await page.route('**/jobs', async (route) => {
      // TODO: route.fulfill({ status: 200, body: JSON.stringify({ job_id: 'test-job-1' }) })
      await route.continue();
    });
    // TODO: fill fields, submit, assert URL
  });

  // ─── AC-014: error banner on API failure ──────────────────────────────────
  test('test_error_banner_visible_when_api_returns_error', async ({ page }) => {
    // TODO: intercept POST /jobs to return 500 with error message body
    // TODO: fill required fields and submit
    // TODO: assert role="alert" banner is visible with error message text
    await page.route('**/jobs', async (route) => {
      // TODO: route.fulfill({ status: 500, body: JSON.stringify({ message: 'Internal error' }) })
      await route.continue();
    });
    // TODO: fill, submit, await expect(page.getByRole('alert')).toBeVisible()
  });

  // ─── AC-016: Cancel navigates without submitting ──────────────────────────
  test('test_cancel_navigates_to_dashboard_without_submitting', async ({ page }) => {
    // TODO: fill some fields
    // TODO: assert POST /jobs is never called (page.route intercept with assertion)
    // TODO: click Cancel, await expect(page).toHaveURL('/dashboard')
    let postJobsCalled = false;
    await page.route('**/jobs', async (route) => {
      postJobsCalled = true;
      await route.continue();
    });
    // TODO: click cancel, navigate, assert postJobsCalled === false
  });

  // ─── AC-020: keyboard tab order ───────────────────────────────────────────
  test('test_keyboard_tab_order_follows_visual_order_top_to_bottom', async ({ page }) => {
    // TODO: page.keyboard.press('Tab') repeatedly
    // TODO: assert focus sequence:
    //   Back link → Job Title → Company Name → Job Description
    //   → Job URL → Base CV Change → Cancel → Create Application
    // TODO: after each Tab, assert document.activeElement matches expected element
  });

  // ─── AC-021: Hebrew strings when locale is he ─────────────────────────────
  test('test_hebrew_strings_rendered_when_locale_is_he', async ({ page }) => {
    // TODO: navigate to /applications/new with locale=he (query param or cookie)
    // TODO: assert '← חזרה' text visible
    // TODO: assert 'שנה' (Change) button text visible
    // TODO: assert form labels are in Hebrew
    await page.goto('/applications/new?locale=he');
    // TODO: await expect(page.getByText(/← חזרה/)).toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /שנה/ })).toBeVisible()
  });

  // ─── AC-022: RTL layout when locale is Hebrew ─────────────────────────────
  test('test_layout_direction_is_rtl_when_locale_he', async ({ page }) => {
    // TODO: navigate with Hebrew locale
    // TODO: assert document.documentElement.dir === 'rtl'
    await page.goto('/applications/new?locale=he');
    // TODO: const dir = await page.evaluate(() => document.documentElement.dir)
    // TODO: expect(dir).toBe('rtl')
  });

  // ─── AC-023: responsive — mobile viewport ────────────────────────────────
  test('test_form_card_has_no_horizontal_overflow_on_mobile_viewport', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 375, height: 812 })
    // TODO: navigate to /applications/new
    // TODO: assert document.body.scrollWidth <= 375 (no horizontal overflow)
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/applications/new');
    // TODO: const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
    // TODO: expect(scrollWidth).toBeLessThanOrEqual(375)
  });

  // ─── visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: ensure page is in stable default state (no loading, no error)
    await expect(page).toHaveScreenshot('new-application-page-baseline.png');
  });

  // ─── visual regression baseline — mobile ──────────────────────────────────
  test('visual regression baseline mobile @slow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await expect(page).toHaveScreenshot('new-application-page-mobile-baseline.png');
  });

  // ─── visual regression baseline — error state ─────────────────────────────
  test('visual regression baseline error state @slow', async ({ page }) => {
    // TODO: intercept POST /jobs → 500, fill and submit, await error banner
    await page.route('**/jobs', async (route) => {
      // TODO: route.fulfill({ status: 500, body: JSON.stringify({ message: 'Test error' }) })
      await route.continue();
    });
    // TODO: fill, submit, await error banner, then screenshot
    await expect(page).toHaveScreenshot('new-application-page-error-baseline.png');
  });

});
