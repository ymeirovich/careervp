import '../../vitest-setup';
import '../setup';

// spec_id: FE-UI-006  component: ErrorBoundary
// file: src/frontend/components/ErrorBoundary/ErrorBoundary.tsx
// Integration notes: No ACs are marked verification_type: integration in this spec.
// Both ACs are verification_type: unit (see unit test file).
// These tests exercise the boundary within a minimal page context (React tree with
// providers) to validate behaviour that requires a more realistic render environment.

import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ReactNode } from 'react';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';

// ---------------------------------------------------------------------------
// wrapper — minimal page context (add providers here as the app grows)
// ---------------------------------------------------------------------------

function PageWrapper({ children }: { children: ReactNode }) {
  // TODO: wrap with AuthContextProvider, ThemeProvider, etc. as needed
  return <div data-testid="page-root">{children}</div>;
}

function renderInPage(ui: ReactNode) {
  return render(ui, { wrapper: PageWrapper });
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function ThrowingChild({ shouldThrow = true }: { shouldThrow?: boolean }): ReactNode {
  if (shouldThrow) throw new Error('render error');
  return <div data-testid="child">OK</div>;
}

// ---------------------------------------------------------------------------
// Boundary in page context — healthy path
// ---------------------------------------------------------------------------

describe('ErrorBoundary integration — renders within page context', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_renders_page_content_when_no_error_thrown', () => {
    renderInPage(
      <ErrorBoundary cloudwatchKey="page">
        <div data-testid="content">Page Content</div>
      </ErrorBoundary>
    );

    expect(screen.getByTestId('page-root')).toContainElement(screen.getByTestId('content'));
  });

  it('test_does_not_mount_fallback_into_page_root_when_children_healthy', () => {
    renderInPage(
      <ErrorBoundary cloudwatchKey="page">
        <div data-testid="content">Page Content</div>
      </ErrorBoundary>
    );

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Boundary in page context — crash recovery (AC-002 path, page-level)
// ---------------------------------------------------------------------------

describe('ErrorBoundary integration — crash recovery in page context', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.clearAllMocks();
  });

  it('test_replaces_page_subtree_with_fallback_when_child_throws', () => {
    renderInPage(
      <ErrorBoundary cloudwatchKey="page">
        <ThrowingChild />
      </ErrorBoundary>
    );

    const pageRoot = screen.getByTestId('page-root');
    const alert = screen.getByRole('alert');
    expect(pageRoot).toContainElement(alert);
  });

  it('test_fallback_is_scoped_to_boundary_subtree_not_full_page', () => {
    // Verifies cascade risk mitigation: only the wrapped subtree is replaced.
    renderInPage(
      <>
        <header data-testid="page-header">Header</header>
        <ErrorBoundary cloudwatchKey="main">
          <ThrowingChild />
        </ErrorBoundary>
      </>
    );

    expect(screen.getByTestId('page-header')).toBeVisible();
    expect(screen.getByRole('alert')).toBeVisible();
  });

  it('test_multiple_boundaries_isolate_crashes_independently', () => {
    // Two ErrorBoundary instances: only the one whose child throws activates.
    renderInPage(
      <>
        <ErrorBoundary cloudwatchKey="boundary-a">
          <ThrowingChild shouldThrow />
        </ErrorBoundary>
        <ErrorBoundary cloudwatchKey="boundary-b">
          <div data-testid="sibling-ok">OK</div>
        </ErrorBoundary>
      </>
    );

    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(screen.getByTestId('sibling-ok')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Boundary in page context — reset flow (AC-002, page-level)
// ---------------------------------------------------------------------------

describe('ErrorBoundary integration — reset restores page content', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.clearAllMocks();
  });

  it('test_re_renders_children_in_page_context_after_reset', () => {
    function Harness(): ReactNode {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <>
          <button type="button" data-testid="toggle" onClick={() => setShouldThrow(false)}>
            Toggle
          </button>
          <ErrorBoundary cloudwatchKey="page">
            <ThrowingChild shouldThrow={shouldThrow} />
          </ErrorBoundary>
        </>
      );
    }

    renderInPage(<Harness />);

    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Batch reset + toggle so both state updates flush together before re-render
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
      fireEvent.click(screen.getByTestId('toggle'));
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Boundary in page context — AC-001 contract (API errors stay inline)
// ---------------------------------------------------------------------------

describe('ErrorBoundary integration — AC-001: API error does not reach boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_page_renders_inline_error_ui_without_triggering_boundary_takeover', () => {
    // Simulates a well-behaved page component that catches an API error and
    // renders its own error state — ErrorBoundary should remain transparent.
    function MockPage(): ReactNode {
      // Component handles error internally; does NOT throw to the parent
      const hasError = true; // simulates a failed API response
      if (hasError) {
        return <p data-testid="inline-err">Failed to load data.</p>;
      }
      return <div data-testid="page-content">Content</div>;
    }

    renderInPage(
      <ErrorBoundary cloudwatchKey="page">
        <MockPage />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('inline-err')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
