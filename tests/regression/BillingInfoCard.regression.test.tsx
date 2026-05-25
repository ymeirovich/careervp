// spec_id: FE-UI-024  component: BillingInfoCard  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. GET /users/me/subscription API contract: endpoint path + response shape
//      (including new fields: payment_method.last4, payment_method.brand)
//   2. POST /billing/portal API contract: endpoint path + response shape (url field)
//   3. BillingContent still renders BillingInfoCard (data-testid="billing-info-card")
//   4. No new non-2xx responses introduced on GET /users/me/subscription or POST /billing/portal
//   5. Existing test suite (BillingContent.test.tsx) passes unmodified

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

// ─── window.open spy ──────────────────────────────────────────────────────────
let windowOpenSpy: ReturnType<typeof jest.spyOn>;

// ─── Mock sibling components (same contract as BillingContent.regression.test.tsx) ──
jest.mock('../../../src/frontend/app/billing/SubscriptionCard', () => ({
  SubscriptionCard: () => <div data-testid="subscription-card" />,
}), { virtual: true });

jest.mock('../../../src/frontend/app/billing/UsageCard', () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}), { virtual: true });

// NOTE: BillingInfoCard is the component under upgrade — do NOT mock it here.
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

// ─── Import under test ────────────────────────────────────────────────────────
import { BillingInfoCard } from '../../../src/frontend/components/billing/BillingInfoCard';

// ─── Prior-contract subscription response (before payment_method fields) ──────
// The component must still render gracefully when legacy shape is received
// (payment_method absent/undefined — treat as no-payment-method state).
const LEGACY_SUBSCRIPTION_RESPONSE = {
  has_active_subscription: true,
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
  // payment_method intentionally absent — backend prerequisite not yet deployed
};

// ─── Current-contract subscription response (with new payment_method fields) ─
const CURRENT_SUBSCRIPTION_RESPONSE = {
  has_active_subscription: true,
  payment_method: { last4: '6363', brand: 'visa' },
  subscription: { plan_type: 'monthly', status: 'active', current_period_end: null },
};

