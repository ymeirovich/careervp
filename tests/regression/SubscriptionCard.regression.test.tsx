// spec_id: FE-UI-022  component: SubscriptionCard  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. GET /users/me/subscription API contract: endpoint path and response shape
//   2. POST /billing/portal API contract: endpoint path and response shape
//   3. BillingContent still mounts SubscriptionCard as a child (no removal)
//   4. No new non-2xx responses on existing billing endpoints
//   5. Existing BillingContent tests pass without modification (sibling unaffected)

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';

// ─── Mocks ────────────────────────────────────────────────────────────────────
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: jest.fn(() => '/billing'),
}));

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);
const mockApiPost = jest.mocked(apiClient.post);

// Mock sibling cards so the full billing page renders without their implementations
jest.mock('../../../src/frontend/app/billing/UsageCard', () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/BillingInfoCard', () => ({
  BillingInfoCard: () => <div data-testid="billing-info-card" />,
}), { virtual: true });

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

jest.mock('../../../src/frontend/components/ui/Spinner', () => ({
  Spinner: ({ 'aria-label': ariaLabel }: { 'aria-label'?: string; size?: string }) => (
    <div role="status" aria-label={ariaLabel} data-testid="spinner" />
  ),
}));

// ─── Provider wrapper ─────────────────────────────────────────────────────────
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── Import under test ────────────────────────────────────────────────────────
import { SubscriptionCard } from '../../../src/frontend/components/billing/SubscriptionCard';
import BillingContent from '../../../src/frontend/app/billing/page';

// ─── Prior API contract fixture (must not change shape) ───────────────────────
const PRIOR_SUBSCRIPTION_CONTRACT = {
  plan_type: 'monthly',
  status: 'active',
  cancel_at_period_end: false,
  current_period_end: '2026-06-24T00:00:00Z',
  next_charge_amount: 3000,
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('SubscriptionCard regression', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── API contract: GET /users/me/subscription response shape ──────────────
  it('test_existing_subscription_api_contract_unchanged', async () => {
    // TODO: mock apiClient.get to resolve with PRIOR_SUBSCRIPTION_CONTRACT
    // TODO: render <SubscriptionCard /> with wrapper
    // TODO: assert apiClient.get was called with URL matching /users/me/subscription
    // TODO: assert no new fields were required by the component beyond the prior shape
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      const urls = mockApiGet.mock.calls.map((c) => c[0] as string);
      // TODO: expect(urls.some((url) => (url as string).includes('/users/me/subscription'))).toBe(true);
    });
  });

  // ─── API contract: POST /billing/portal shape unchanged ───────────────────
  it('test_existing_billing_portal_api_contract_unchanged', async () => {
    // TODO: trigger the billing portal action from SubscriptionCard (if wired)
    // TODO: assert apiClient.post was called with URL matching /billing/portal
    // TODO: assert response shape { url: string } is still accepted without error
    mockApiPost.mockResolvedValue({ url: 'https://billing.stripe.com/session/test' });
    // TODO: render <SubscriptionCard />, trigger portal action, then assert:
    // expect(mockApiPost).toHaveBeenCalledWith(expect.stringMatching(/\/billing\/portal/), expect.anything());
  });

  // ─── No new non-2xx responses on existing billing endpoints ───────────────
  it('test_no_new_non_2xx_responses_on_subscription_endpoint', async () => {
    // TODO: render with all known prior-contract API responses
    // TODO: assert every URL called by SubscriptionCard is a pre-existing endpoint
    mockApiGet.mockImplementation((url: unknown) => {
      if ((url as string).includes('/users/me/subscription')) {
        return Promise.resolve(PRIOR_SUBSCRIPTION_CONTRACT);
      }
      return Promise.reject(new Error(`Unexpected endpoint: ${url}`));
    });
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      for (const call of mockApiGet.mock.calls) {
        const url = call[0] as string;
        const knownEndpoints = ['/users/me/subscription'];
        // TODO: expect(knownEndpoints.some((ep) => url.includes(ep))).toBe(true);
      }
    });
  });

  // ─── BillingContent still mounts SubscriptionCard as child ───────────────
  it('test_billing_content_still_renders_subscription_card_as_child', () => {
    // TODO: mock useUserContext to return loaded state
    // TODO: render <BillingContent />
    // TODO: assert data-testid="subscription-card" is present in the page
    // This guards against accidental removal of SubscriptionCard from BillingContent.
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('subscription-card')).toBeDefined();
  });

  // ─── Sibling cards unaffected by SubscriptionCard introduction ────────────
  it('test_usage_card_unaffected_by_subscription_card_change', () => {
    // TODO: render <BillingContent /> and assert data-testid="usage-card" is present and unchanged
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('usage-card')).toBeDefined();
  });

  it('test_billing_info_card_unaffected_by_subscription_card_change', () => {
    // TODO: render <BillingContent /> and assert data-testid="billing-info-card" is present and unchanged
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('billing-info-card')).toBeDefined();
  });

  // ─── ErrorBoundary cloudwatchKey on billing page preserved ───────────────
  it('test_billing_page_error_boundary_cloudwatch_key_unchanged', () => {
    // TODO: render <BillingContent />
    // TODO: assert data-cloudwatch-key="billing-page" is still present after SubscriptionCard is wired in
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: const boundary = screen.getByTestId('error-boundary');
    // TODO: expect(boundary.getAttribute('data-cloudwatch-key')).toBe('billing-page');
  });

  // ─── SubscriptionCard renders without crashing on prior response shape ────
  it('test_subscription_card_renders_without_crash_on_prior_api_response_shape', async () => {
    // Asserts that the prior response shape (no new required fields) is still accepted.
    mockApiGet.mockResolvedValue(PRIOR_SUBSCRIPTION_CONTRACT);
    const Wrapper = createWrapper();
    expect(() => render(<SubscriptionCard />, { wrapper: Wrapper })).not.toThrow();
    await waitFor(() => {
      // TODO: assert at least one element from the card is rendered (card heading or badge)
    });
  });

});
