// spec_id: FE-UI-001  component: Badge  file: src/frontend/components/ui/Badge.tsx
// Integration notes: Badge has no API dependencies. Integration tests cover rendering
// within a realistic React tree (QueryClientProvider) and verify that soft prop
// behaviour survives provider wrapping unchanged.
import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import { Badge } from '../../../src/frontend/components/ui/Badge';
import { StatusBadge } from '../../../src/frontend/components/ui/StatusBadge';

// ---------------------------------------------------------------------------
// wrapper factory — fresh QueryClient per test to prevent state leakage
// ---------------------------------------------------------------------------
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ---------------------------------------------------------------------------
// Badge integration — soft prop survives provider context
// ---------------------------------------------------------------------------
describe('Badge integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('test_renders_soft_success_classes_within_provider_tree', () => {
    // TODO: render Badge with variant="success" soft={true} data-testid="badge"
    //       inside createWrapper()
    // TODO: query element by testId "badge"
    // TODO: assert element classList contains "bg-green-50"
    // TODO: assert element classList contains "text-green-700"
  });

  it('test_renders_solid_success_classes_within_provider_tree_when_soft_false', () => {
    // TODO: render Badge with variant="success" soft={false} inside createWrapper()
    // TODO: assert element classList contains "bg-state-active"
    // TODO: assert element classList does NOT contain "bg-green-50"
  });

  it('test_renders_soft_error_unchanged_within_provider_tree', () => {
    // AC-003 integration: error variant must retain solid style even with soft={true}
    // TODO: render Badge with variant="error" soft={true} inside createWrapper()
    // TODO: assert element classList contains "bg-state-error"
    // TODO: assert element classList contains "text-white"
  });

  it('test_statusbadge_forwards_soft_prop_within_provider_tree', () => {
    // AC-010 integration: StatusBadge soft propagation survives provider wrapping
    // TODO: render StatusBadge with status="complete" soft={true} data-testid="sb"
    //       inside createWrapper()
    // TODO: query element by testId "sb"
    // TODO: assert element classList contains "bg-green-50"
  });
});
