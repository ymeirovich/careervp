import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { ProcessingDots } from '../../components/ui/ProcessingDots';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ProcessingDots', () => {
  it('renders the "Processing" text label', () => {
    render(<ProcessingDots />);
    expect(screen.getByText(/processing/i)).toBeDefined();
  });

  it('renders exactly 3 dot spans with aria-hidden="true"', () => {
    render(<ProcessingDots />);
    const dots = document.querySelectorAll('[aria-hidden="true"]');
    expect(dots).toHaveLength(3);
  });

  it('dot spans do NOT use animate-pulse class', () => {
    render(<ProcessingDots />);
    const dots = document.querySelectorAll('[aria-hidden="true"]');
    dots.forEach((dot) => {
      expect(dot.className).not.toContain('animate-pulse');
    });
  });

  it('renders static "Processing..." text in reduced-motion context', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(<ProcessingDots />);
    // In reduced-motion mode: static "Processing..." with no separate dot spans
    expect(screen.getByText('Processing...')).toBeDefined();
    expect(document.querySelectorAll('[aria-hidden="true"]')).toHaveLength(0);
  });
});
