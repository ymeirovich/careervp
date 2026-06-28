import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { useUserContextMock, apiClientPostMock } = vi.hoisted(() => ({
  useUserContextMock: vi.fn(),
  apiClientPostMock: vi.fn(),
}));

vi.mock('../../../hooks/useUserContext', () => ({
  useUserContext: () => useUserContextMock(),
}));

vi.mock('../../../api/client', () => ({
  apiClient: { post: (...args: unknown[]) => apiClientPostMock(...args) },
}));

import { PlansSection } from '../../../components/billing/PlansSection';

afterEach(() => {
  document.documentElement.lang = 'en';
  useUserContextMock.mockReset();
  apiClientPostMock.mockReset();
});

function mockUserContext(planType: string | null) {
  useUserContextMock.mockReturnValue({
    user: null,
    usage: null,
    subscription: planType
      ? { has_active_subscription: true, subscription: { plan_type: planType, status: 'active', current_period_end: null } }
      : { has_active_subscription: false, subscription: null },
    isLoading: false,
    hasActiveAccess: false,
    applicationsRemaining: null,
  });
}

describe('FE-UI-025 — PlansSection', () => {
  it('renders a section with id="plans" and aria-labelledby pointing to the h2 heading', () => {
    mockUserContext(null);

    render(<PlansSection />);

    const section = screen.getByTestId('plans-section');
    expect(section.tagName).toBe('SECTION');
    expect(section).toHaveAttribute('id', 'plans');
    expect(section).toHaveAttribute('aria-labelledby', 'plans-section-heading');

    const heading = screen.getByRole('heading', { level: 2, name: 'Choose Your Plan' });
    expect(heading).toHaveAttribute('id', 'plans-section-heading');
  });

  it('renders a 3-column layout on md+ via Tailwind grid classes', () => {
    mockUserContext(null);

    render(<PlansSection />);

    const grid = screen.getByTestId('plans-grid');
    expect(grid.className).toContain('grid-cols-1');
    expect(grid.className).toContain('md:grid-cols-3');
  });

  it('stacks cards on mobile and places the recommended plan first via order utilities', () => {
    mockUserContext(null);

    render(<PlansSection />);

    expect(screen.getByTestId('plan-card-wrap-3month').className).toContain('order-1');
    expect(screen.getByTestId('plan-card-wrap-3month').className).toContain('md:order-2');
    expect(screen.getByTestId('plan-card-wrap-monthly').className).toContain('order-2');
    expect(screen.getByTestId('plan-card-wrap-monthly').className).toContain('md:order-1');
    expect(screen.getByTestId('plan-card-wrap-6month').className).toContain('order-3');
    expect(screen.getByTestId('plan-card-wrap-6month').className).toContain('md:order-3');
  });

  it('renders three plan cards with correct pricing and billing labels', () => {
    mockUserContext(null);

    render(<PlansSection />);

    const monthly = screen.getByTestId('plan-card-monthly');
    expect(within(monthly).getByRole('heading', { level: 3, name: 'Monthly' })).toBeInTheDocument();
    expect(within(monthly).getByText('$30')).toBeInTheDocument();
    expect(within(monthly).getByText('Billed monthly')).toBeInTheDocument();

    const threeMonth = screen.getByTestId('plan-card-3month');
    expect(within(threeMonth).getByRole('heading', { level: 3, name: '3-Month' })).toBeInTheDocument();
    expect(within(threeMonth).getByText('$25')).toBeInTheDocument();
    expect(within(threeMonth).getByText('Billed $75 every 3 months')).toBeInTheDocument();

    const sixMonth = screen.getByTestId('plan-card-6month');
    expect(within(sixMonth).getByRole('heading', { level: 3, name: '6-Month' })).toBeInTheDocument();
    expect(within(sixMonth).getByText('$20')).toBeInTheDocument();
    expect(within(sixMonth).getByText('Billed $120 every 6 months')).toBeInTheDocument();
  });

  it('marks the current plan based on subscription.plan_type and hardcodes 3-Month as recommended', () => {
    mockUserContext('3month');

    render(<PlansSection />);

    const threeMonth = screen.getByTestId('plan-card-3month');
    expect(threeMonth.className).toContain('border-2');
    expect(threeMonth.className).toContain('border-primary-action');
    expect(within(threeMonth).getByRole('button', { name: 'Current Plan' })).toHaveAttribute('aria-disabled', 'true');

    const monthly = screen.getByTestId('plan-card-monthly');
    expect(monthly.className).toContain('border-border-default');
    expect(within(monthly).getByRole('button', { name: 'Choose Plan' })).not.toHaveAttribute('aria-disabled');

    const sixMonth = screen.getByTestId('plan-card-6month');
    expect(sixMonth.className).toContain('border-border-default');
    expect(within(sixMonth).getByRole('button', { name: 'Choose Plan' })).not.toHaveAttribute('aria-disabled');
  });

  it('renders centered mailto support link below the cards', () => {
    mockUserContext(null);

    render(<PlansSection />);

    const link = screen.getByRole('link', { name: 'Contact us' });
    expect(link).toHaveAttribute('href', 'mailto:support@careervp.com');
  });

  it('renders Hebrew copy and RTL layout when locale is he', () => {
    document.documentElement.lang = 'he';
    mockUserContext(null);

    render(<PlansSection />);

    const section = screen.getByTestId('plans-section');
    expect(section).toHaveAttribute('dir', 'rtl');
    expect(screen.getByRole('heading', { level: 2, name: 'בחרו את התוכנית שלכם' })).toBeInTheDocument();
    expect(within(screen.getByTestId('plan-card-monthly')).getByText('חיוב חודשי')).toBeInTheDocument();
    expect(screen.getByText('שאלות?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'צרו קשר' })).toHaveAttribute('href', 'mailto:support@careervp.com');
  });

  it('posts to /billing/checkout when a plan is chosen', async () => {
    mockUserContext(null);
    apiClientPostMock.mockResolvedValue({ data: { checkout_url: '' } });

    render(<PlansSection />);

    fireEvent.click(within(screen.getByTestId('plan-card-monthly')).getByRole('button', { name: 'Choose Plan' }));

    expect(apiClientPostMock).toHaveBeenCalledWith(
      '/billing/checkout',
      expect.objectContaining({ plan: 'monthly' }),
    );
  });
});

