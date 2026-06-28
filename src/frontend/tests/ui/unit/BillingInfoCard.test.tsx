import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { getSubscriptionMock, createBillingPortalMock } = vi.hoisted(() => ({
  getSubscriptionMock: vi.fn(),
  createBillingPortalMock: vi.fn(),
}));

vi.mock('../../../api/methods', () => ({
  api: {
    getSubscription: () => getSubscriptionMock(),
    createBillingPortal: (data?: { return_url?: string }) => createBillingPortalMock(data),
  },
}));

import { BillingInfoCard } from '../../../components/billing/BillingInfoCard';

afterEach(() => {
  document.documentElement.lang = 'en';
  getSubscriptionMock.mockReset();
  createBillingPortalMock.mockReset();
  vi.restoreAllMocks();
});

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('FE-UI-024 — BillingInfoCard', () => {
  it('renders payment method, trust line, and aria-label when payment method exists', async () => {
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        payment_method: {
          last4: '6363',
          brand: 'visa',
        },
      },
    });

    renderWithQuery(<BillingInfoCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'Billing Info' });
    const card = heading.closest('[data-testid="billing-info-card"]') as HTMLElement;
    expect(card).toBeTruthy();

    const method = within(card).getByTestId('billing-info-payment-method');
    expect(method).toHaveTextContent('Payment method •••• 6363 (Visa)');
    expect(method).toHaveAttribute('aria-label', 'Payment method ending in 6363, Visa');
    expect(within(card).getByText('Billing handled securely via Stripe.')).toBeInTheDocument();

    expect(within(card).getByRole('button', { name: 'Manage Billing' })).toBeInTheDocument();
  });

  it('renders empty state with Add Payment Method CTA when no payment method exists', async () => {
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: {
        plan_type: 'monthly',
        status: 'trialing',
        payment_method: null,
      },
    });

    renderWithQuery(<BillingInfoCard />);

    await screen.findByText('No payment method');
    const card = screen.getByTestId('billing-info-card');
    expect(within(card).getByText('No payment method')).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'Add Payment Method' })).toBeInTheDocument();
  });

  it('opens the Stripe billing portal in a new tab when Manage Billing is clicked', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        payment_method: {
          last4: '1111',
          brand: 'visa',
        },
      },
    });

    createBillingPortalMock.mockResolvedValue({
      portal_url: 'https://billing.example.com/portal/session_123',
    });

    renderWithQuery(<BillingInfoCard />);

    const manageButton = await screen.findByRole('button', { name: 'Manage Billing' });
    fireEvent.click(manageButton);

    await waitFor(() => {
      expect(createBillingPortalMock).toHaveBeenCalledTimes(1);
      expect(openSpy).toHaveBeenCalledWith('https://billing.example.com/portal/session_123', '_blank', 'noopener,noreferrer');
    });
  });

  it('opens the Stripe billing portal in a new tab when Add Payment Method is clicked', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: {
        plan_type: 'monthly',
        status: 'trialing',
        payment_method: null,
      },
    });

    createBillingPortalMock.mockResolvedValue({
      portal_url: 'https://billing.example.com/portal/session_456',
    });

    renderWithQuery(<BillingInfoCard />);

    const addButton = await screen.findByRole('button', { name: 'Add Payment Method' });
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(createBillingPortalMock).toHaveBeenCalledTimes(1);
      expect(openSpy).toHaveBeenCalledWith('https://billing.example.com/portal/session_456', '_blank', 'noopener,noreferrer');
    });
  });

  it('shows a shimmer skeleton while loading', () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    getSubscriptionMock.mockImplementation(async () => {
      await gate;
      return {
        has_active_subscription: false,
        subscription: null,
      };
    });

    renderWithQuery(<BillingInfoCard />);

    expect(screen.getByTestId('billing-info-skeleton')).toBeInTheDocument();
    release();
  });

  it('renders an inline error state with Retry, then refetches on click', async () => {
    getSubscriptionMock
      .mockRejectedValueOnce(new Error('Server error'))
      .mockResolvedValueOnce({
        has_active_subscription: true,
        subscription: {
          plan_type: 'monthly',
          status: 'active',
          payment_method: {
            last4: '6363',
            brand: 'visa',
          },
        },
      });

    renderWithQuery(<BillingInfoCard />);

    const card = await screen.findByTestId('billing-info-card');
    await waitFor(() => {
      expect(within(card).getByText(/server error/i)).toBeInTheDocument();
    });

    fireEvent.click(within(card).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(getSubscriptionMock).toHaveBeenCalledTimes(2);
      expect(within(card).getByText('Payment method •••• 6363 (Visa)')).toBeInTheDocument();
    });
  });

  it('renders an inline portal error message when POST /billing/portal fails', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        payment_method: {
          last4: '6363',
          brand: 'visa',
        },
      },
    });

    createBillingPortalMock.mockRejectedValueOnce(new Error('Portal unavailable'));

    renderWithQuery(<BillingInfoCard />);

    const manageButton = await screen.findByRole('button', { name: 'Manage Billing' });
    fireEvent.click(manageButton);

    const card = screen.getByTestId('billing-info-card');
    await waitFor(() => {
      expect(within(card).getByTestId('billing-info-portal-error')).toHaveTextContent('Portal unavailable');
      expect(openSpy).not.toHaveBeenCalled();
    });
  });

  it('renders Hebrew copy and RTL layout when locale is he', async () => {
    document.documentElement.lang = 'he';

    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        payment_method: {
          last4: '6363',
          brand: 'visa',
        },
      },
    });

    renderWithQuery(<BillingInfoCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'פרטי חיוב' });
    const card = heading.closest('[data-testid="billing-info-card"]') as HTMLElement;
    expect(card).toBeTruthy();
    expect(card).toHaveAttribute('dir', 'rtl');

    expect(within(card).getByRole('button', { name: 'ניהול חיוב' })).toBeInTheDocument();
  });
});
