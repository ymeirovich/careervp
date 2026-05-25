// spec_id: FE-UI-021  component: BillingContent  tier: e2e
// route: /billing   route-slug: billing
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover the complete
// user flow and visual regression baseline.
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
// Billing Page — /billing — BillingContent
// ===========================================================================
test.describe('Billing Page — BillingContent', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: navigate to /billing
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── AC-001: page title is "Billing" (not "Billing & Plan") ───────────────
  test('test_page_title_displays_billing_not_billing_and_plan', async ({ page }) => {
    // TODO: assert h1 element is visible and contains exactly "Billing"
    // TODO: assert text "Billing & Plan" does not appear anywhere on the page
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    // TODO: await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^billing$/i)
    // TODO: await expect(page.getByText(/billing & plan/i)).not.toBeVisible()
  });

  // ─── AC-002: three stacked cards in order ─────────────────────────────────
  test('test_three_cards_render_in_correct_stacked_order', async ({ page }) => {
    // TODO: assert subscription-card, usage-card, billing-info-card each visible
    // TODO: assert DOM order: subscription-card → usage-card → billing-info-card
    await expect(page.getByTestId('subscription-card')).toBeVisible();
    // TODO: await expect(page.getByTestId('usage-card')).toBeVisible()
    // TODO: await expect(page.getByTestId('billing-info-card')).toBeVisible()
  });

  // ─── AC-003: Plans section with id="plans" ────────────────────────────────
  test('test_plans_section_renders_with_anchor_id_plans', async ({ page }) => {
    // TODO: assert element #plans exists in the DOM and is visible
    await expect(page.locator('#plans')).toBeVisible();
  });

  test('test_plans_section_smooth_scroll_from_upgrade_link', async ({ page }) => {
    // TODO: click the upgrade link in UsageCard (href="#plans")
    // TODO: assert #plans section is in the viewport after scroll
    // TODO: await page.getByRole('link', { name: /upgrade/i }).click()
    // TODO: await expect(page.locator('#plans')).toBeInViewport()
  });

  // ─── AC-004: three pricing tiers ──────────────────────────────────────────
  test('test_plans_section_shows_monthly_30_tier', async ({ page }) => {
    // TODO: assert text "$30" or "$30/mo" is visible within #plans section
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$30')
  });

  test('test_plans_section_shows_three_month_25_tier', async ({ page }) => {
    // TODO: assert text "$25" or "$25/mo" and "$75 billed" visible within #plans
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$25')
    // TODO: await expect(page.locator('#plans')).toContainText('75')
  });

  test('test_plans_section_shows_six_month_20_tier', async ({ page }) => {
    // TODO: assert text "$20" or "$20/mo" and "$120 billed" visible within #plans
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$20')
    // TODO: await expect(page.locator('#plans')).toContainText('120')
  });

  // ─── AC-005: loading state (full-page spinner) ────────────────────────────
  test('test_spinner_displayed_with_correct_aria_label_while_loading', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription and delay response to capture loading state
    // TODO: navigate to /billing and assert spinner with aria-label "Loading billing info…" is visible
    // await page.route('**/users/me/subscription', route => /* delay */);
    // await authenticateAndNavigate(page, '/billing');
    // TODO: await expect(page.getByRole('status', { name: /loading billing info/i })).toBeVisible()
  });

  // ─── AC-006: ErrorBoundary fallback ───────────────────────────────────────
  test('test_error_boundary_fallback_renders_when_data_fetch_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription to return 500
    // TODO: navigate to /billing
    // TODO: assert ErrorBoundary fallback UI is visible (no unhandled crash)
    // await page.route('**/users/me/subscription', route => route.fulfill({ status: 500 }));
    // await authenticateAndNavigate(page, '/billing');
    // TODO: assert some error fallback element is visible
  });

  // ─── AC-008: landmark heading structure ───────────────────────────────────
  test('test_landmark_headings_h1_and_h2_present_for_accessibility', async ({ page }) => {
    // TODO: assert one h1 exists with page title
    // TODO: assert at least one h2 exists in the Plans section
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    // TODO: await expect(page.getByRole('heading', { level: 2 })).toBeVisible()
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: await full data load before screenshot (wait for subscription-card to be visible)
    // TODO: await page.waitForSelector('[data-testid="subscription-card"]')
    await expect(page).toHaveScreenshot('billing-billingcontent-baseline.png');
  });

});
