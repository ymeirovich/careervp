import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { getSubscriptionMock } = vi.hoisted(() => ({
  getSubscriptionMock: vi.fn(),
}));

vi.mock('../../../api/methods', () => ({
  api: {
    getSubscription: () => getSubscriptionMock(),
  },
}));

import { SubscriptionCard } from '../../../components/billing/SubscriptionCard';

afterEach(() => {
  document.documentElement.lang = 'en';
  getSubscriptionMock.mockReset();
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

describe('FE-UI-022 — SubscriptionCard', () => {
  it('renders active subscription with green Active badge, plan pill, renewal date, and next charge', async () => {
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        cancel_at_period_end: false,
        current_period_end: '2026-06-30T00:00:00Z',
        next_charge_amount: 30,
      },
    });

    renderWithQuery(<SubscriptionCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'Current Subscription' });
    const card = heading.closest('[data-testid="subscription-card"]') as HTMLElement;
    expect(card).toBeTruthy();

    expect(within(card).getByText('Active')).toBeInTheDocument();
    expect(within(card).getByRole('status')).toHaveAttribute('aria-label', 'Subscription status: Active');

    expect(within(card).getByText('Pro Monthly')).toBeInTheDocument();
    expect(within(card).getByText(/Renews/i)).toBeInTheDocument();
    expect(within(card).getByText('$30.00')).toBeInTheDocument();

    expect(within(card).getByRole('button', { name: 'View Plans' })).toBeInTheDocument();
  });

  it('renders trialing subscription with blue Trial badge and days remaining', async () => {
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: {
        plan_type: 'monthly',
        status: 'trialing',
        trial_days_remaining: 7,
      },
    });

    renderWithQuery(<SubscriptionCard />);

    await screen.findByText('Trial');
    const card = screen.getByTestId('subscription-card');
    expect(within(card).getByText('Trial')).toBeInTheDocument();
    expect(within(card).getByText('7 days remaining')).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'View Plans' })).toBeInTheDocument();
  });

  it('renders cancelled/expired state with no badge and a Choose a Plan CTA', async () => {
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: null,
    });

    renderWithQuery(<SubscriptionCard />);

    await screen.findByText('No active subscription');
    const card = screen.getByTestId('subscription-card');
    expect(within(card).queryByRole('status')).not.toBeInTheDocument();
    expect(within(card).getByText('No active subscription')).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'Choose a Plan' })).toBeInTheDocument();
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

    renderWithQuery(<SubscriptionCard />);

    expect(screen.getByTestId('subscription-skeleton')).toBeInTheDocument();
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
          cancel_at_period_end: false,
          current_period_end: '2026-06-30T00:00:00Z',
          next_charge_amount: 30,
        },
      });

    renderWithQuery(<SubscriptionCard />);

    const card = await screen.findByTestId('subscription-card');
    await waitFor(() => {
      expect(within(card).getByText(/server error/i)).toBeInTheDocument();
    });

    fireEvent.click(within(card).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(within(card).getByText('Active')).toBeInTheDocument();
      expect(getSubscriptionMock).toHaveBeenCalledTimes(2);
    });
  });

  it('renders Hebrew copy and RTL layout when locale is he', async () => {
    document.documentElement.lang = 'he';

    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
        cancel_at_period_end: false,
        current_period_end: '2026-06-30T00:00:00Z',
        next_charge_amount: 30,
      },
    });

    renderWithQuery(<SubscriptionCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'המנוי הנוכחי' });
    const card = heading.closest('[data-testid="subscription-card"]') as HTMLElement;
    expect(card).toBeTruthy();
    expect(card).toHaveAttribute('dir', 'rtl');
    expect(within(card).getByText('פעיל')).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'צפייה בתוכניות' })).toBeInTheDocument();
  });
});
