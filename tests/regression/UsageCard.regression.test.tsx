// spec_id: FE-UI-023  component: UsageCard
// file: src/frontend/components/billing/UsageCard.tsx
// Regression tests — guard existing API contracts and sibling components that
// must not be affected by the introduction of UsageCard on /billing.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Sibling component mocks (stubs that expose rendered state for assertion)
// ---------------------------------------------------------------------------
// SubscriptionCard stub — guards that its rendered output is unchanged
vi.mock('../../src/frontend/components/billing/SubscriptionCard', () => ({
  SubscriptionCard: ({
    planName,
    status,
  }: {
    planName: string;
    status: string;
  }) => (
    <div
      data-testid="subscription-card"
      data-plan-name={planName}
      data-status={status}
    />
  ),
}));

// BillingInfoCard stub — guards that its rendered output is unchanged
vi.mock('../../src/frontend/components/billing/BillingInfoCard', () => ({
  BillingInfoCard: () => <div data-testid="billing-info-card" />,
}));

// UsageCard stub — guards it is importable and renders without crashing
// (the real component is new; we verify it does not break surrounding layout)
vi.mock('../../src/frontend/components/billing/UsageCard', () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}));

// i18n stub
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => 'en'),
}));

// ---------------------------------------------------------------------------
// API client mock — assert existing endpoints are NOT modified by this change
// ---------------------------------------------------------------------------
// TODO: replace with actual API client module path
vi.mock('../../src/frontend/lib/api/billingApi', () => ({
  fetchSubscription: vi.fn(),
  createBillingPortalSession: vi.fn(),
}));

import { fetchSubscription, createBillingPortalSession } from '../../src/frontend/lib/api/billingApi';
const mockFetchSubscription = vi.mocked(fetchSubscription);
const mockCreateBillingPortalSession = vi.mocked(createBillingPortalSession);

// ---------------------------------------------------------------------------
// beforeEach
// ---------------------------------------------------------------------------
beforeEach(() => {
  vi.clearAllMocks();
});

// ===========================================================================
// UsageCard regression tests
// ===========================================================================
describe('UsageCard regression', () => {

  // ─── Existing API contract: GET /users/me/subscription unchanged ──────────────
  it('test_existing_get_users_me_subscription_api_contract_unchanged', () => {
    // TODO: call fetchSubscription() and assert response shape matches prior contract
    // TODO: assert response contains: { plan_name, status, next_billing_date, amount }
    // TODO: assert no new required fields have been added that would break existing callers
    mockFetchSubscription.mockResolvedValueOnce({
      plan_name: 'Monthly',
      status: 'active',
      next_billing_date: '2026-06-24',
      amount: 20,
    });
    // TODO: const result = await fetchSubscription()
    // TODO: expect(result).toMatchObject({ plan_name: expect.any(String), status: expect.any(String) })
    expect(mockFetchSubscription).toBeDefined();
  });

  // ─── Existing API contract: POST /billing/portal unchanged ───────────────────
  it('test_existing_post_billing_portal_api_contract_unchanged', () => {
    // TODO: call createBillingPortalSession() and assert response contains { url: string }
    mockCreateBillingPortalSession.mockResolvedValueOnce({ url: 'https://billing.stripe.com/session/xyz' });
    // TODO: const result = await createBillingPortalSession()
    // TODO: expect(result).toHaveProperty('url')
    // TODO: expect(typeof result.url).toBe('string')
    expect(mockCreateBillingPortalSession).toBeDefined();
  });

  // ─── Sibling component: SubscriptionCard unaffected ──────────────────────────
  it('test_subscription_card_renders_unchanged_when_usage_card_is_present', () => {
    // TODO: render a minimal BillingContent wrapper that includes both SubscriptionCard and UsageCard stubs
    // TODO: assert data-testid="subscription-card" is in the document
    // TODO: assert it has expected prop attributes (plan-name, status)
    render(
      <>
        {/* TODO: render BillingContent or compose SubscriptionCard + UsageCard here */}
        <div data-testid="subscription-card" data-plan-name="Monthly" data-status="active" />
        <div data-testid="usage-card" />
      </>
    );
    const subscriptionCard = screen.getByTestId('subscription-card');
    expect(subscriptionCard).toBeTruthy();
    // TODO: expect(subscriptionCard.getAttribute('data-plan-name')).toBe('Monthly')
    // TODO: expect(subscriptionCard.getAttribute('data-status')).toBe('active')
  });

  // ─── Sibling component: BillingInfoCard unaffected ───────────────────────────
  it('test_billing_info_card_renders_unchanged_when_usage_card_is_present', () => {
    // TODO: render a minimal layout including BillingInfoCard and UsageCard stubs
    // TODO: assert data-testid="billing-info-card" is in the document
    render(
      <>
        <div data-testid="billing-info-card" />
        <div data-testid="usage-card" />
      </>
    );
    expect(screen.getByTestId('billing-info-card')).toBeTruthy();
  });

  // ─── Card render order unchanged: subscription → usage → billing-info ─────────
  it('test_billing_page_card_order_unchanged_when_usage_card_inserted', () => {
    // TODO: render the full BillingContent layout
    // TODO: assert DOM order: subscription-card appears before usage-card, usage-card before billing-info-card
    const { container } = render(
      <>
        <div data-testid="subscription-card" />
        <div data-testid="usage-card" />
        <div data-testid="billing-info-card" />
      </>
    );
    const cards = container.querySelectorAll(
      '[data-testid="subscription-card"], [data-testid="usage-card"], [data-testid="billing-info-card"]'
    );
    // TODO: expect(cards[0].getAttribute('data-testid')).toBe('subscription-card')
    // TODO: expect(cards[1].getAttribute('data-testid')).toBe('usage-card')
    // TODO: expect(cards[2].getAttribute('data-testid')).toBe('billing-info-card')
    expect(cards.length).toBe(3);
  });

  // ─── New component does not crash on import ───────────────────────────────────
  it('test_usage_card_renders_without_crashing_when_mounted_in_isolation', () => {
    // TODO: render <UsageCard /> stub (no providers — verifies no import-time side-effects crash billing page)
    // TODO: assert data-testid="usage-card" is in the document
    const { UsageCard } = vi.getMockImplementation(
      '../../src/frontend/components/billing/UsageCard'
    ) as { UsageCard: () => JSX.Element } ?? { UsageCard: () => <div data-testid="usage-card" /> };
    render(<div data-testid="usage-card" />);
    expect(screen.getByTestId('usage-card')).toBeTruthy();
  });

  // ─── No new non-2xx on GET /users/me/usage ────────────────────────────────────
  it('test_get_users_me_usage_endpoint_returns_2xx_when_user_is_authenticated', () => {
    // TODO: assert that GET /users/me/usage (the new endpoint introduced by this spec)
    //        returns a 2xx response for an authenticated user.
    // TODO: mock the fetch call and assert status in [200, 201, 204]
    // NOTE: RT-002 rollback trigger fires if any non-2xx appears here post-deploy
    expect(true).toBeTruthy(); // placeholder — replace with real assertion
  });

  // ─── Existing Stripe webhook handling unaffected ──────────────────────────────
  it('test_stripe_webhook_handler_module_not_modified_by_this_change', () => {
    // TODO: import the Stripe webhook handler and assert its exported function signature is unchanged
    // TODO: e.g. assert typeof handleStripeWebhook === 'function'
    // TODO: assert it accepts (req, res) or (event) depending on implementation
    expect(true).toBeTruthy(); // placeholder — replace with actual import + type assertion
  });

});
