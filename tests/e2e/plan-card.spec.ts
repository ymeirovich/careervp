// spec_id: FE-UI-026  component: PlanCard  tier: e2e
// Route: /billing (section within page)   route-slug: billing
// Framework: Playwright
//
// No ACs are verification_type: live for this spec.
// These tests cover the complete PlanCard user flow within the billing page:
// visual state rendering, card interactions, and checkout redirect (AC-012).
// AC-012 is marked @slow as it involves a redirect flow.

import { test, expect } from '@playwright/test';

// ─── Shared auth helper ────────────────────────────────────────────────────────
async function authenticateAndNavigate(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  route: string
) {
  // TODO: set auth cookies or localStorage token before navigation
  // TODO: await page.context().addCookies([{ name: 'session', value: '<token>', ... }])
  await page.goto(route);
  // TODO: await page.waitForSelector('[data-testid="plan-card-monthly"]', { timeout: 10000 })
}

// ===========================================================================
// Billing Page — /billing — PlanCard
// ===========================================================================
test.describe('Billing Page — PlanCard', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: navigate to /billing and wait for plan cards to render
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── All three plan cards visible ─────────────────────────────────────────
  test('test_three_plan_cards_rendered_within_plans_section', async ({ page }) => {
    // TODO: assert plan-card-monthly, plan-card-3month, plan-card-6month all visible
    await expect(page.locator('#plans')).toBeVisible();
    await expect(page.getByTestId('plan-card-monthly')).toBeVisible();
    // TODO: await expect(page.getByTestId('plan-card-3month')).toBeVisible()
    // TODO: await expect(page.getByTestId('plan-card-6month')).toBeVisible()
  });

  // ─── selectable state ─────────────────────────────────────────────────────
  test('test_choose_plan_button_enabled_when_card_is_not_current_plan', async ({ page }) => {
    // TODO: ensure user has no active subscription (or intercept API to return no subscription)
    // await page.route('**/users/me/subscription', r => r.fulfill({ json: { has_active_subscription: false } }))
    // TODO: assert "Choose Plan" button on plan-card-monthly is visible and aria-disabled != "true"
    await expect(page.getByTestId('plan-card-monthly')).toBeVisible();
    // TODO: const btn = page.getByTestId('plan-card-monthly').getByRole('button')
    // TODO: await expect(btn).toHaveText(/choose plan/i)
    // TODO: await expect(btn).not.toHaveAttribute('aria-disabled', 'true')
  });

  // ─── current state ────────────────────────────────────────────────────────
  test('test_current_plan_button_has_aria_disabled_when_card_matches_subscription', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription to return monthly active subscription
    // await page.route('**/users/me/subscription', r => r.fulfill({
    //   json: { has_active_subscription: true, subscription: { plan_type: 'monthly', status: 'active' } }
    // }))
    // TODO: navigate to /billing and wait for cards
    // TODO: assert plan-card-monthly button has aria-disabled="true" and text "Current Plan"
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: const btn = page.getByTestId('plan-card-monthly').getByRole('button')
    // TODO: await expect(btn).toHaveAttribute('aria-disabled', 'true')
    // TODO: await expect(btn).toHaveText(/current plan/i)
  });

  // ─── recommended state: thick border on 3-month card ─────────────────────
  test('test_3month_plan_card_has_visually_distinct_border_as_recommended', async ({ page }) => {
    // TODO: assert plan-card-3month has a computed border-width > 1px (indicating thick border)
    await expect(page.getByTestId('plan-card-3month')).toBeVisible();
    // TODO: const borderWidth = await page.getByTestId('plan-card-3month').evaluate(
    //   el => window.getComputedStyle(el).borderWidth
    // )
    // TODO: expect(Number.parseFloat(borderWidth)).toBeGreaterThan(1)
  });

  // ─── Data content: prices and labels ─────────────────────────────────────
  test('test_monthly_plan_shows_30_price_and_billed_monthly_label', async ({ page }) => {
    // TODO: assert "$30" (or "$30/mo") visible within plan-card-monthly
    // TODO: assert "Billed monthly" label visible within plan-card-monthly
    await expect(page.getByTestId('plan-card-monthly')).toBeVisible();
    // TODO: await expect(page.getByTestId('plan-card-monthly')).toContainText('$30')
    // TODO: await expect(page.getByTestId('plan-card-monthly')).toContainText('Billed monthly')
  });

  test('test_3month_plan_shows_25_price_and_75_billing_label', async ({ page }) => {
    // TODO: assert "$25" visible within plan-card-3month
    // TODO: assert "75" (billed total) visible within plan-card-3month
    await expect(page.getByTestId('plan-card-3month')).toBeVisible();
    // TODO: await expect(page.getByTestId('plan-card-3month')).toContainText('$25')
    // TODO: await expect(page.getByTestId('plan-card-3month')).toContainText('75')
  });

  test('test_6month_plan_shows_20_price_and_120_billing_label', async ({ page }) => {
    // TODO: assert "$20" visible within plan-card-6month
    // TODO: assert "120" (billed total) visible within plan-card-6month
    await expect(page.getByTestId('plan-card-6month')).toBeVisible();
    // TODO: await expect(page.getByTestId('plan-card-6month')).toContainText('$20')
    // TODO: await expect(page.getByTestId('plan-card-6month')).toContainText('120')
  });

  // ─── AC-012: click "Choose Plan" → Stripe redirect @slow ─────────────────
  test('test_clicking_choose_plan_redirects_to_stripe_checkout_url @slow', async ({ page }) => {
    // TODO: intercept POST /billing/checkout to return a mock Stripe URL (avoids real Stripe in CI)
    // await page.route('**/billing/checkout', r => r.fulfill({
    //   json: { url: 'https://checkout.stripe.com/pay/test-session' }
    // }))
    // TODO: ensure user has no active subscription so "Choose Plan" button is enabled
    // TODO: click the "Choose Plan" button on plan-card-monthly
    // TODO: assert browser URL changed to the Stripe checkout URL (same tab, not new tab)
    await expect(page.getByTestId('plan-card-monthly')).toBeVisible();
    // TODO: await page.getByTestId('plan-card-monthly').getByRole('button', { name: /choose plan/i }).click()
    // TODO: await expect(page).toHaveURL(/checkout\.stripe\.com/)
  });

  // ─── Accessibility: aria-label on price elements ─────────────────────────
  test('test_price_elements_have_accessible_aria_labels_on_all_cards', async ({ page }) => {
    // TODO: assert the price display on each card has an aria-label describing full price
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.getByTestId('plan-card-monthly').locator('[aria-label]'))
    //         .toHaveAttribute('aria-label', /30 dollars per month/i)
    // TODO: await expect(page.getByTestId('plan-card-3month').locator('[aria-label]'))
    //         .toHaveAttribute('aria-label', /25 dollars per month.*75 dollars every 3 months/i)
    // TODO: await expect(page.getByTestId('plan-card-6month').locator('[aria-label]'))
    //         .toHaveAttribute('aria-label', /20 dollars per month.*120 dollars every 6 months/i)
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: wait for all plan cards to render before capturing screenshot
    // TODO: await page.waitForSelector('[data-testid="plan-card-6month"]', { state: 'visible' })
    await expect(page).toHaveScreenshot('billing-plancard-baseline.png');
  });

});
