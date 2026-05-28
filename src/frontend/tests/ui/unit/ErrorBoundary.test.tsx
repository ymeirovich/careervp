import '../../vitest-setup';
import '../setup';

// spec_id: FE-UI-006  component: ErrorBoundary
// file: src/frontend/components/ErrorBoundary/ErrorBoundary.tsx
// All ACs are verification_type: unit — no integration or live ACs exist for this spec.

import React, { type ReactNode } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';

function suppressErrorOutput() {
  vi.spyOn(console, 'error').mockImplementation(() => {});
}

function ThrowingChild({ shouldThrow, error }: { shouldThrow: boolean; error?: Error }): ReactNode {
  if (shouldThrow) throw error ?? new Error('render error');
  return <div data-testid="child">OK</div>;
}

function makeError(
  message: string,
  extras: { status?: number; isApiError?: boolean } = {}
): Error {
  return Object.assign(new Error(message), extras);
}

describe('ErrorBoundary - default state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('ErrorBoundary - uncaught render errors', () => {
  beforeEach(() => {
    suppressErrorOutput();
    vi.clearAllMocks();
  });

  it('renders the default fallback when a child throws', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
    expect(screen.queryByTestId('child')).not.toBeInTheDocument();
  });

  it('calls onError and logs to console.error when a child throws', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary cloudwatchKey="test" onError={onError}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][1]).toMatchObject({ componentStack: expect.any(String) });
    expect(console.error).toHaveBeenCalledWith(
      '[ErrorBoundary:test]',
      expect.any(Error),
      expect.any(String)
    );
  });

  it('reset restores the child when Try again is clicked', () => {
    function Harness(): ReactNode {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <>
          <button type="button" data-testid="toggle" onClick={() => setShouldThrow(false)}>
            Toggle
          </button>
          <ErrorBoundary cloudwatchKey="test">
            <ThrowingChild shouldThrow={shouldThrow} />
          </ErrorBoundary>
        </>
      );
    }

    render(<Harness />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    // Batch both events in a single act() so React processes reset + shouldThrow=false
    // together. Without act batching, reset causes a synchronous re-render where
    // shouldThrow is still true → child re-throws → boundary re-catches before toggle fires.
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
      fireEvent.click(screen.getByTestId('toggle'));
    });
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('ErrorBoundary - custom fallback', () => {
  beforeEach(() => {
    suppressErrorOutput();
    vi.clearAllMocks();
  });

  it('renders a custom ReactNode fallback', () => {
    render(
      <ErrorBoundary cloudwatchKey="test" fallback={<div data-testid="custom-fb" />}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('custom-fb')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('invokes a render-function fallback with error and reset', () => {
    const fallback = vi.fn((_error: Error, _reset: () => void) => <div data-testid="fn-fb" />);

    render(
      <ErrorBoundary cloudwatchKey="test" fallback={fallback}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>
    );

    // React 18 replays the error boundary render after componentDidCatch commits,
    // so the fallback may be called more than once. Assert on args, not call count.
    expect(fallback).toHaveBeenCalled();
    expect(fallback.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(fallback.mock.calls[0][1]).toEqual(expect.any(Function));
    expect(screen.getByTestId('fn-fb')).toBeInTheDocument();
  });

  it('passes a working reset function to the render-function fallback', () => {
    function Harness(): ReactNode {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <>
          <button type="button" data-testid="toggle" onClick={() => setShouldThrow(false)}>
            Toggle
          </button>
          <ErrorBoundary
            cloudwatchKey="test"
            fallback={(_error, reset) => {
              return <button type="button" data-testid="reset-fallback" onClick={reset} />;
            }}
          >
            <ThrowingChild shouldThrow={shouldThrow} />
          </ErrorBoundary>
        </>
      );
    }

    render(<Harness />);

    expect(screen.getByTestId('reset-fallback')).toBeInTheDocument();
    // Batch reset + toggle so both state updates are flushed together.
    act(() => {
      fireEvent.click(screen.getByTestId('reset-fallback'));
      fireEvent.click(screen.getByTestId('toggle'));
    });
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});

describe('ErrorBoundary - message mapping', () => {
  beforeEach(() => {
    suppressErrorOutput();
    vi.clearAllMocks();
  });

  it('shows the 5xx message for server errors', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={makeError('oops', { status: 500 })} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toHaveTextContent('trouble loading this page');
  });

  it('shows the 403 message for forbidden errors', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={makeError('oops', { status: 403 })} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toHaveTextContent("don't have access");
  });

  it('shows the 404 message for not found errors', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={makeError('oops', { status: 404 })} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toHaveTextContent('could not be found');
  });

  it('shows the network message for connection failures', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={makeError('network error')} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Check your connection');
  });

  it('shows the generic message for unknown errors', () => {
    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={new Error('unexpected')} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong');
  });
});

describe('ErrorBoundary - AC-001 contract and CloudWatch logging', () => {
  beforeEach(() => {
    suppressErrorOutput();
    vi.clearAllMocks();
  });

  it('does not show the boundary fallback when a component handles its API error inline', () => {
    render(
      <ErrorBoundary cloudwatchKey="page-test">
        <div data-testid="inline-error">API error handled inline</div>
      </ErrorBoundary>
    );

    expect(screen.getByTestId('inline-error')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('still catches a propagated API error as a legacy safety net', () => {
    render(
      <ErrorBoundary cloudwatchKey="page-test">
        <ThrowingChild shouldThrow error={makeError('API failed', { isApiError: true })} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('posts non-API errors to /api/errors with the cloudwatch key', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 200 }));

    render(
      <ErrorBoundary cloudwatchKey="billing-page">
        <ThrowingChild shouldThrow error={new Error('plain js error')} />
      </ErrorBoundary>
    );

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/errors',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.any(String),
      })
    );

    const requestInit = fetchSpy.mock.calls[0][1];
    expect(requestInit).toBeDefined();
    const payload = JSON.parse(String(requestInit?.body));
    expect(payload).toMatchObject({
      error: 'plain js error',
      boundary_key: 'billing-page',
    });
    expect(payload.stack).toEqual(expect.any(String));
  });

  it('does not post API errors below the 500 threshold', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 200 }));

    render(
      <ErrorBoundary cloudwatchKey="test">
        <ThrowingChild shouldThrow error={makeError('api', { isApiError: true })} />
      </ErrorBoundary>
    );

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
