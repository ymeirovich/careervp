// spec_id: FE-UI-024  component: BillingInfoCard  tier: e2e
// Route: /billing   route-slug: billing-billinginfocard
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover complete user
// flows and the visual regression baseline for BillingInfoCard on /billing.
//
// NOTE: Integration testing of POST /billing/portal is partially blocked
// until the backend prerequisite ships (GET /users/me/subscription returning
// payment_method.last4 + brand). Use API route intercepts in the interim.

import { test, expect } from '@playwright/test';

// ─── Shared auth + navigation helper ─────────────────────────────────────────
async function authenticateAndNavigate(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  route: string
): Promise<void> {
  // TODO: set auth cookies or localStorage token before navigation
  // TODO: await page.context().addCookies([{ name: 'session', value: '<token>', domain: 'localhost' }])
  await page.goto(route);
}

// ─── Shared intercept helpers ─────────────────────────────────────────────────
async function interceptSubscriptionWithPayment(
  page: Parameters<Parameters<typeof test>[1]>[0]['page']
): Promise<void> {
  // TODO: intercept GET /users/me/subscription and respond with payment_method fixture
  await page.route('**/users/me/subscription', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        has_active_subscription: true,
        payment_method: { last4: '6363', brand: 'visa' },
        subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
      }),
    })
  );
}

async function interceptSubscriptionNoPayment(
  page: Parameters<Parameters<typeof test>[1]>[0]['page']
): Promise<void> {
  // TODO: intercept GET /users/me/subscription and respond with null payment_method
  await page.route('**/users/me/subscription', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        has_active_subscription: true,
        payment_method: null,
        subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
      }),
    })
  );
}

async function interceptBillingPortal(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  portalUrl = 'https://billing.stripe.com/session/test-session-id'
): Promise<void> {
  // TODO: intercept POST /billing/portal and respond with a portal URL
  await page.route('**/billing/portal', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ url: portalUrl }),
    })
  );
}

