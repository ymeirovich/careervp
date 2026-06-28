import '../../../src/frontend/tests/vitest-setup';
import '../../../src/frontend/tests/ui/setup';

// spec_id: FE-UI-007  component: Spinner  file: src/frontend/components/ui/Spinner.tsx
// Verification contract: AC-001 (unit, pre_merge), AC-002 (unit, pre_merge)

import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Button } from '../../../src/frontend/components/ui/Button';
import { Spinner } from '../../../src/frontend/components/ui/Spinner';
import type { SpinnerProps } from '../../../src/frontend/components/ui/Spinner';

function renderInlineLoadingButton() {
  return render(
    <Button isLoading>
      Creating...
    </Button>
  );
}

describe('Spinner - AC-001 inline-only usage contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders inside an inline loading button context', () => {
    renderInlineLoadingButton();

    const spinner = screen.getByTestId('spinner');
    expect(spinner).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText('Creating...')).toBeInTheDocument();
  });

  it('does not render full-section sizing classes by default', () => {
    render(<Spinner />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).not.toContain('w-full');
      expect(svg.className.baseVal).not.toContain('h-full');
      expect(svg.className.baseVal).not.toContain('h-screen');
    }
  });
});

describe('Spinner - AC-002 button inline loading state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uses the sm size when Button is loading', () => {
    renderInlineLoadingButton();

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).toContain('h-4');
      expect(svg.className.baseVal).toContain('w-4');
    }
  });

  it('disables the button while loading', () => {
    renderInlineLoadingButton();

    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows the loading label alongside the spinner', () => {
    renderInlineLoadingButton();

    expect(screen.getByText('Creating...')).toBeInTheDocument();
    expect(screen.getByTestId('spinner')).toBeInTheDocument();
  });

  it('marks the button as busy while loading', () => {
    renderInlineLoadingButton();

    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });
});

describe('Spinner - default rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders role status by default', () => {
    render(<Spinner />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('uses the default aria-label when no label is provided', () => {
    render(<Spinner />);

    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading…');
  });

  it('sets aria-live to polite', () => {
    render(<Spinner />);

    expect(screen.getByTestId('spinner')).toHaveAttribute('aria-live', 'polite');
  });

  it('renders the canonical test id', () => {
    render(<Spinner />);

    expect(screen.getByTestId('spinner')).toBeInTheDocument();
  });

  it('hides the decorative svg from assistive tech', () => {
    render(<Spinner />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg).toHaveAttribute('aria-hidden', 'true');
    }
  });
});

describe('Spinner - size variants', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('applies sm classes when size is sm', () => {
    render(<Spinner size="sm" />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).toContain('h-4');
      expect(svg.className.baseVal).toContain('w-4');
    }
  });

  it('applies md classes when size is md', () => {
    render(<Spinner size="md" />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).toContain('h-5');
      expect(svg.className.baseVal).toContain('w-5');
    }
  });

  it('applies lg classes when size is lg', () => {
    render(<Spinner size="lg" />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).toContain('h-7');
      expect(svg.className.baseVal).toContain('w-7');
    }
  });

  it('defaults to md classes when size is omitted', () => {
    render(<Spinner />);

    const svg = screen.getByTestId('spinner').querySelector('svg');
    expect(svg).not.toBeNull();
    if (svg) {
      expect(svg.className.baseVal).toContain('h-5');
      expect(svg.className.baseVal).toContain('w-5');
    }
  });
});

describe('Spinner - custom aria-label', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a custom aria-label when provided', () => {
    render(<Spinner aria-label="Submitting form" />);

    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Submitting form');
  });

  it('replaces the default aria-label when custom text is provided', () => {
    render(<Spinner aria-label="Please wait" />);

    expect(screen.getByRole('status')).not.toHaveAttribute('aria-label', 'Loading…');
  });
});

describe('Spinner - className passthrough', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('appends custom classes to the wrapper', () => {
    render(<Spinner className="my-custom-class" />);

    expect(screen.getByTestId('spinner')).toHaveClass('my-custom-class');
  });
});

describe('Spinner - TypeScript prop contract', () => {
  it('accepts sm md lg and defaults without extra props', () => {
    const withSm: SpinnerProps = { size: 'sm' };
    const withMd: SpinnerProps = { size: 'md' };
    const withLg: SpinnerProps = { size: 'lg' };
    const withDefaults: SpinnerProps = {};

    expect(withSm).toBeDefined();
    expect(withMd).toBeDefined();
    expect(withLg).toBeDefined();
    expect(withDefaults).toBeDefined();
  });
});
