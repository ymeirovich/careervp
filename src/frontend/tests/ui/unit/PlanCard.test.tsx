import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PlanCard, type PlanCardProps } from '../../../components/billing/PlanCard';

const renderPlanCard = (overrides: Partial<PlanCardProps> = {}) => {
  const props: PlanCardProps = {
    planKey: 'monthly',
    displayName: 'Monthly Plan',
    pricePerMonth: 30,
    billingPeriodLabel: 'Billed monthly',
    isCurrentPlan: false,
    isRecommended: false,
    onChoosePlan: vi.fn(),
    ...overrides,
  };

  render(<PlanCard {...props} />);
  return props;
};

describe('PlanCard', () => {
  it('renders selectable state (choose plan enabled + hover tint + standard border)', () => {
    renderPlanCard();

    const card = screen.getByTestId('plan-card-monthly');
    expect(card.className).toContain('border-border-default');
    expect(card.className).toContain('hover:bg-surface-selected');

    const button = screen.getByRole('button', { name: 'Choose Plan' });
    expect(button.getAttribute('aria-disabled')).toBeNull();
    expect(button.className).toContain('bg-primary-action');
  });

  it('renders recommended selectable state (thick primary border + choose plan enabled)', () => {
    renderPlanCard({ planKey: '3month', displayName: '3 Month Plan', pricePerMonth: 25, billingPeriodLabel: 'Billed $75 every 3 months', isRecommended: true });

    const card = screen.getByTestId('plan-card-3month');
    expect(card.className).toContain('border-2');
    expect(card.className).toContain('border-primary-action');

    const button = screen.getByRole('button', { name: 'Choose Plan' });
    expect(button.getAttribute('aria-disabled')).toBeNull();
  });

  it('renders current state (current plan aria-disabled + no hover tint) and blocks selection', () => {
    const props = renderPlanCard({ isCurrentPlan: true });

    const card = screen.getByTestId('plan-card-monthly');
    expect(card.className).not.toContain('hover:bg-surface-selected');

    const button = screen.getByRole('button', { name: 'Current Plan' });
    expect(button.getAttribute('aria-disabled')).toBe('true');
    expect(button.className).toContain('cursor-not-allowed');

    fireEvent.click(button);
    expect(props.onChoosePlan).not.toHaveBeenCalled();
  });

  it('invokes onChoosePlan(planKey) when selectable button is clicked', () => {
    const props = renderPlanCard({ planKey: '6month' });
    fireEvent.click(screen.getByRole('button', { name: 'Choose Plan' }));
    expect(props.onChoosePlan).toHaveBeenCalledWith('6month');
  });

  it('sets an aria-label on the price display describing full price', () => {
    renderPlanCard({ planKey: '3month', displayName: '3 Month Plan', pricePerMonth: 25, billingPeriodLabel: 'Billed $75 every 3 months' });
    expect(screen.getByLabelText('25 dollars per month, billed 75 every 3 months')).toBeDefined();
  });
});