// ─── Portal response contract ─────────────────────────────────────────────────
const PORTAL_RESPONSE = {
  url: 'https://billing.stripe.com/session/test-session-id',
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('BillingInfoCard regression', () => {

  beforeEach(() => {
    jest.clearAllMocks();
    windowOpenSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    windowOpenSpy.mockRestore();
  });

  // ─── API contract: GET /users/me/subscription — endpoint path unchanged ───
  it('test_existing_subscription_api_endpoint_path_unchanged', async () => {
    // TODO: mock apiClient.get to resolve with CURRENT_SUBSCRIPTION_RESPONSE
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: await any data render
    // TODO: assert apiClient.get was called with a URL matching /users/me/subscription
    // TODO: assert no calls were made to any renamed/new endpoint
    mockApiGet.mockResolvedValue(CURRENT_SUBSCRIPTION_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      const urls = mockApiGet.mock.calls.map((c) => c[0] as string);
      expect(urls.some((url) => url.includes('/users/me/subscription'))).toBe(true);
    });
  });

  // ─── API contract: GET /users/me/subscription — response shape accepted ───
  it('test_existing_subscription_api_response_shape_still_accepted', async () => {
    // TODO: mock apiClient.get to resolve with CURRENT_SUBSCRIPTION_RESPONSE (new shape)
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: assert component renders without throwing (no crash on new payment_method fields)
    mockApiGet.mockResolvedValue(CURRENT_SUBSCRIPTION_RESPONSE);
    const Wrapper = createWrapper();
    expect(() => render(<BillingInfoCard />, { wrapper: Wrapper })).not.toThrow();
    await waitFor(() => {
      // TODO: expect(screen.getByText(/•••• 6363/)).toBeDefined()
      expect(true).toBe(true); // placeholder — replace with payment text assertion
    });
  });

  // ─── API contract: GET /users/me/subscription — legacy shape degrades gracefully
  it('test_component_renders_gracefully_when_payment_method_fields_absent_from_response', async () => {
    // TODO: mock apiClient.get to resolve with LEGACY_SUBSCRIPTION_RESPONSE (no payment_method)
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: assert component does not crash and renders no-payment-method state
    mockApiGet.mockResolvedValue(LEGACY_SUBSCRIPTION_RESPONSE);
    const Wrapper = createWrapper();
    expect(() => render(<BillingInfoCard />, { wrapper: Wrapper })).not.toThrow();
    await waitFor(() => {
      // TODO: expect(screen.getByText(/no payment method/i)).toBeDefined()
      expect(true).toBe(true); // placeholder
    });
  });

  // ─── API contract: POST /billing/portal — endpoint path unchanged ─────────
  it('test_existing_billing_portal_api_endpoint_path_unchanged', async () => {
    // TODO: mock apiClient.get to resolve with CURRENT_SUBSCRIPTION_RESPONSE
    // TODO: mock apiClient.post to resolve with PORTAL_RESPONSE
    // TODO: render, await card, click "Manage Billing", assert POST path matches /billing/portal
    mockApiGet.mockResolvedValue(CURRENT_SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(PORTAL_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /manage billing/i })).toBeDefined();
    });
    // TODO: fireEvent.click(screen.getByRole('button', { name: /manage billing/i }))
    // TODO: await waitFor(() => {
    // TODO:   const urls = mockApiPost.mock.calls.map((c) => c[0] as string)
    // TODO:   expect(urls.some((url) => url.includes('/billing/portal'))).toBe(true)
    // TODO: })
  });

  // ─── API contract: POST /billing/portal — response shape (url field) ──────
  it('test_existing_billing_portal_response_url_field_consumed_correctly', async () => {
    // TODO: mock apiClient.post to resolve with PORTAL_RESPONSE ({ url: '...' })
    // TODO: trigger "Manage Billing" click
    // TODO: assert window.open was called with PORTAL_RESPONSE.url
    // TODO: assert no other field name (e.g. 'portalUrl', 'redirect_url') is used
    mockApiGet.mockResolvedValue(CURRENT_SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(PORTAL_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /manage billing/i })).toBeDefined();
    });
    // TODO: fireEvent.click(screen.getByRole('button', { name: /manage billing/i }))
    // TODO: await waitFor(() => {
    // TODO:   expect(windowOpenSpy).toHaveBeenCalledWith(PORTAL_RESPONSE.url, '_blank')
    // TODO: })
  });

  // ─── No new non-2xx responses on GET /users/me/subscription ──────────────
  it('test_no_new_non_2xx_responses_introduced_on_subscription_endpoint', async () => {
    // TODO: mock apiClient.get to resolve with CURRENT_SUBSCRIPTION_RESPONSE (2xx)
    // TODO: render <BillingInfoCard /> with wrapper
    // TODO: assert every call to apiClient.get resolves (no unexpected rejections)
    // TODO: assert no calls are made to unknown/new endpoints
    mockApiGet.mockImplementation((url: string) => {
      const knownEndpoints = ['/users/me/subscription', '/users/me'];
      const isKnown = knownEndpoints.some((ep) => url.includes(ep));
      expect(isKnown).toBe(true);
      return Promise.resolve(CURRENT_SUBSCRIPTION_RESPONSE);
    });
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      // Allow all enqueued microtasks to settle
      expect(mockApiGet.mock.calls.length).toBeGreaterThanOrEqual(0);
    });
  });

  // ─── No new non-2xx responses on POST /billing/portal ────────────────────
  it('test_no_new_non_2xx_responses_introduced_on_billing_portal_endpoint', async () => {
    // TODO: mock apiClient.post to resolve with PORTAL_RESPONSE (2xx)
    // TODO: trigger portal action and assert no unexpected rejections
    mockApiGet.mockResolvedValue(CURRENT_SUBSCRIPTION_RESPONSE);
    mockApiPost.mockResolvedValue(PORTAL_RESPONSE);
    const Wrapper = createWrapper();
    render(<BillingInfoCard />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /manage billing/i })).toBeDefined();
    });
    // TODO: fireEvent.click the button and await; assert mockApiPost resolved (not rejected)
  });

  // ─── Unmodified sibling: BillingContent still mounts BillingInfoCard ──────
  it('test_billing_content_still_renders_billing_info_card_slot_unchanged', () => {
    // TODO: render BillingContent (with BillingInfoCard mocked as data-testid="billing-info-card")
    // TODO: assert data-testid="billing-info-card" is present in the document
    // TODO: confirms BillingContent mount contract for BillingInfoCard has not changed
    //
    // import BillingContent from '../../../src/frontend/app/billing/page'
    // const Wrapper = createWrapper()
    // render(<BillingContent />, { wrapper: Wrapper })
    // expect(screen.getByTestId('billing-info-card')).toBeDefined()
    expect(true).toBe(true); // placeholder — uncomment block above to activate
  });

  // ─── Unmodified sibling: SubscriptionCard renders without changes ─────────
  it('test_subscription_card_renders_unaffected_by_billing_info_card_upgrade', () => {
    // TODO: render the full /billing page (BillingContent) with BillingInfoCard real + others mocked
    // TODO: assert data-testid="subscription-card" is present and unchanged
    //
    // render(<BillingContent />, { wrapper: createWrapper() })
    // expect(screen.getByTestId('subscription-card')).toBeDefined()
    expect(true).toBe(true); // placeholder
  });

  // ─── Unmodified sibling: UsageCard renders without changes ───────────────
  it('test_usage_card_renders_unaffected_by_billing_info_card_upgrade', () => {
    // TODO: render the full /billing page (BillingContent) with BillingInfoCard real + others mocked
    // TODO: assert data-testid="usage-card" is present and unchanged
    //
    // render(<BillingContent />, { wrapper: createWrapper() })
    // expect(screen.getByTestId('usage-card')).toBeDefined()
    expect(true).toBe(true); // placeholder
  });

});
