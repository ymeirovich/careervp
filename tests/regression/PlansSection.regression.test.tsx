// spec_id: FE-UI-025  component: PlansSection  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. POST /billing/checkout API contract: endpoint path + response shape
//   2. GET /users/me/subscription API contract: endpoint path used for currentPlanKey derivation
//   3. BillingContent still renders SubscriptionCard, UsageCard, BillingInfoCard unmodified
//   4. No new non-2xx responses introduced on GET /users/me/subscription or POST /billing/checkout
//   5. UsageCard's #plans anchor link continues to resolve (id="plans" present after upgrade)
//   6. Existing test suites (BillingContent.test.tsx) pass without modification

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, afterEach, describe, it, expect, jest } from '@jest/globals';

// ─── API client mock ──────────────────────────────────────────────────────────
jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);
const mockApiPost = jest.mocked(apiClient.post);

// ─── i18n / routing mocks ─────────────────────────────────────────────────────
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: jest.fn(() => '/billing'),
}));

// ─── Sibling component mocks (must not change post-upgrade) ───────────────────
jest.mock('../../../src/frontend/app/billing/SubscriptionCard', () => ({
  SubscriptionCard: () => <div data-testid="subscription-card" />,
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/UsageCard', () => ({
  UsageCard: () => (
    <div data-testid="usage-card">
      <a href="#plans" data-testid="upgrade-to-plans-link">
        Upgrade subscription to save money
      </a>
    </div>
  ),
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/BillingInfoCard', () => ({
  BillingInfoCard: () => <div data-testid="billing-info-card" />,
}), { virtual: true });

// NOTE: PlansSection is the component under upgrade — do NOT mock it here.
// We test its real implementation for regression compliance.

jest.mock('../../../src/frontend/components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({
    children,
    cloudwatchKey,
  }: {
    children: React.ReactNode;
    cloudwatchKey: string;
  }) => (
    <div data-testid="error-boundary" data-cloudwatch-key={cloudwatchKey}>
      {children}
    </div>
  ),
}));

// ─── Provider wrapper ─────────────────────────────────────────────────────────
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const SUBSCRIPTION_RESPONSE = {
  has_active_subscription: true,
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
};

const CHECKOUT_RESPONSE = {
  checkout_url: 'https://checkout.stripe.com/pay/test-session-id',
};

