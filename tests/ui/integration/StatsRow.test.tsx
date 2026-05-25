// spec_id: FE-UI-009  component: StatsRow  file: src/frontend/components/dashboard/StatsRow.tsx
// Integration notes: StatsRow has no API dependencies — data flows in via props from
// DashboardPage. Integration tests verify rendering within a realistic provider tree
// and that prop-driven state transitions (default ↔ loading) behave correctly there.
import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import { StatsRow } from '../../../src/frontend/components/dashboard/StatsRow';

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

const defaultProps = {
  plan: 'Annual Plan',
  creditsUsed: 1,
  creditsTotal: 3,
  isActive: true,
};

// ---------------------------------------------------------------------------
// rendering with data — state: default
// ---------------------------------------------------------------------------
describe('StatsRow integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('test_renders_data_within_provider_tree_when_isLoading_false', () => {
    // Verifies component renders correctly inside QueryClientProvider
    // (mirrors how DashboardPage wraps it at the app level)
    // TODO: render <StatsRow {...defaultProps} isLoading={false} /> inside createWrapper()
    // TODO: assert plan value "Annual Plan" is in the document
    // TODO: assert credits fraction text is in the document
    // TODO: assert "Active" status text is in the document
  });

  it('test_renders_data_within_provider_tree_when_isLoading_omitted', () => {
    // AC-005: backward-compatible — omitting isLoading must render data
    // TODO: render <StatsRow {...defaultProps} /> inside createWrapper()
    // TODO: assert plan value is visible
    // TODO: assert no element with "animate-pulse" class is present
  });

  // ---------------------------------------------------------------------------
  // state transition: default → loading (prop change)
  // ---------------------------------------------------------------------------

  it('test_renders_skeleton_within_provider_tree_when_isLoading_true', () => {
    // AC-002/AC-003: loading state survives provider wrapping
    // TODO: render <StatsRow {...defaultProps} isLoading={true} /> inside createWrapper()
    // TODO: query all skeleton elements
    // TODO: assert 3 skeleton elements are present
    // TODO: assert each has "animate-pulse" class
  });

  it('test_data_text_absent_within_provider_tree_when_isLoading_true', () => {
    // AC-004: no data text during loading — confirmed inside provider tree
    // TODO: render <StatsRow {...defaultProps} isLoading={true} /> inside createWrapper()
    // TODO: assert screen.queryByText("Annual Plan") is null
    // TODO: assert screen.queryByText("Active") is null
  });

  it('test_pill_corner_radius_within_provider_tree_when_default', () => {
    // AC-001: rounded-xl class survives provider wrapping
    // TODO: render <StatsRow {...defaultProps} /> inside createWrapper()
    // TODO: query all three pill containers
    // TODO: assert each classList contains "rounded-xl"
    // TODO: assert each classList does NOT contain "rounded-lg"
  });

  it('test_inactive_status_renders_within_provider_tree', () => {
    // AC-005: isActive=false renders "Inactive" correctly inside provider tree
    // TODO: render <StatsRow {...defaultProps} isActive={false} /> inside createWrapper()
    // TODO: assert "Inactive" text is in the document
    // TODO: assert "Active" text is NOT in the document
  });
});
