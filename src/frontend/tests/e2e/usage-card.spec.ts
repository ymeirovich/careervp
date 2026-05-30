// spec_id: FE-UI-023  component: UsageCard
// route: /billing   route-slug: usage-card
// Framework: Playwright
// Note: UsageCard is embedded in the /billing page (BillingContent).
// These e2e tests cover the complete user flows specific to UsageCard that are
// not covered by billing.spec.ts (BillingContent-scoped tests).
import { test, expect } from '@playwright/test';

// ─── Shared auth helper ────────────────────────────────────────────────────────
async function authenticateAndNavigate(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  route: string
) {
  // TODO: set auth cookies or localStorage token before navigation
  // TODO: await page.context().addCookies([{ name: 'session', value: '<token>', ... }])
  await page.goto(route);
}

// ===========================================================================
// Billing Page — /billing — UsageCard
// ===========================================================================
test.describe('Billing Page — UsageCard @batch6', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate and navigate to /billing
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── AC-001 / AC-002: correct usage text depending on subscription state ──────
  test('test_unlimited_credits_displayed_when_user_has_active_subscription', async ({ page }) => {
    // TODO: ensure test account has active subscription (or mock API via page.route)
    // TODO: await UsageCard data load (wait for skeleton to disappear)
    // TODO: assert text /unlimited credits/i is visible within data-testid="usage-card"
    await expect(page.getByTestId('usage-card')).toBeVisible();
    // TODO: await expect(page.getByTestId('usage-card')).toContainText(/unlimited credits/i)
  });

  test('test_trial_usage_text_displayed_when_user_is_on_trial', async ({ page }) => {
    // TODO: ensure test account is a trial user (or intercept GET /users/me/usage)
    // TODO: await page.route('**/users/me/usage', route => route.fulfill({ ... trial data ... }))
    // TODO: await navigateToPage and assert "X of 3 applications used" is visible
    await expect(page.getByTestId('usage-card')).toBeVisible();
    // TODO: await expect(page.getByTestId('usage-card')).toContainText(/of 3 applications used/)
  });

  // ─── AC-003: progress indicator visible for trial user ───────────────────────
  test('test_progress_indicator_visible_for_trial_user', async ({ page }) => {
    // TODO: intercept GET /users/me/usage to return trial data
    // TODO: await page.route('**/users/me/usage', route => route.fulfill({ ... }))
    // TODO: navigate and assert progress indicator is visible
    await expect(page.getByTestId('usage-card')).toBeVisible();
    // TODO: await expect(page.getByRole('progressbar')).toBeVisible()
  });

  // ─── AC-004 / AC-005: upgrade link smooth-scrolls to #plans ──────────────────
  test('test_upgrade_link_smooth_scrolls_to_plans_section_when_clicked', async ({ page }) => {
    // TODO: await UsageCard to be visible and loaded
    // TODO: click upgrade link: page.getByRole('link', { name: /upgrade subscription to save money/i })
    // TODO: assert #plans section is now in viewport
    await expect(page.getByTestId('usage-card')).toBeVisible();
    // TODO: await page.getByRole('link', { name: /upgrade subscription to save money/i }).click()
    // TODO: await expect(page.locator('#plans')).toBeInViewport()
  });

  // ─── AC-006: loading state — skeleton visible before data ────────────────────
  test('test_skeleton_visible_while_usage_api_is_loading', async ({ page }) => {
    // TODO: intercept GET /users/me/usage to delay response by 2000ms
    // TODO: await page.route('**/users/me/usage', async route => { await delay(2000); route.continue() })
    // TODO: navigate to /billing and assert skeleton is visible before response arrives
    // TODO: await expect(page.getByTestId('usage-card-skeleton')).toBeVisible()
    // TODO: after delay, assert skeleton disappears and content loads
  });

  // ─── AC-007 / AC-008: error state and Retry re-fetches ───────────────────────
  test('test_error_state_displays_retry_button_when_usage_fetch_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/usage to return status 500
    // TODO: await page.route('**/users/me/usage', route => route.fulfill({ status: 500 }))
    // TODO: navigate and assert inline error message is visible
    // TODO: assert Retry button is visible within usage-card
    // TODO: await expect(page.getByTestId('usage-card').getByRole('button', { name: /retry/i })).toBeVisible()
  });

  test('test_retry_button_refetches_usage_data_when_clicked', async ({ page }) => {
    // TODO: intercept GET /users/me/usage: fail first request, succeed second
    // TODO: navigate, await error state, click Retry
    // TODO: assert content renders after successful retry
    // TODO: await expect(page.getByTestId('usage-card')).toContainText(/credits/)
  });

  // ─── AC-009: Hebrew locale — RTL layout ──────────────────────────────────────
  test('test_usage_card_renders_rtl_layout_when_locale_is_hebrew', async ({ page }) => {
    // TODO: navigate to /billing with Hebrew locale (e.g. /he/billing or set Accept-Language header)
    // TODO: assert UsageCard container or progress bar has dir="rtl"
    // TODO: assert usage text is rendered in Hebrew
  });

  // ─── AC-010: ARIA attributes on progress indicator ───────────────────────────
  test('test_progress_indicator_aria_attributes_present_in_trial_state', async ({ page }) => {
    // TODO: intercept GET /users/me/usage to return trial data with applications_used=1
    // TODO: navigate and assert progressbar has aria-valuenow, aria-valuemin, aria-valuemax
    await expect(page.getByTestId('usage-card')).toBeVisible();
    // TODO: const bar = page.getByRole('progressbar')
    // TODO: await expect(bar).toHaveAttribute('aria-valuenow', '1')
    // TODO: await expect(bar).toHaveAttribute('aria-valuemin', '0')
    // TODO: await expect(bar).toHaveAttribute('aria-valuemax', '3')
  });

  // ─── Visual regression baseline ───────────────────────────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: await full data load before screenshot (wait for usage-card data to be visible)
    // TODO: await page.waitForSelector('[data-testid="usage-card"]:not(:has([data-testid="usage-card-skeleton"]))')
    await expect(page).toHaveScreenshot('billing-usagecard-baseline.png');
  });

});
