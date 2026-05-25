// spec_id: FE-UI-021  component: BillingContent  tier: integration
// Route: /billing
// All ACs are verification_type: unit; integration tests cover state transitions
// and API-client-level wiring that unit tests mock at hook level.

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';

// ─── Mocks ────────────────────────────────────────────────────────────────────
const mockPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: jest.fn() }),
  usePathname: jest.fn(() => '/billing'),
}));

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

// Mock at API client level (not hook level) per integration test rules
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

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const SUBSCRIPTION_RESPONSE = {
  has_active_subscription: true,
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
};

const USAGE_RESPONSE = {
  trial: { active: false, days_remaining: 0 },
  applications: { remaining: 5 },
};

const USER_RESPONSE = { id: 'user-1', email: 'test@example.com' };

// ─── Import under test ────────────────────────────────────────────────────────
import BillingContent from '../../../src/frontend/app/billing/page';

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('BillingContent integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── Loading → data rendered ──────────────────────────────────────────────
  it('test_renders_all_three_cards_when_all_api_calls_succeed', async () => {
    // TODO: mock apiClient.get to resolve for /users/me, /users/me/usage, /users/me/subscription
    // TODO: render <BillingContent /> with wrapper
    // TODO: await waitFor and assert subscription-card, usage-card, billing-info-card present
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/subscription')) return Promise.resolve(SUBSCRIPTION_RESPONSE);
      if (url.includes('/usage')) return Promise.resolve(USAGE_RESPONSE);
      return Promise.resolve(USER_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByTestId('subscription-card')).toBeTruthy();
      // TODO: expect(screen.getByTestId('usage-card')).toBeTruthy();
      // TODO: expect(screen.getByTestId('billing-info-card')).toBeTruthy();
    });
  });

  it('test_shows_spinner_while_api_calls_pending', async () => {
    // TODO: mock apiClient.get to return a never-resolving promise (simulate in-flight)
    // TODO: render <BillingContent /> with wrapper
    // TODO: assert spinner is present before data arrives
    mockApiGet.mockReturnValue(new Promise(() => {}));
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('spinner')).toBeTruthy();
  });

  it('test_transitions_from_loading_to_data_rendered_when_api_resolves', async () => {
    // TODO: mock apiClient.get to resolve after short delay
    // TODO: render with wrapper
    // TODO: assert spinner present initially, then absent after waitFor; assert cards present
    let resolveSubscription: (val: unknown) => void;
    const subscriptionPromise = new Promise((res) => { resolveSubscription = res; });
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/subscription')) return subscriptionPromise;
      if (url.includes('/usage')) return Promise.resolve(USAGE_RESPONSE);
      return Promise.resolve(USER_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('spinner')).toBeTruthy();
    // resolveSubscription!(SUBSCRIPTION_RESPONSE);
    // await waitFor(() => expect(screen.queryByTestId('spinner')).toBeNull());
    // TODO: expect(screen.getByTestId('subscription-card')).toBeTruthy();
  });

  // ─── API error → error state rendered ────────────────────────────────────
  it('test_shows_error_state_when_subscription_api_fails', async () => {
    // TODO: mock apiClient.get for /users/me/subscription to reject with 500
    // TODO: render with wrapper
    // TODO: assert ErrorBoundary fallback or error indicator is visible
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/subscription')) return Promise.reject(new Error('500 Internal Server Error'));
      if (url.includes('/usage')) return Promise.resolve(USAGE_RESPONSE);
      return Promise.resolve(USER_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: assert error UI is shown; exact assertion depends on ErrorBoundary implementation
    });
  });

  it('test_shows_error_state_when_usage_api_fails', async () => {
    // TODO: mock apiClient.get for /users/me/usage to reject
    // TODO: render with wrapper
    // TODO: assert error state renders
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/usage')) return Promise.reject(new Error('500 Internal Server Error'));
      if (url.includes('/subscription')) return Promise.resolve(SUBSCRIPTION_RESPONSE);
      return Promise.resolve(USER_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: assert error UI is shown
    });
  });

  // ─── User action → API call → UI update ──────────────────────────────────
  it('test_billing_portal_api_called_when_manage_billing_action_triggered', async () => {
    // TODO: mock apiClient.get for all three endpoints to resolve
    // TODO: mock apiClient.post for /billing/portal to resolve with { url: 'https://portal.example' }
    // TODO: render with wrapper; await data load
    // TODO: click "Manage Billing" / portal button in BillingInfoCard area
    // TODO: assert apiClient.post was called with /billing/portal
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/subscription')) return Promise.resolve(SUBSCRIPTION_RESPONSE);
      if (url.includes('/usage')) return Promise.resolve(USAGE_RESPONSE);
      return Promise.resolve(USER_RESPONSE);
    });
    mockApiPost.mockResolvedValue({ url: 'https://portal.example.com' });
    const Wrapper = createWrapper();
    render(<BillingContent />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(screen.getByRole('button', { name: /manage billing/i }));
      // TODO: expect(mockApiPost).toHaveBeenCalledWith('/billing/portal', expect.anything());
    });
  });

});
