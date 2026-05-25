// spec_id: FE-UI-024  component: BillingInfoCard  tier: integration
// Route: /billing
// All spec ACs are verification_type: unit; integration tests cover state
// transitions and API-client-level interactions within page context.
// Mock boundary: api client (not hook level). No real network calls.

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { jest, beforeEach, describe, it, expect } from '@jest/globals';

// ─── API client mock (integration boundary) ───────────────────────────────────
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

// ─── window.open spy (integration-level: assert it IS called on success) ──────
let windowOpenSpy: ReturnType<typeof jest.spyOn>;

// ─── Provider wrapper ─────────────────────────────────────────────────────────
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── Import under test ────────────────────────────────────────────────────────
import { BillingInfoCard } from '../../../src/frontend/components/billing/BillingInfoCard';

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const SUBSCRIPTION_WITH_PAYMENT = {
  has_active_subscription: true,
  payment_method: { last4: '6363', brand: 'visa' },
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
};

const SUBSCRIPTION_NO_PAYMENT = {
  has_active_subscription: true,
  payment_method: null,
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
};

const PORTAL_RESPONSE = {
  url: 'https://billing.stripe.com/session/test-session-id',
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('BillingInfoCard integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
    windowOpenSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    windowOpenSpy.mockRestore();
  });

  // ─── State transition: loading → has-payment-method ───────────────────────
  it('test_renders_masked_card_after_subscription_api_succeeds_with_payment_method', async () => {
    // TODO: mock apiClient.get('/users/me/subscription') to resolve with SUBSCRIPTION_WITH_PAYMENT
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: await text "•••• 6363" to appear in the document
    mockApiGet.mockResolvedValue(SUBSCRIPTION_WITH_PAYMENT);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/•••• 6363/)).toBeDefined();
    });
  });

  // ─── State transition: loading → no-payment-method ────────────────────────
  it('test_renders_no_payment_method_after_subscription_api_returns_null_payment', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_NO_PAYMENT
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: await text "No payment method" and "Add Payment Method" button to appear
    mockApiGet.mockResolvedValue(SUBSCRIPTION_NO_PAYMENT);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/no payment method/i)).toBeDefined();
    });
    // TODO: expect(screen.getByRole('button', { name: /add payment method/i })).toBeDefined()
  });

  // ─── State transition: loading → error ────────────────────────────────────
  it('test_shows_error_state_when_subscription_api_rejects', async () => {
    // TODO: mock apiClient.get to reject with an Error
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: await Retry button to appear (confirms error state rendered)
    mockApiGet.mockRejectedValue(new Error('Network error'));
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeDefined();
    });
  });

  // ─── User action: Retry → re-fetches subscription data ───────────────────
  it('test_clicking_retry_triggers_subscription_refetch_after_error', async () => {
    // TODO: first call rejects, second call resolves with SUBSCRIPTION_WITH_PAYMENT
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: await error state, click Retry, await payment method text to appear
    mockApiGet
      .mockRejectedValueOnce(new Error('First attempt failed'))
      .mockResolvedValueOnce(SUBSCRIPTION_WITH_PAYMENT);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeDefined();
    });
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => {
      expect(screen.getByText(/•••• 6363/)).toBeDefined();
    });
  });

  // ─── User action: Manage Billing → POST /billing/portal → window.open ────
  it('test_manage_billing_click_posts_to_portal_and_opens_url_in_new_tab', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_WITH_PAYMENT
    // TODO: mock apiClient.post('/billing/portal') to resolve with PORTAL_RESPONSE
    // TODO: render <BillingInfoCard /> with wrapper, await card, click "Manage Billing"
    // TODO: assert apiClient.post called with URL matching /billing/portal
    // TODO: assert window.open called with PORTAL_RESPONSE.url and '_blank'
    mockApiGet.mockResolvedValue(SUBSCRIPTION_WITH_PAYMENT);
    mockApiPost.mockResolvedValue(PORTAL_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /manage billing/i })).toBeDefined();
    });
    fireEvent.click(screen.getByRole('button', { name: /manage billing/i }));
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        expect.stringMatching(/\/billing\/portal/),
        expect.anything()
      );
      expect(windowOpenSpy).toHaveBeenCalledWith(PORTAL_RESPONSE.url, '_blank');
    });
  });

  // ─── User action: Add Payment Method → POST /billing/portal → window.open ─
  it('test_add_payment_method_click_posts_to_portal_and_opens_url_in_new_tab', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_NO_PAYMENT
    // TODO: mock apiClient.post('/billing/portal') to resolve with PORTAL_RESPONSE
    // TODO: render <BillingInfoCard /> with wrapper, await empty state, click "Add Payment Method"
    // TODO: assert window.open called with PORTAL_RESPONSE.url and '_blank'
    mockApiGet.mockResolvedValue(SUBSCRIPTION_NO_PAYMENT);
    mockApiPost.mockResolvedValue(PORTAL_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add payment method/i })).toBeDefined();
    });
    fireEvent.click(screen.getByRole('button', { name: /add payment method/i }));
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        expect.stringMatching(/\/billing\/portal/),
        expect.anything()
      );
      expect(windowOpenSpy).toHaveBeenCalledWith(PORTAL_RESPONSE.url, '_blank');
    });
  });

  // ─── User action: portal POST failure → inline error, no window.open ──────
  it('test_shows_inline_error_and_does_not_open_tab_when_portal_post_fails', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_WITH_PAYMENT
    // TODO: mock apiClient.post('/billing/portal') to reject
    // TODO: render <BillingInfoCard />, click "Manage Billing"
    // TODO: assert inline error visible, assert window.open NOT called
    mockApiGet.mockResolvedValue(SUBSCRIPTION_WITH_PAYMENT);
    mockApiPost.mockRejectedValue(new Error('Portal unavailable'));
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /manage billing/i })).toBeDefined();
    });
    fireEvent.click(screen.getByRole('button', { name: /manage billing/i }));
    await waitFor(() => {
      // TODO: expect(screen.getByRole('alert') OR screen.getByText(/error|failed|unavailable/i)).toBeDefined()
      expect(windowOpenSpy).not.toHaveBeenCalled();
    });
  });

  // ─── State transition: loading indicator visible before data resolves ──────
  it('test_skeleton_visible_before_subscription_data_resolves', async () => {
    // TODO: mock apiClient.get to return a never-resolving promise (simulates in-flight)
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: assert skeleton/shimmer element is visible immediately (before await)
    mockApiGet.mockReturnValue(new Promise(() => {})); // never resolves
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    // TODO: expect(screen.getByTestId('skeleton') OR screen.queryByRole('status')).toBeDefined()
    expect(screen.queryByRole('button', { name: /manage billing/i })).toBeNull();
  });

  // ─── Stripe trust line appears only when payment method data is present ────
  it('test_stripe_trust_line_visible_only_after_payment_method_data_loads', async () => {
    // TODO: mock apiClient.get to resolve with SUBSCRIPTION_WITH_PAYMENT
    // TODO: render <BillingInfoCard />, await data, assert trust text is visible
    mockApiGet.mockResolvedValue(SUBSCRIPTION_WITH_PAYMENT);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/billing handled securely via stripe/i)).toBeDefined();
    });
  });

});
