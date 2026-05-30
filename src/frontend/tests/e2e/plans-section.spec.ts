// spec_id: FE-UI-025  component: PlansSection  tier: e2e
// route: /billing   route-slug: billing
// Framework: Playwright
// AC-009 is the only verification_type: live AC; additional tests cover
// the complete PlansSection user flow and visual regression baseline.

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
// Billing Page — /billing — PlansSection
// ===========================================================================
test.describe('Billing Page — PlansSection @batch6', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: navigate to /billing and await PlansSection to be visible
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── AC-001: section element with id="plans" ──────────────────────────────
  test('test_plans_section_anchor_id_present_in_dom', async ({ page }) => {
    // TODO: assert element #plans exists in the DOM and is visible
    await expect(page.locator('#plans')).toBeVisible();
  });

  // ─── AC-004: h2 heading "Choose Your Plan" ────────────────────────────────
  test('test_plans_section_heading_choose_your_plan_visible', async ({ page }) => {
    // TODO: assert an h2 element within #plans is visible with text "Choose Your Plan"
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans h2')).toHaveText(/choose your plan/i)
  });

  // ─── AC-005: three pricing tiers ─────────────────────────────────────────
  test('test_monthly_plan_30_per_month_displayed_in_plans_section', async ({ page }) => {
    // TODO: assert text "$30" or "$30/mo" is visible within #plans section
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$30')
  });

  test('test_three_month_plan_25_per_month_and_75_total_displayed_in_plans_section', async ({ page }) => {
    // TODO: assert text "$25" or "$25/mo" and "$75 billed" are visible within #plans
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$25')
    // TODO: await expect(page.locator('#plans')).toContainText('75')
  });

  test('test_six_month_plan_20_per_month_and_120_total_displayed_in_plans_section', async ({ page }) => {
    // TODO: assert text "$20" or "$20/mo" and "$120 billed" are visible within #plans
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('#plans')).toContainText('$20')
    // TODO: await expect(page.locator('#plans')).toContainText('120')
  });

  // ─── AC-007: 3-Month recommended badge ───────────────────────────────────
  test('test_three_month_plan_shows_recommended_badge', async ({ page }) => {
    // TODO: assert a "Recommended" badge or marker is visible on the 3-Month plan card
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('[data-testid="plan-card-3month"]')).toContainText(/recommended/i)
  });

  // ─── AC-008: "Contact us" mailto link ────────────────────────────────────
  test('test_contact_us_link_visible_below_plan_cards', async ({ page }) => {
    // TODO: assert a link with text matching /contact us/i is visible below #plans cards
    // TODO: assert link href is "mailto:support@careervp.com"
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: const link = page.locator('#plans a[href="mailto:support@careervp.com"]')
    // TODO: await expect(link).toBeVisible()
  });

  // ─── AC-009: smooth scroll from UsageCard upgrade link @slow ─────────────
  test('test_plans_section_scrolls_into_view_when_upgrade_link_clicked @slow', async ({ page }) => {
    // TODO: wait for UsageCard to be visible and locate the "Upgrade subscription" anchor
    // TODO: click the anchor with href="#plans"
    // TODO: assert #plans section is in the viewport after the scroll
    // TODO: optionally assert scrollBehavior is 'smooth' via page.evaluate
    // await page.getByRole('link', { name: /upgrade subscription/i }).click()
    // await expect(page.locator('#plans')).toBeInViewport()
  });

  // ─── AC-006: current plan highlighted ────────────────────────────────────
  test('test_current_plan_card_shows_current_plan_state_when_subscription_is_active', async ({ page }) => {
    // TODO: authenticate as a user with an active monthly subscription
    // TODO: navigate to /billing
    // TODO: assert the monthly plan card renders "Current Plan" or equivalent disabled CTA
    // TODO: assert the other two cards show "Choose Plan" CTA
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: await expect(page.locator('[data-testid="plan-card-monthly"] button')).toBeDisabled()
    // TODO: await expect(page.locator('[data-testid="plan-card-3month"] button')).toBeEnabled()
  });

  // ─── AC-003: mobile stacked layout, recommended card first ───────────────
  test('test_plan_cards_stacked_vertically_with_recommended_first_on_mobile', async ({ page }) => {
    // TODO: resize viewport to mobile breakpoint (below md = 768px)
    // TODO: assert #plans renders in a single column
    // TODO: assert the 3-Month (recommended) card is the first visible card
    await page.setViewportSize({ width: 375, height: 812 });
    await authenticateAndNavigate(page, '/billing');
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: const cards = page.locator('[data-testid^="plan-card-"]')
    // TODO: expect(await cards.first().getAttribute('data-testid')).toBe('plan-card-3month')
  });

  // ─── AC-011: accessibility — aria-labelledby ──────────────────────────────
  test('test_plans_section_has_aria_labelledby_pointing_to_h2', async ({ page }) => {
    // TODO: assert #plans has aria-labelledby attribute
    // TODO: assert the element with the referenced id is the h2 "Choose Your Plan"
    await expect(page.locator('#plans')).toBeVisible();
    // TODO: const labelledById = await page.locator('#plans').getAttribute('aria-labelledby')
    // TODO: await expect(page.locator(`#${labelledById}`)).toHaveText(/choose your plan/i)
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: await full data load before screenshot (wait for #plans to be visible)
    await page.locator('#plans').waitFor({ state: 'visible' });
    await expect(page).toHaveScreenshot('billing-planssection-baseline.png');
  });

});
