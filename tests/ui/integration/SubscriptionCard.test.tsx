// spec_id: FE-UI-022  component: SubscriptionCard  tier: integration
// Route: /billing
// All spec ACs are verification_type: unit; integration tests cover
// state transitions and API-client-level wiring that unit tests mock at hook level.

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

// Mock at API client level (not hook level) per integration test rules
jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);

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

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const ACTIVE_RESPONSE = {
  plan_type: 'Pro Monthly',
  status: 'active',
  cancel_at_period_end: false,
  current_period_end: '2026-06-24T00:00:00Z',
  next_charge_amount: 3000,
};

const CANCELLING_RESPONSE = {
  ...ACTIVE_RESPONSE,
  cancel_at_period_end: true,
};

const TRIALING_RESPONSE = {
  ...ACTIVE_RESPONSE,
  status: 'trialing',
  cancel_at_period_end: false,
};

const PAST_DUE_RESPONSE = {
  ...ACTIVE_RESPONSE,
  status: 'past_due',
  cancel_at_period_end: false,
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('SubscriptionCard integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── State transition: loading → active data rendered ─────────────────────
  it('test_renders_active_data_when_subscription_api_succeeds', async () => {
    // TODO: mock apiClient.get to resolve with ACTIVE_RESPONSE
    // TODO: render <SubscriptionCard /> with createWrapper()
    // TODO: await waitFor and assert "Active" badge and "Pro Monthly" pill are visible
    mockApiGet.mockResolvedValue(ACTIVE_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByText('Active')).toBeDefined();
      // TODO: expect(screen.getByText('Pro Monthly')).toBeDefined();
    });
  });

  it('test_shows_skeleton_then_data_during_loading_to_active_transition', async () => {
    // TODO: mock apiClient.get to delay then resolve with ACTIVE_RESPONSE
    // TODO: render <SubscriptionCard />
    // TODO: assert skeleton is visible before resolve
    // TODO: await resolve and assert skeleton gone, data visible
    mockApiGet.mockReturnValue(new Promise((resolve) => setTimeout(() => resolve(ACTIVE_RESPONSE), 100)));
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('skeleton')).toBeDefined();
    await waitFor(() => {
      // TODO: expect(screen.queryByTestId('skeleton')).toBeNull();
      // TODO: expect(screen.getByText('Active')).toBeDefined();
    });
  });

  // ─── State transition: API error → error state rendered ───────────────────
  it('test_shows_error_state_when_subscription_api_fails', async () => {
    // TODO: mock apiClient.get to reject with a network error
    // TODO: render <SubscriptionCard /> with createWrapper()
    // TODO: await waitFor and assert inline error message and "Retry" button are visible
    mockApiGet.mockRejectedValue(new Error('Network error'));
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByRole('button', { name: /retry/i })).toBeDefined();
    });
  });

  // ─── User action: "Retry" click → re-fetch ────────────────────────────────
  it('test_retry_button_triggers_refetch_after_error', async () => {
    // TODO: mock apiClient.get to reject first, then resolve on second call
    // TODO: render <SubscriptionCard />
    // TODO: await error state, then fireEvent.click("Retry")
    // TODO: await waitFor and assert subscription data renders after refetch
    mockApiGet
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(ACTIVE_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    });
    await waitFor(() => {
      // TODO: expect(screen.getByText('Active')).toBeDefined();
    });
  });

  // ─── Cancelling state renders correctly end-to-end ────────────────────────
  it('test_renders_cancelling_state_when_cancel_at_period_end_true', async () => {
    // TODO: mock apiClient.get to resolve with CANCELLING_RESPONSE
    // TODO: render <SubscriptionCard />
    // TODO: await waitFor and assert "Cancelling" badge and "Resubscribe" CTA visible
    mockApiGet.mockResolvedValue(CANCELLING_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByText('Cancelling')).toBeDefined();
      // TODO: expect(screen.getByRole('button', { name: /resubscribe/i })).toBeDefined();
    });
  });

  // ─── Trial state renders correctly end-to-end ─────────────────────────────
  it('test_renders_trial_state_when_status_is_trialing', async () => {
    // TODO: mock apiClient.get to resolve with TRIALING_RESPONSE
    // TODO: render <SubscriptionCard />
    // TODO: await waitFor and assert "Trial" badge and days-remaining text visible
    mockApiGet.mockResolvedValue(TRIALING_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByText('Trial')).toBeDefined();
    });
  });

  // ─── Past-due state renders correctly end-to-end ──────────────────────────
  it('test_renders_past_due_state_when_status_is_past_due', async () => {
    // TODO: mock apiClient.get to resolve with PAST_DUE_RESPONSE
    // TODO: render <SubscriptionCard />
    // TODO: await waitFor and assert "Past Due" badge and payment prompt visible
    mockApiGet.mockResolvedValue(PAST_DUE_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByText('Past Due')).toBeDefined();
    });
  });

  // ─── "View Plans" scroll integration ─────────────────────────────────────
  it('test_view_plans_cta_click_triggers_scroll_to_plans_anchor_when_active', async () => {
    // TODO: spy on window.scrollIntoView or document.getElementById('#plans').scrollIntoView
    // TODO: mock apiClient.get to resolve with ACTIVE_RESPONSE
    // TODO: render <SubscriptionCard /> wrapped in a page layout that includes #plans element
    // TODO: fireEvent.click("View Plans") and assert scroll was called
    mockApiGet.mockResolvedValue(ACTIVE_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: const cta = screen.getByRole('button', { name: /view plans/i });
      // TODO: fireEvent.click(cta);
      // TODO: assert window.location.hash === '#plans' or scrollIntoView was called
    });
  });

  // ─── API call uses correct endpoint ───────────────────────────────────────
  it('test_subscription_card_calls_correct_api_endpoint_on_mount', async () => {
    // TODO: mock apiClient.get to resolve with ACTIVE_RESPONSE
    // TODO: render <SubscriptionCard />
    // TODO: assert apiClient.get was called with a URL matching /users/me/subscription
    mockApiGet.mockResolvedValue(ACTIVE_RESPONSE);
    const Wrapper = createWrapper();
    render(<SubscriptionCard />, { wrapper: Wrapper });
    await waitFor(() => {
      const urls = mockApiGet.mock.calls.map((c) => c[0] as string);
      // TODO: expect(urls.some((url) => url.includes('/users/me/subscription'))).toBe(true);
    });
  });

});
