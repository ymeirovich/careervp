// spec_id: FE-UI-002  component: ProgressBar
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import { ProgressBar } from '../../src/frontend/components/ui/ProgressBar';
import type { ProgressBarProps } from '../../src/frontend/components/ui/ProgressBar';

describe('ProgressBar regression', () => {
  it('keeps the existing API contract intact', () => {
    const withoutShowLabel: ProgressBarProps = { value: 50 };
    const withLabelAndColor: ProgressBarProps = { value: 75, label: 'CV Tailoring', color: 'warning' };

    expect(withoutShowLabel).toBeDefined();
    expect(withLabelAndColor).toBeDefined();
  });

  it('renders identically without showLabel and with showLabel false', () => {
    const { container: omitted } = render(<ProgressBar value={60} />);
    const { container: explicitFalse } = render(<ProgressBar value={60} showLabel={false} />);

    expect(omitted.innerHTML).toBe(explicitFalse.innerHTML);
  });

  it('preserves default color and clamping behavior', () => {
    const { container } = render(<ProgressBar value={200} />);

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
    expect(container.querySelector('.bg-primary-action')).toBeInTheDocument();
  });

  it('keeps the sr-only label path when label is provided', () => {
    render(<ProgressBar value={70} label="Interview Prep" />);

    expect(screen.getByText('Interview Prep: 70%')).toHaveClass('sr-only');
  });
});
