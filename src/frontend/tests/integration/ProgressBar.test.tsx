import '../vitest-setup';
import '../ui/setup';

// spec_id: FE-UI-002  component: ProgressBar
// file: src/frontend/components/ui/ProgressBar.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, vi } from 'vitest';
import { ProgressBar } from '../../components/ui/ProgressBar';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ProgressBar integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders label and percentage inside a provider tree', () => {
    render(<ProgressBar value={85} showLabel />, { wrapper: createWrapper() });

    expect(screen.getByText('Progress')).toBeVisible();
    expect(screen.getByText('85%')).toBeVisible();
  });

  it('keeps the old no-label rendering path intact', () => {
    render(<ProgressBar value={85} />, { wrapper: createWrapper() });

    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
    expect(screen.queryByText('85%')).not.toBeInTheDocument();
  });

  it('clamps visible text and aria-valuenow within a provider tree', () => {
    render(<ProgressBar value={150} showLabel />, { wrapper: createWrapper() });

    expect(screen.getByText('100%')).toBeVisible();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });
});
