import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiClientGetMock, apiClientPostMock } = vi.hoisted(() => ({
  apiClientGetMock: vi.fn(),
  apiClientPostMock: vi.fn(),
}));

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => apiClientGetMock(...args),
    post: (...args: unknown[]) => apiClientPostMock(...args),
  },
  apiFetchOrNull: async <T,>(fn: () => Promise<T>): Promise<T | null> => fn(),
}));

import BillingPage from '../../../app/billing/page';

const userResponse = {
  data: {
    id: 'user-1',
    user_id: 'user-1',
    email: 'user@example.com',
    name: 'User',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  },
};

const usageResponse = {
  data: {
    trial: {
      active: false,
      days_elapsed: 0,
      days_remaining: 0,
      ends_at: '2026-06-01T00:00:00Z',
    },
    applications: { used: 4, remaining: 16 },
  },
};

const subscriptionResponse = {
  data: {
    has_active_subscription: true,
    subscription: {
      plan_type: 'monthly',
      status: 'active',
      current_period_end: '2026-06-30T00:00:00Z',
      next_charge_amount: 30,
      payment_method: { last4: '4242', brand: 'visa' },
    },
  },
};

function mockBillingApis(): void {
  apiClientGetMock.mockImplementation((url: string) => {
    if (url === '/users/me') return Promise.resolve(userResponse);
    if (url === '/users/me/usage') return Promise.resolve(usageResponse);
    if (url === '/users/me/subscription') return Promise.resolve(subscriptionResponse);
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });

  apiClientPostMock.mockImplementation((url: string) => {
    if (url === '/billing/checkout') return Promise.resolve({ data: { checkout_url: '' } });
    if (url === '/billing/portal') return Promise.resolve({ data: { portal_url: 'https://billing.example.test/session' } });
    return Promise.reject(new Error(`Unexpected POST ${url}`));
  });
}

function renderBillingPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BillingPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  document.documentElement.lang = 'en';
  Element.prototype.scrollIntoView = vi.fn();
  vi.spyOn(window, 'open').mockImplementation(() => null);
  mockBillingApis();
});

afterEach(() => {
  vi.restoreAllMocks();
  apiClientGetMock.mockReset();
  apiClientPostMock.mockReset();
  document.documentElement.lang = 'en';
});

describe('FE-UI-021 — BillingContent', () => {
  it('renders the Billing page as three stacked cards followed by the Plans section', async () => {
    renderBillingPage();

    const page = await screen.findByTestId('billing-page');
    expect(within(page).getByRole('heading', { level: 1, name: 'Billing' })).toBeInTheDocument();
    expect(screen.queryByText('Billing & Plan')).not.toBeInTheDocument();

    const overviewCards = screen.getByTestId('billing-overview-cards');
    expect(Array.from(overviewCards.children).map((child) => child.getAttribute('data-testid'))).toEqual([
      'subscription-card',
      'usage-card',
      'billing-info-card',
    ]);

    const plansSection = screen.getByTestId('plans-section');
    expect(plansSection).toHaveAttribute('id', 'plans');
    expect(overviewCards.compareDocumentPosition(plansSection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(plansSection).getByRole('heading', { level: 2, name: 'Choose Your Plan' })).toBeInTheDocument();
    expect(within(plansSection).getByText('$30')).toBeInTheDocument();
    expect(within(plansSection).getByText('Billed $75 every 3 months')).toBeInTheDocument();
    expect(within(plansSection).getByText('Billed $120 every 6 months')).toBeInTheDocument();
  });

  it('shows a full-page loading spinner while billing context data is loading', () => {
    apiClientGetMock.mockReturnValue(new Promise(() => undefined));

    renderBillingPage();

    expect(screen.getByTestId('billing-page-loading')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Loading billing info…' })).toBeInTheDocument();
  });

  it('wires the Usage upgrade CTA to the #plans scroll anchor', async () => {
    renderBillingPage();

    const usageCard = await screen.findByTestId('usage-card');
    fireEvent.click(within(usageCard).getByRole('link', { name: 'Upgrade subscription to save money' }));

    await waitFor(() => {
      expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
    });
  });

  it('wires plan and billing-management CTAs to checkout and portal API calls', async () => {
    renderBillingPage();

    const plansSection = await screen.findByTestId('plans-section');
    fireEvent.click(within(screen.getByTestId('plan-card-3month')).getByRole('button', { name: 'Choose Plan' }));

    await waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledWith(
        '/billing/checkout',
        expect.objectContaining({
          plan: '3month',
          success_url: expect.stringContaining('/billing?checkout=success'),
          cancel_url: expect.stringContaining('/billing?checkout=cancel'),
        }),
      );
    });

    const billingInfoCard = screen.getByTestId('billing-info-card');
    fireEvent.click(within(billingInfoCard).getByRole('button', { name: 'Manage Billing' }));

    await waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledWith(
        '/billing/portal',
        expect.objectContaining({ return_url: expect.stringContaining(window.location.origin) }),
      );
      expect(window.open).toHaveBeenCalledWith('https://billing.example.test/session', '_blank', 'noopener,noreferrer');
    });

    expect(plansSection).toHaveAttribute('id', 'plans');
  });

  it('renders Hebrew page and Plans copy with RTL layout', async () => {
    document.documentElement.lang = 'he';

    renderBillingPage();

    const page = await screen.findByTestId('billing-page');
    expect(page).toHaveAttribute('dir', 'rtl');
    expect(within(page).getByRole('heading', { level: 1, name: 'חיוב' })).toBeInTheDocument();

    const plansSection = screen.getByTestId('plans-section');
    expect(plansSection).toHaveAttribute('dir', 'rtl');
    expect(within(plansSection).getByRole('heading', { level: 2, name: 'בחרו את התוכנית שלכם' })).toBeInTheDocument();
    expect(within(screen.getByTestId('plan-card-3month')).getByText('חיוב בסך $75 כל 3 חודשים')).toBeInTheDocument();
  });
});
