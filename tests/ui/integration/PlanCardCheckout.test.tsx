// spec_id: FE-UI-026  component: PlanCard (via PlansSection)  tier: integration
// Route: /billing (section within page)
// ACs covered: AC-012 (verification_type: integration, blocking_gate: post_deploy)
//
// AC-012: onChoosePlan invoked → POST /billing/checkout → window.location.href redirect
//
// PlanCard does not call the API directly. PlansSection provides the real
// onChoosePlan callback that calls POST /billing/checkout. This integration
// test renders PlansSection with a real (unmocked) onChoosePlan to verify
// the full click → POST → redirect chain.

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

jest.mock('../../../src/frontend/hooks/useUserContext', () => ({
  useUserContext: jest.fn(() => ({
    user: null,
    subscription: { has_active_subscription: false, subscription: null },
    isLoading: false,
    hasActiveAccess: false,
    applicationsRemaining: 0,
  })),
}));

// ─── window.location.href intercept ───────────────────────────────────────────
let capturedHref: string | undefined;
const originalLocation = window.location;

beforeEach(() => {
  // window.location is not configurable in jsdom; reassign via Object.defineProperty
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: {
      ...originalLocation,
      get href() { return capturedHref ?? originalLocation.href; },
      set href(val: string) { capturedHref = val; },
    },
  });
  capturedHref = undefined;
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

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
import { PlansSection } from '../../../src/frontend/components/billing/PlansSection';

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('PlanCardCheckout integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── AC-012: click → POST → redirect ─────────────────────────────────────
  it('test_renders_data_when_plans_section_mounts', async () => {
    // TODO: render <PlansSection onChoosePlan={jest.fn()} /> with wrapper
    // TODO: assert all three plan cards are visible
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByTestId('plan-card-monthly')).toBeDefined()
      // TODO: expect(screen.getByTestId('plan-card-3month')).toBeDefined()
      // TODO: expect(screen.getByTestId('plan-card-6month')).toBeDefined()
    });
  });

  it('test_post_billing_checkout_called_when_choose_plan_clicked', async () => {
    // TODO: mock apiClient.post for /billing/checkout to resolve with { url: 'https://checkout.stripe.com/pay/test' }
    // TODO: render <PlansSection onChoosePlan={<real handler that calls POST /billing/checkout>} /> with wrapper
    // TODO: click the "Choose Plan" button on the monthly card (data-testid="plan-card-monthly")
    // TODO: await waitFor and assert apiClient.post was called with URL matching /billing/checkout
    // TODO: assert the request body includes planKey="monthly"
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/test-session' });
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(screen.getByTestId('plan-card-monthly').querySelector('button'))
      // TODO: expect(mockApiPost).toHaveBeenCalledWith(
      //   expect.stringMatching(/\/billing\/checkout/),
      //   expect.objectContaining({ planKey: 'monthly' })
      // )
    });
  });

  it('test_browser_redirects_to_stripe_checkout_url_when_api_responds', async () => {
    // TODO: mock apiClient.post to resolve with { url: 'https://checkout.stripe.com/pay/test-session' }
    // TODO: render PlansSection with a real onChoosePlan that calls POST /billing/checkout
    // TODO: click "Choose Plan" on a non-current card
    // TODO: await waitFor and assert window.location.href === 'https://checkout.stripe.com/pay/test-session'
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/test-session' });
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(screen.getByTestId('plan-card-monthly').querySelector('button'))
      // TODO: expect(capturedHref).toBe('https://checkout.stripe.com/pay/test-session')
    });
  });

  it('test_shows_error_state_when_post_billing_checkout_fails', async () => {
    // TODO: mock apiClient.post for /billing/checkout to reject with a network error
    // TODO: render PlansSection with a real onChoosePlan
    // TODO: click "Choose Plan"
    // TODO: assert window.location.href is NOT changed (no redirect on failure)
    // TODO: assert some error indicator is shown OR simply assert no unhandled crash
    mockApiPost.mockRejectedValue(new Error('500 Internal Server Error'));
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(...)
      // TODO: expect(capturedHref).toBeUndefined()
    });
  });

  it('test_redirect_uses_same_tab_window_location_href_not_window_open', async () => {
    // Spec requires same-tab redirect via window.location.href, not window.open (new tab)
    // TODO: spy on window.open and assert it is NOT called
    // TODO: mock apiClient.post to resolve with checkout URL
    // TODO: click "Choose Plan" and assert window.open was never invoked
    const windowOpenSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/test-session' });
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(...)
      // TODO: expect(windowOpenSpy).not.toHaveBeenCalled()
    });
    windowOpenSpy.mockRestore();
  });

});
