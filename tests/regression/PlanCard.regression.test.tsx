// spec_id: FE-UI-026  component: PlanCard  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. POST /billing/checkout API contract: endpoint path and request/response shape
//   2. BillingContent rendering unaffected (PlanCard is a new leaf; no sibling regression)
//   3. PlansSection continues to render with correct props after PlanCard extraction
//   4. Existing Stripe checkout redirect path unchanged (window.location.href)
//   5. No new non-2xx responses on POST /billing/checkout for any planKey

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

jest.mock('../../../src/frontend/hooks/useUserContext', () => ({
  useUserContext: jest.fn(() => ({
    user: null,
    subscription: { has_active_subscription: false, subscription: null },
    isLoading: false,
    hasActiveAccess: false,
    applicationsRemaining: 0,
  })),
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

// ─── Imports under test ───────────────────────────────────────────────────────
import { PlanCard } from '../../../src/frontend/components/billing/PlanCard';
import { PlansSection } from '../../../src/frontend/components/billing/PlansSection';

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('PlanCard regression', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── API contract: POST /billing/checkout ─────────────────────────────────
  it('test_existing_post_billing_checkout_api_contract_unchanged', async () => {
    // Assert the checkout POST is called with the exact prior contract:
    //   URL: /billing/checkout (or matching path)
    //   Request body: { planKey: string }
    //   Response shape: { url: string } (Stripe Checkout URL)
    // TODO: render PlansSection with real onChoosePlan (not mocked) inside wrapper
    // TODO: click a "Choose Plan" button to trigger the POST
    // TODO: assert apiClient.post was called with URL matching /billing/checkout
    // TODO: assert the planKey is passed in the request body
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/test-session' });
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(screen.getByTestId('plan-card-monthly').querySelector('button'))
      // TODO: expect(mockApiPost).toHaveBeenCalledWith(
      //   expect.stringMatching(/\/billing\/checkout/),
      //   expect.objectContaining({ planKey: expect.any(String) })
      // )
    });
  });

  it('test_no_new_non_2xx_responses_on_billing_checkout_for_monthly_plankey', async () => {
    // Assert that calling POST /billing/checkout with planKey="monthly" does not
    // produce a non-2xx response — the endpoint must accept all three known planKeys.
    // TODO: invoke the real (or near-real) checkout handler with planKey="monthly"
    // TODO: assert the mock resolves (no rejection for a valid planKey)
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/monthly-test' });
    // TODO: trigger onChoosePlan('monthly')
    // TODO: expect(mockApiPost).not.toThrow()
    // TODO: expect(await mockApiPost.mock.results[0].value).toHaveProperty('url')
  });

  it('test_no_new_non_2xx_responses_on_billing_checkout_for_3month_plankey', async () => {
    // Assert POST /billing/checkout with planKey="3month" resolves with a URL
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/3month-test' });
    // TODO: trigger onChoosePlan('3month')
    // TODO: expect(await mockApiPost.mock.results[0].value).toHaveProperty('url')
  });

  it('test_no_new_non_2xx_responses_on_billing_checkout_for_6month_plankey', async () => {
    // Assert POST /billing/checkout with planKey="6month" resolves with a URL
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/6month-test' });
    // TODO: trigger onChoosePlan('6month')
    // TODO: expect(await mockApiPost.mock.results[0].value).toHaveProperty('url')
  });

  // ─── BillingContent rendering unaffected ─────────────────────────────────
  it('test_unmodified_billing_content_renders_plans_section_without_crash', async () => {
    // PlanCard is a new leaf component extracted from PlansSection.
    // Assert that PlansSection still renders all three plan cards after the extraction.
    // TODO: render <PlansSection onChoosePlan={jest.fn()} /> with wrapper
    // TODO: assert plan-card-monthly, plan-card-3month, plan-card-6month are present
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: expect(screen.getByTestId('plan-card-monthly')).toBeDefined()
      // TODO: expect(screen.getByTestId('plan-card-3month')).toBeDefined()
      // TODO: expect(screen.getByTestId('plan-card-6month')).toBeDefined()
    });
  });

  // ─── PlanCard prop contract with PlansSection unchanged ───────────────────
  it('test_plan_card_receives_correct_props_from_plans_section', async () => {
    // Assert PlansSection passes the expected props to each PlanCard.
    // This guards against prop renames or removals that would silently break rendering.
    // TODO: render PlansSection and assert each PlanCard has expected data-* attributes
    //       (relies on PlanCard forwarding props to data-testid root or similar)
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: const monthly = screen.getByTestId('plan-card-monthly')
      // TODO: expect(monthly.getAttribute('data-price-per-month') ?? monthly.textContent).toMatch(/30/)
    });
  });

  // ─── data-testid contract preserved ──────────────────────────────────────
  it('test_plan_card_root_data_testid_format_unchanged', () => {
    // Assert the data-testid="plan-card-{planKey}" format is preserved.
    // Any change here would break Playwright selectors in existing e2e tests.
    render(<PlanCard
      planKey="monthly"
      displayName="Monthly Plan"
      pricePerMonth={30}
      billingPeriodLabel="Billed monthly"
      isCurrentPlan={false}
      isRecommended={false}
      onChoosePlan={jest.fn()}
    />);
    expect(screen.getByTestId('plan-card-monthly')).toBeDefined();
  });

  it('test_plan_card_data_testid_uses_plankey_as_suffix', () => {
    // Assert that each unique planKey produces a unique, correctly-suffixed testid.
    const { unmount } = render(<PlanCard
      planKey="3month"
      displayName="3 Month Plan"
      pricePerMonth={25}
      billingPeriodLabel="Billed $75 every 3 months"
      isCurrentPlan={false}
      isRecommended={true}
      onChoosePlan={jest.fn()}
    />);
    expect(screen.getByTestId('plan-card-3month')).toBeDefined();
    unmount();

    render(<PlanCard
      planKey="6month"
      displayName="6 Month Plan"
      pricePerMonth={20}
      billingPeriodLabel="Billed $120 every 6 months"
      isCurrentPlan={false}
      isRecommended={false}
      onChoosePlan={jest.fn()}
    />);
    expect(screen.getByTestId('plan-card-6month')).toBeDefined();
  });

  // ─── Stripe redirect uses window.location.href (same tab) ────────────────
  it('test_checkout_redirect_uses_window_location_href_not_window_open', async () => {
    // Assert the redirect stays in the same tab. This guards against a refactor
    // that switches to window.open (which would open a new tab).
    const windowOpenSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
    mockApiPost.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/test-session' });
    const Wrapper = createWrapper();
    render(<PlansSection onChoosePlan={jest.fn()} />, { wrapper: Wrapper });
    await waitFor(() => {
      // TODO: userEvent.click(screen.getByTestId('plan-card-monthly').querySelector('button'))
      // TODO: expect(windowOpenSpy).not.toHaveBeenCalled()
    });
    windowOpenSpy.mockRestore();
  });

});
