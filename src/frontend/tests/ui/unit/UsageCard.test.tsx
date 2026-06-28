import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { getUsageMock, getSubscriptionMock } = vi.hoisted(() => ({
  getUsageMock: vi.fn(),
  getSubscriptionMock: vi.fn(),
}));

vi.mock('../../../api/methods', () => ({
  api: {
    getUsage: () => getUsageMock(),
    getSubscription: () => getSubscriptionMock(),
  },
}));

import { UsageCard } from '../../../components/billing/UsageCard';

afterEach(() => {
  document.documentElement.lang = 'en';
  document.body.innerHTML = '';
  getUsageMock.mockReset();
  getSubscriptionMock.mockReset();
});

beforeEach(() => {
  // JSDOM doesn't implement this; we assert it was called
  Element.prototype.scrollIntoView = vi.fn();
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

describe('FE-UI-023 — UsageCard', () => {
  it('renders paid state with "Unlimited credits" and smooth-scroll upgrade link', async () => {
    document.body.innerHTML = '<div id="plans"></div>';

    getUsageMock.mockResolvedValue({
      credits_used: 0,
      credits_total: 0,
      trial: { active: false },
    });
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        plan_type: 'monthly',
        status: 'active',
      },
    });

    renderWithQuery(<UsageCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'Usage' });
    const card = heading.closest('[data-testid="usage-card"]') as HTMLElement;
    expect(card).toBeTruthy();

    expect(within(card).getByText('Unlimited credits')).toBeInTheDocument();
    const link = within(card).getByRole('link', { name: 'Upgrade subscription to save money' });

    fireEvent.click(link);

    await waitFor(() => {
      expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(1);
    });
  });

  it('renders trial state with "X of 3 applications used" and progressbar a11y attributes', async () => {
    getUsageMock.mockResolvedValue({
      trial: { active: true, applications_used: 2, applications_limit: 3 },
    });
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: null,
    });

    renderWithQuery(<UsageCard />);

    const label = await screen.findByTestId('usage-trial-label');
    expect(label).toHaveTextContent('2 of 3 applications used');

    const progress = screen.getByTestId('usage-progress');
    expect(progress).toHaveAttribute('aria-valuenow', '2');
    expect(progress).toHaveAttribute('aria-valuemin', '0');
    expect(progress).toHaveAttribute('aria-valuemax', '3');
  });

  it('shows a shimmer skeleton while loading', () => {
    let releaseUsage: () => void = () => undefined;
    const usageGate = new Promise<void>((resolve) => {
      releaseUsage = resolve;
    });

    getUsageMock.mockImplementation(async () => {
      await usageGate;
      return { trial: { active: true, applications_used: 0, applications_limit: 3 } };
    });
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: null,
    });

    renderWithQuery(<UsageCard />);
    expect(screen.getByTestId('usage-skeleton')).toBeInTheDocument();
    releaseUsage();
  });

  it('renders an inline error state with Retry, then refetches on click', async () => {
    getUsageMock
      .mockRejectedValueOnce(new Error('Server error'))
      .mockResolvedValueOnce({
        trial: { active: true, applications_used: 1, applications_limit: 3 },
      });
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: null,
    });

    renderWithQuery(<UsageCard />);

    const card = await screen.findByTestId('usage-card');
    await waitFor(() => {
      expect(within(card).getByText(/server error/i)).toBeInTheDocument();
    });

    fireEvent.click(within(card).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(within(card).getByText('1 of 3 applications used')).toBeInTheDocument();
      expect(getUsageMock).toHaveBeenCalledTimes(2);
    });
  });

  it('renders Hebrew copy and RTL layout; progress fill aligns to the right', async () => {
    document.documentElement.lang = 'he';
    getUsageMock.mockResolvedValue({
      trial: { active: true, applications_used: 1, applications_limit: 3 },
    });
    getSubscriptionMock.mockResolvedValue({
      has_active_subscription: false,
      subscription: null,
    });

    renderWithQuery(<UsageCard />);

    const heading = await screen.findByRole('heading', { level: 2, name: 'שימוש' });
    const card = heading.closest('[data-testid="usage-card"]') as HTMLElement;
    expect(card).toBeTruthy();
    expect(card).toHaveAttribute('dir', 'rtl');
    expect(within(card).getByText('1 מתוך 3 בקשות נוצלו')).toBeInTheDocument();

    const fill = within(card).getByTestId('usage-progress-fill');
    expect(fill.className).toMatch(/\bml-auto\b/);
  });
});