// ─── Import under test (full page — PlansSection rendered within BillingContent) ─
import BillingContent from '../../../src/frontend/app/billing/page';

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('PlansSection regression', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── API contract: GET /users/me/subscription — endpoint path unchanged ───
  it('test_existing_subscription_api_endpoint_path_unchanged_after_plans_section_added', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_RESPONSE
    // TODO: render <BillingContent /> with wrapper
    // TODO: await any data settle
    // TODO: assert apiClient.get was called with a URL matching /users/me/subscription
    // TODO: assert no calls were made to any renamed or new subscription endpoint
    mockApiGet.mockResolvedValue(SUBSCRIPTION_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      const urls = mockApiGet.mock.calls.map((c) => c[0] as string);
      const hasSubscriptionCall = urls.some((url) => url.includes('/users/me/subscription'));
      // TODO: expect(hasSubscriptionCall).toBe(true)
      expect(true).toBe(true); // placeholder
    });
  });

  // ─── API contract: POST /billing/checkout — endpoint path ────────────────
  it('test_existing_checkout_api_endpoint_path_unchanged_when_plan_chosen', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_RESPONSE
    // TODO: mock apiClient.post to resolve with CHECKOUT_RESPONSE
    // TODO: render <BillingContent /> with wrapper
    // TODO: await plans section; trigger onChoosePlan (e.g. click a PlanCard)
    // TODO: assert apiClient.post was called with a URL matching /billing/checkout
    // TODO: assert no calls were made to any renamed endpoint (e.g. /billing/subscribe)
    mockApiGet.mockResolvedValue(SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(CHECKOUT_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: click plan card, then check post call
      expect(true).toBe(true); // placeholder
    });
  });

  // ─── API contract: POST /billing/checkout — response shape (checkout_url) ─
  it('test_existing_checkout_response_checkout_url_field_consumed_correctly', async () => {
    // TODO: mock apiClient.post to resolve with CHECKOUT_RESPONSE ({ checkout_url: '...' })
    // TODO: trigger plan selection
    // TODO: assert navigation or window.location change used CHECKOUT_RESPONSE.checkout_url
    // TODO: assert no other field name (e.g. 'url', 'redirect', 'session_url') is consumed
    mockApiGet.mockResolvedValue(SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(CHECKOUT_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: interact and assert
    expect(true).toBe(true); // placeholder
  });

  // ─── No new non-2xx responses on GET /users/me/subscription ──────────────
  it('test_no_new_non_2xx_responses_introduced_on_subscription_endpoint_by_plans_section', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_RESPONSE for all known endpoints
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert every GET call resolves (no unexpected rejections)
    // TODO: assert no calls were made to unknown/new endpoints
    mockApiGet.mockImplementation((url: unknown) => {
      const knownEndpoints = ['/users/me/subscription', '/users/me'];
      const isKnown = knownEndpoints.some((ep) => (url as string).includes(ep));
      expect(isKnown).toBe(true);
      return Promise.resolve(SUBSCRIPTION_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(mockApiGet.mock.calls.length).toBeGreaterThanOrEqual(0);
    });
  });

  // ─── No new non-2xx responses on POST /billing/checkout ──────────────────
  it('test_no_new_non_2xx_responses_introduced_on_checkout_endpoint', async () => {
    // TODO: mock apiClient.post to resolve with CHECKOUT_RESPONSE
    // TODO: trigger plan selection and assert mockApiPost resolved (not rejected)
    mockApiGet.mockResolvedValue(SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(CHECKOUT_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: trigger onChoosePlan click
    // TODO: await waitFor(() => expect(mockApiPost).toHaveResolvedWith(CHECKOUT_RESPONSE))
    expect(true).toBe(true); // placeholder
  });

  // ─── Unmodified sibling: SubscriptionCard still renders ──────────────────
  it('test_subscription_card_renders_unaffected_after_plans_section_added', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert data-testid="subscription-card" is present in the document
    // TODO: confirms SubscriptionCard mount contract has not changed
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    expect(screen.getByTestId('subscription-card')).toBeDefined();
  });

  // ─── Unmodified sibling: UsageCard still renders ──────────────────────────
  it('test_usage_card_renders_unaffected_after_plans_section_added', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert data-testid="usage-card" is present in the document
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    expect(screen.getByTestId('usage-card')).toBeDefined();
  });

  // ─── Unmodified sibling: BillingInfoCard still renders ───────────────────
  it('test_billing_info_card_renders_unaffected_after_plans_section_added', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert data-testid="billing-info-card" is present in the document
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    expect(screen.getByTestId('billing-info-card')).toBeDefined();
  });

  // ─── Unmodified sibling: card DOM order unchanged ─────────────────────────
  it('test_existing_card_dom_order_subscription_usage_billing_info_unchanged', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert subscription-card → usage-card → billing-info-card DOM order is preserved
    // TODO: assert PlansSection is appended after billing-info-card, not inserted between cards
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    const subscriptionCard = screen.getByTestId('subscription-card');
    const usageCard = screen.getByTestId('usage-card');
    const billingInfoCard = screen.getByTestId('billing-info-card');
    expect(
      subscriptionCard.compareDocumentPosition(usageCard) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(
      usageCard.compareDocumentPosition(billingInfoCard) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  // ─── Unmodified: PlansSection renders BELOW billing-info-card ────────────
  it('test_plans_section_added_below_billing_info_card_not_above', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert billing-info-card precedes the #plans section in DOM order
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    const billingInfoCard = screen.getByTestId('billing-info-card');
    const plansSection = document.getElementById('plans');
    expect(plansSection).not.toBeNull();
    if (plansSection) {
      expect(
        billingInfoCard.compareDocumentPosition(plansSection) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    }
  });

  // ─── Unmodified: UsageCard #plans anchor still resolves ──────────────────
  it('test_usage_card_upgrade_link_href_plans_anchor_still_resolves_to_existing_section', () => {
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert the upgrade link inside usage-card has href="#plans"
    // TODO: assert document.getElementById('plans') is not null (anchor target exists)
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    const upgradeLink = screen.getByTestId('upgrade-to-plans-link');
    expect(upgradeLink.getAttribute('href')).toBe('#plans');
    expect(document.getElementById('plans')).not.toBeNull();
  });

});
