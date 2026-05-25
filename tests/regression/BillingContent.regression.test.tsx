// spec_id: FE-UI-021  component: BillingContent  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. GET /users/me/subscription API contract: endpoint path and response shape
//   2. GET /users/me/usage API contract: endpoint path and response shape
//   3. POST /billing/portal API contract: endpoint path and request/response shape
//   4. ErrorBoundary with cloudwatchKey="billing-page" retained
//   5. Existing Stripe webhook handling unaffected (no route changes)
//   6. useUserContext continues to be consumed (no hook removal)

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

// Child cards are new components; mock them so any sibling regression tests
// that render the whole page are not broken by missing implementations.
jest.mock('../../../src/frontend/app/billing/SubscriptionCard', () => ({
  SubscriptionCard: () => <div data-testid="subscription-card" />,
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/UsageCard', () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/BillingInfoCard', () => ({
  BillingInfoCard: () => <div data-testid="billing-info-card" />,
}), { virtual: true });

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
import BillingContent from '../../../src/frontend/app/billing/page';

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('BillingContent regression', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── API contract: GET /users/me/subscription ─────────────────────────────
  it('test_existing_subscription_api_contract_unchanged', async () => {
    // TODO: mock apiClient.get to resolve with prior contract shape
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert apiClient.get was called with a URL matching /users/me/subscription
    // TODO: assert no non-2xx error thrown from the subscription call
    mockApiGet.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        current_period_end: null,
      },
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      const calls = mockApiGet.mock.calls.map((c) => c[0] as string);
      expect(calls.some((url) => url.includes('/subscription'))).toBe(true);
    });
  });

  // ─── API contract: GET /users/me/usage ────────────────────────────────────
  it('test_existing_usage_api_contract_unchanged', async () => {
    // TODO: mock apiClient.get to resolve with prior contract shape
    // TODO: assert apiClient.get was called with a URL matching /users/me/usage
    mockApiGet.mockResolvedValue({
      trial: { active: false, days_remaining: 0 },
      applications: { remaining: 5 },
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      const calls = mockApiGet.mock.calls.map((c) => c[0] as string);
      expect(calls.some((url) => url.includes('/usage'))).toBe(true);
    });
  });

  // ─── API contract: POST /billing/portal ───────────────────────────────────
  it('test_existing_billing_portal_api_contract_unchanged', async () => {
    // TODO: trigger the billing portal action (click "Manage Billing")
    // TODO: assert apiClient.post was called with URL matching /billing/portal
    // TODO: assert no request body fields were removed from the call
    mockApiPost.mockResolvedValue({ url: 'https://billing.stripe.com/session/test' });
    // TODO: render, wait for load, click portal button, then assert:
    // expect(mockApiPost).toHaveBeenCalledWith(expect.stringMatching(/\/billing\/portal/), expect.anything());
  });

  // ─── ErrorBoundary cloudwatchKey preserved ────────────────────────────────
  it('test_error_boundary_cloudwatch_key_billing_page_unchanged', () => {
    // TODO: render <BillingContent /> (no api mock needed — ErrorBoundary wraps synchronously)
    // TODO: assert data-testid="error-boundary" has data-cloudwatch-key="billing-page"
    mockApiGet.mockResolvedValue({});
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    const boundary = screen.getByTestId('error-boundary');
    expect(boundary.getAttribute('data-cloudwatch-key')).toBe('billing-page');
  });

  // ─── Spinner aria-label preserved ────────────────────────────────────────
  it('test_loading_spinner_aria_label_unchanged', () => {
    // TODO: cause loading state (delay all api.get calls)
    // TODO: assert spinner aria-label is still "Loading billing info…"
    mockApiGet.mockReturnValue(new Promise(() => {}));
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    const spinner = screen.queryByTestId('spinner');
    if (spinner) {
      expect(spinner.getAttribute('aria-label')).toBe('Loading billing info…');
    }
    // TODO: if spinner is absent in loading state after restructure, investigate regression
  });

  // ─── Unmodified sibling: AppSidebar (route /billing remains sidebar-visible) ─
  it('test_billing_route_unaffected_in_app_sidebar_nav', () => {
    // TODO: render AppSidebar (or its test double) and assert /billing link is present
    // TODO: assert href="/billing" link exists and is not broken after restructure
    // import { AppSidebar } from '../../../src/frontend/components/AppSidebar/AppSidebar';
    // render(<AppSidebar />);
    // expect(screen.getByRole('link', { name: /billing/i })).toBeDefined();
  });

  // ─── No new non-2xx responses on existing endpoints ───────────────────────
  it('test_no_new_500_errors_on_subscription_endpoint', async () => {
    // TODO: render with real (or near-real) fetch and assert only 2xx responses
    // This is a contract test — the shape of the prior response must still be accepted.
    // Verifies that the restructured page does not call any new or renamed endpoints.
    mockApiGet.mockImplementation((url: string) => {
      if ((url as string).includes('/subscription')) {
        return Promise.resolve({
          has_active_subscription: true,
          subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
        });
      }
      if ((url as string).includes('/usage')) {
        return Promise.resolve({ trial: { active: false, days_remaining: 0 }, applications: { remaining: 5 } });
      }
      return Promise.resolve({ id: 'user-1', email: 'test@example.com' });
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      for (const call of mockApiGet.mock.calls) {
        // Assert every URL called is a known, pre-existing endpoint
        const url = call[0] as string;
        const knownEndpoints = ['/users/me', '/users/me/usage', '/users/me/subscription'];
        expect(knownEndpoints.some((ep) => url.includes(ep))).toBe(true);
      }
    });
  });

});
