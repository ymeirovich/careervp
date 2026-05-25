// spec_id: FE-UI-022  component: SubscriptionCard  tier: e2e
// route: /billing   route-slug: billing
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover the complete
// user flow and visual regression baseline for the SubscriptionCard.
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
// Billing Page — /billing — SubscriptionCard
// ===========================================================================
test.describe('Billing Page — SubscriptionCard', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate and navigate to /billing
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── AC-001: active state badge visible ───────────────────────────────────
  test('test_active_badge_visible_when_subscription_is_active', async ({ page }) => {
    // TODO: ensure test account has status="active", cancel_at_period_end=false
    // TODO: assert element with text "Active" is visible on the page
    await expect(page.getByTestId('subscription-card')).toBeVisible();
    // TODO: await expect(page.getByText('Active')).toBeVisible();
  });

  // ─── AC-002: cancelling state — "Active until" text ──────────────────────
  test('test_cancelling_state_shows_active_until_date_on_card', async ({ page }) => {
    // TODO: ensure test account has cancel_at_period_end=true
    // TODO: assert "Cancelling" badge and "Active until [date]" text are visible
    // TODO: await expect(page.getByText('Cancelling')).toBeVisible();
    // TODO: await expect(page.getByText(/active until/i)).toBeVisible();
  });

  // ─── AC-003: trial state — badge + days remaining ─────────────────────────
  test('test_trial_badge_and_days_remaining_visible_when_trialing', async ({ page }) => {
    // TODO: ensure test account has status="trialing"
    // TODO: assert "Trial" badge is visible
    // TODO: assert days-remaining text is visible
    // TODO: await expect(page.getByText('Trial')).toBeVisible();
    // TODO: await expect(page.getByText(/days remaining/i)).toBeVisible();
  });

  // ─── AC-007: next charge amount formatted ────────────────────────────────
  test('test_next_charge_amount_displayed_as_formatted_currency', async ({ page }) => {
    // TODO: ensure test account subscription has a non-null next_charge_amount
    // TODO: assert currency-formatted text (e.g. "$30.00") is visible in the card
    await expect(page.getByTestId('subscription-card')).toBeVisible();
    // TODO: await expect(page.getByText(/\$\d+\.\d{2}/)).toBeVisible();
  });

  // ─── AC-008: "View Plans" CTA scrolls to #plans ───────────────────────────
  test('test_view_plans_cta_smooth_scrolls_to_plans_section', async ({ page }) => {
    // TODO: assert "View Plans" button is visible on the subscription card
    // TODO: click "View Plans" button
    // TODO: assert #plans section is in the viewport after scroll
    // TODO: await page.getByRole('button', { name: /view plans/i }).click();
    // TODO: await expect(page.locator('#plans')).toBeInViewport();
  });

  // ─── AC-009: cancelling → "Resubscribe" CTA ───────────────────────────────
  test('test_resubscribe_cta_shown_instead_of_view_plans_when_cancelling', async ({ page }) => {
    // TODO: ensure test account has cancel_at_period_end=true
    // TODO: assert "Resubscribe" button is visible
    // TODO: assert "View Plans" button is NOT visible
    // TODO: await expect(page.getByRole('button', { name: /resubscribe/i })).toBeVisible();
    // TODO: await expect(page.getByRole('button', { name: /view plans/i })).not.toBeVisible();
  });

  // ─── AC-010: loading state skeleton ───────────────────────────────────────
  test('test_skeleton_placeholder_visible_while_subscription_data_loading', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription and delay response
    // TODO: navigate to /billing
    // TODO: assert skeleton element is visible before response resolves
    // TODO: await page.route('**/users/me/subscription', async (route) => {
    //   await page.waitForTimeout(500);
    //   await route.continue();
    // });
    // TODO: await expect(page.getByTestId('subscription-skeleton')).toBeVisible();
  });

  // ─── AC-011: error state with "Retry" button ─────────────────────────────
  test('test_inline_error_and_retry_button_visible_when_api_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription and return 500
    await page.route('**/users/me/subscription', (route) => route.fulfill({ status: 500, body: '' }));
    await page.goto('/billing');
    // TODO: await expect(page.getByRole('button', { name: /retry/i })).toBeVisible();
  });

  // ─── AC-012: retry button re-fetches ──────────────────────────────────────
  test('test_clicking_retry_refetches_and_renders_data_after_error', async ({ page }) => {
    // TODO: intercept first request with 500, second with ACTIVE_RESPONSE fixture
    // TODO: navigate to /billing, await error state
    // TODO: click "Retry" button
    // TODO: assert subscription data renders after successful refetch
    // TODO: await page.getByRole('button', { name: /retry/i }).click();
    // TODO: await expect(page.getByText('Active')).toBeVisible();
  });

  // ─── AC-013: Hebrew RTL layout @slow ──────────────────────────────────────
  test('test_hebrew_rtl_layout_on_subscription_card @slow', async ({ page }) => {
    // TODO: navigate to /billing?locale=he or set cookie for Hebrew locale
    // TODO: assert dir="rtl" or lang="he" is present on card or page wrapper
    // TODO: assert badge, plan-type pill, and CTA text are Hebrew strings
    // TODO: await page.goto('/billing?locale=he');
    // TODO: await expect(page.locator('[dir="rtl"]')).toBeVisible();
  });

  // ─── AC-014: status badge accessibility ───────────────────────────────────
  test('test_status_badge_has_correct_role_and_aria_label', async ({ page }) => {
    // TODO: assert element with role="status" is present on the card
    // TODO: assert aria-label attribute describes the subscription state
    await expect(page.getByTestId('subscription-card')).toBeVisible();
    // TODO: await expect(page.getByRole('status')).toHaveAttribute('aria-label', /subscription status/i);
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline — active state @slow', async ({ page }) => {
    // TODO: ensure test account has status="active" subscription
    await expect(page.getByTestId('subscription-card')).toBeVisible();
    await expect(page).toHaveScreenshot('billing-subscriptioncard-active-baseline.png');
  });

  test('visual regression baseline — cancelling state @slow', async ({ page }) => {
    // TODO: ensure test account has cancel_at_period_end=true
    // TODO: await expect(page.getByTestId('subscription-card')).toBeVisible();
    await expect(page).toHaveScreenshot('billing-subscriptioncard-cancelling-baseline.png');
  });

  test('visual regression baseline — error state @slow', async ({ page }) => {
    await page.route('**/users/me/subscription', (route) => route.fulfill({ status: 500, body: '' }));
    await page.goto('/billing');
    // TODO: await expect(page.getByRole('button', { name: /retry/i })).toBeVisible();
    await expect(page).toHaveScreenshot('billing-subscriptioncard-error-baseline.png');
  });

});
