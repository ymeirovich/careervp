// spec_id: FE-UI-002  component: ProgressBar  file: src/frontend/components/ui/ProgressBar.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ProgressBar } from '../../../src/frontend/components/ui/ProgressBar';

function renderProgressBar(props: React.ComponentProps<typeof ProgressBar>) {
  return render(<ProgressBar {...props} />);
}

describe('ProgressBar', () => {
  it('renders no visible label when showLabel is omitted', () => {
    const { container } = renderProgressBar({ value: 50 });

    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
    expect(container.querySelector('[role="progressbar"]')).toHaveAttribute('aria-valuenow', '50');
  });

  it('renders no visible label when showLabel is false', () => {
    renderProgressBar({ value: 50, showLabel: false });

    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('renders a visible label row when showLabel is true', () => {
    renderProgressBar({ value: 85, showLabel: true });

    expect(screen.getByText('Progress')).toBeVisible();
    expect(screen.getByText('85%')).toBeVisible();
  });

  it('clamps visible percentage and aria-valuenow', () => {
    const { container, rerender } = render(<ProgressBar value={150} showLabel />);
    expect(screen.getByText('100%')).toBeVisible();
    expect(container.querySelector('[role="progressbar"]')).toHaveAttribute('aria-valuenow', '100');

    rerender(<ProgressBar value={-5} showLabel />);
    expect(screen.getByText('0%')).toBeVisible();
    expect(container.querySelector('[role="progressbar"]')).toHaveAttribute('aria-valuenow', '0');
  });

  it('preserves aria label and sr-only text when showLabel is true', () => {
    renderProgressBar({ value: 85, label: 'Generating CV', showLabel: true });

    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toHaveAttribute('aria-label', 'Generating CV');
    expect(screen.getByText('Generating CV: 85%')).toHaveClass('sr-only');
  });

  it('keeps rounded ends and error color behavior', () => {
    const { container } = renderProgressBar({ value: 100, color: 'error', showLabel: true });

    const track = container.querySelector('.bg-surface-subtle');
    const fill = container.querySelector('.bg-state-error');

    expect(track).toHaveClass('h-2');
    expect(track).toHaveClass('rounded-full');
    expect(fill).toHaveClass('rounded-full');
  });
});