// =============================================================================
// Billing Page — /billing — BillingInfoCard
// =============================================================================
test.describe('Billing Page — BillingInfoCard @batch6', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: default subscription intercept — override per test where needed
    await interceptSubscriptionWithPayment(page);
    await authenticateAndNavigate(page, '/billing');
  });

  // ─── AC-001: masked card number displayed ─────────────────────────────────
  test('test_masked_card_number_visible_when_subscription_has_payment_method', async ({ page }) => {
    // TODO: await billing-info-card to be visible
    // TODO: assert text "•••• 6363" is visible within the BillingInfoCard
    // TODO: assert text "(Visa)" or "(visa)" is visible alongside the masked number
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    // TODO: await expect(page.getByTestId('billing-info-card')).toContainText('•••• 6363')
    // TODO: await expect(page.getByTestId('billing-info-card')).toContainText('Visa')
  });

  // ─── AC-002: empty state (no payment method) ──────────────────────────────
  test('test_no_payment_method_state_renders_when_subscription_has_null_payment', async ({ page }) => {
    // TODO: override subscription intercept before navigation for this test
    // TODO: reload with SUBSCRIPTION_NO_PAYMENT fixture
    // TODO: assert "No payment method" is visible within BillingInfoCard
    // TODO: assert "Add Payment Method" button is visible
    await page.unroute('**/users/me/subscription');
    await interceptSubscriptionNoPayment(page);
    await page.reload();
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    // TODO: await expect(page.getByTestId('billing-info-card')).toContainText('No payment method')
    // TODO: await expect(page.getByRole('button', { name: /add payment method/i })).toBeVisible()
  });

  // ─── AC-003: Stripe trust line ────────────────────────────────────────────
  test('test_stripe_trust_text_visible_when_payment_method_present', async ({ page }) => {
    // TODO: await BillingInfoCard visible with payment method data
    // TODO: assert "Billing handled securely via Stripe." text is visible
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    // TODO: await expect(page.getByText(/billing handled securely via stripe/i)).toBeVisible()
  });

  // ─── AC-004: Manage Billing CTA → portal → new tab ───────────────────────
  test('test_manage_billing_opens_stripe_portal_in_new_tab', async ({ page, context }) => {
    // TODO: intercept POST /billing/portal to return a portal URL
    // TODO: listen for new page/tab event
    // TODO: click "Manage Billing" button
    // TODO: assert new tab opens with the portal URL (or window.open was called)
    await interceptBillingPortal(page);
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    const newPagePromise = context.waitForEvent('page');
    // TODO: await page.getByRole('button', { name: /manage billing/i }).click()
    // TODO: const newPage = await newPagePromise
    // TODO: await expect(newPage.url()).toContain('billing.stripe.com')
  });

  // ─── AC-005: Add Payment Method CTA → portal → new tab ───────────────────
  test('test_add_payment_method_opens_stripe_portal_in_new_tab', async ({ page, context }) => {
    // TODO: set subscription to no-payment-method state
    // TODO: intercept POST /billing/portal to return a portal URL
    // TODO: click "Add Payment Method" button
    // TODO: assert new tab opens with the portal URL
    await page.unroute('**/users/me/subscription');
    await interceptSubscriptionNoPayment(page);
    await interceptBillingPortal(page);
    await page.reload();
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    const newPagePromise = context.waitForEvent('page');
    // TODO: await page.getByRole('button', { name: /add payment method/i }).click()
    // TODO: const newPage = await newPagePromise
    // TODO: await expect(newPage.url()).toContain('billing.stripe.com')
    void newPagePromise; // suppress unused-var warning until implemented
  });

  // ─── AC-006: loading state — skeleton shimmer ─────────────────────────────
  test('test_skeleton_placeholder_visible_while_subscription_data_loading', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription with an artificial delay
    // TODO: navigate to /billing and immediately assert skeleton is visible
    // TODO: await full data load and assert skeleton is gone
    await page.unroute('**/users/me/subscription');
    await page.route('**/users/me/subscription', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      // TODO: route.fulfill({ status: 200, ... })
      await route.continue();
    });
    await authenticateAndNavigate(page, '/billing');
    // TODO: await expect(page.getByTestId('billing-info-card-skeleton')).toBeVisible()
  });

  // ─── AC-007 + AC-008: error state → Retry button → refetch ───────────────
  test('test_retry_button_visible_and_refetches_when_subscription_api_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/subscription to return 500
    // TODO: navigate to /billing, assert Retry button visible in BillingInfoCard
    // TODO: re-intercept to return success, click Retry, assert card data appears
    await page.unroute('**/users/me/subscription');
    await page.route('**/users/me/subscription', (route) =>
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    );
    await page.reload();
    // TODO: await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
    // TODO: await page.unroute('**/users/me/subscription')
    // TODO: await interceptSubscriptionWithPayment(page)
    // TODO: await page.getByRole('button', { name: /retry/i }).click()
    // TODO: await expect(page.getByText(/•••• 6363/)).toBeVisible()
  });

  // ─── AC-009: portal POST failure → inline error, no new tab ──────────────
  test('test_inline_error_shown_and_no_tab_opened_when_portal_post_fails', async ({ page }) => {
    // TODO: intercept POST /billing/portal to return 500
    // TODO: click "Manage Billing", assert no new tab opened
    // TODO: assert inline error message is visible inside BillingInfoCard
    await page.route('**/billing/portal', (route) =>
      route.fulfill({ status: 500, body: 'Portal unavailable' })
    );
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    // TODO: await page.getByRole('button', { name: /manage billing/i }).click()
    // TODO: await expect(page.getByRole('alert')).toBeVisible()
  });

  // ─── AC-010: Hebrew locale — RTL layout ───────────────────────────────────
  test('test_rtl_layout_and_hebrew_text_when_locale_is_he', async ({ page }) => {
    // TODO: set locale to Hebrew (via cookie, URL param, or localStorage) before navigation
    // TODO: navigate to /billing
    // TODO: assert dir="rtl" is present on the BillingInfoCard wrapper element
    // TODO: assert card heading text is in Hebrew
    await page.goto('/billing?locale=he');
    // TODO: await expect(page.getByTestId('billing-info-card')).toHaveAttribute('dir', 'rtl')
    // TODO: await expect(page.getByTestId('billing-info-card')).toContainText(/<hebrew-billing-info-text>/)
  });

  // ─── AC-011: aria-label on masked card element ────────────────────────────
  test('test_masked_card_has_correct_aria_label_when_payment_method_present', async ({ page }) => {
    // TODO: await BillingInfoCard with payment method data visible
    // TODO: assert element with aria-label "Payment method ending in 6363, visa" exists in DOM
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    // TODO: await expect(page.getByLabel('Payment method ending in 6363, visa')).toBeVisible()
  });

  // ─── AC-012: keyboard navigation ─────────────────────────────────────────
  test('test_manage_billing_button_reachable_via_keyboard_when_payment_method_present', async ({ page }) => {
    // TODO: focus the BillingInfoCard section
    // TODO: Tab through interactive elements and assert "Manage Billing" button receives focus
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    await page.getByTestId('billing-info-card').focus();
    // TODO: await page.keyboard.press('Tab') — repeat until Manage Billing receives focus
    // TODO: await expect(page.getByRole('button', { name: /manage billing/i })).toBeFocused()
  });

  // ─── Visual regression baseline ───────────────────────────────────────────
  test('visual regression baseline — has-payment-method state @slow', async ({ page }) => {
    // TODO: await BillingInfoCard fully loaded (payment method text visible)
    // TODO: await page.waitForSelector('[data-testid="billing-info-card"]')
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    await expect(page).toHaveScreenshot('billing-billinginfocard-has-payment-baseline.png');
  });

  test('visual regression baseline — no-payment-method state @slow', async ({ page }) => {
    // TODO: set subscription to no-payment-method state and reload
    await page.unroute('**/users/me/subscription');
    await interceptSubscriptionNoPayment(page);
    await page.reload();
    // TODO: await page.waitForSelector('[data-testid="billing-info-card"]')
    await expect(page.getByTestId('billing-info-card')).toBeVisible();
    await expect(page).toHaveScreenshot('billing-billinginfocard-no-payment-baseline.png');
  });

});
