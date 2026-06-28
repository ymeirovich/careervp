import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge, type BadgeProps } from '../../../components/ui/Badge';
import { StatusBadge } from '../../../components/ui/StatusBadge';

const renderBadge = (props: Partial<BadgeProps> & Pick<BadgeProps, 'variant'>) => {
  render(<Badge {...props}>Label</Badge>);
  return screen.getByText('Label');
};

describe('Badge soft variant', () => {
  it('renders success soft with green tinted classes', () => {
    const badge = renderBadge({ variant: 'success', soft: true });
    expect(badge.className).toContain('bg-green-50');
    expect(badge.className).toContain('text-green-700');
    expect(badge.className).toContain('border-green-200');
  });

  it('renders info soft with blue tinted classes', () => {
    const badge = renderBadge({ variant: 'info', soft: true });
    expect(badge.className).toContain('bg-blue-50');
    expect(badge.className).toContain('text-blue-700');
    expect(badge.className).toContain('border-blue-200');
  });

  it('keeps error solid when soft is true', () => {
    const badge = renderBadge({ variant: 'error', soft: true });
    expect(badge.className).toContain('bg-state-error');
    expect(badge.className).toContain('text-white');
    expect(badge.className).not.toContain('bg-red-50');
  });

  it('renders final soft with green tinted classes', () => {
    const badge = renderBadge({ variant: 'final', soft: true });
    expect(badge.className).toContain('bg-green-50');
    expect(badge.className).toContain('text-green-700');
    expect(badge.className).toContain('border-green-200');
  });

  it('renders edited soft with green tinted classes', () => {
    const badge = renderBadge({ variant: 'edited', soft: true });
    expect(badge.className).toContain('bg-green-50');
    expect(badge.className).toContain('text-green-700');
    expect(badge.className).toContain('border-green-200');
  });

  it('renders neutral soft with gray tinted classes', () => {
    const badge = renderBadge({ variant: 'neutral', soft: true });
    expect(badge.className).toContain('bg-gray-50');
    expect(badge.className).toContain('text-gray-700');
    expect(badge.className).toContain('border-gray-200');
  });

  it('renders warning soft with amber tinted classes', () => {
    const badge = renderBadge({ variant: 'warning', soft: true });
    expect(badge.className).toContain('bg-amber-50');
    expect(badge.className).toContain('text-amber-700');
    expect(badge.className).toContain('border-amber-200');
  });

  it('keeps solid style when soft is omitted', () => {
    const badge = renderBadge({ variant: 'success' });
    expect(badge.className).toContain('bg-state-active');
    expect(badge.className).toContain('text-white');
    expect(badge.className).not.toContain('bg-green-50');
  });

  it('keeps solid style when soft is false', () => {
    const badge = renderBadge({ variant: 'warning', soft: false });
    expect(badge.className).toContain('bg-state-warning');
    expect(badge.className).toContain('text-white');
    expect(badge.className).not.toContain('bg-amber-50');
  });

  it('forwards soft=true from StatusBadge', () => {
    render(<StatusBadge status="ready" soft data-testid="status-badge" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('bg-green-50');
    expect(badge.className).toContain('text-green-700');
    expect(badge.className).toContain('border-green-200');
  });

  it('renders stale soft with amber tinted classes', () => {
    const badge = renderBadge({ variant: 'stale', soft: true });
    expect(badge.className).toContain('bg-amber-50');
    expect(badge.className).toContain('text-amber-700');
    expect(badge.className).toContain('border-amber-200');
  });

  it('types soft as optional boolean', () => {
    const softValue: BadgeProps['soft'] = true;
    const softValueUndefined: BadgeProps['soft'] = undefined;
    expect(softValue).toBe(true);
    expect(softValueUndefined).toBeUndefined();
  });
});
