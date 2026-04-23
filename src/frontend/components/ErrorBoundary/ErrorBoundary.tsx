'use client';

import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, info: ErrorInfo) => void;
  cloudwatchKey: string;
}

interface State {
  error: Error | null;
}

function getUserMessage(error: Error): string {
  const status = (error as { status?: number; statusCode?: number }).status
    ?? (error as { status?: number; statusCode?: number }).statusCode;
  if (status && status >= 500) return "We're having trouble loading this page. Please try again in a moment.";
  if (status === 403) return "You don't have access to this content.";
  if (status === 404) return 'This content could not be found.';
  const msg = error.message?.toLowerCase() ?? '';
  if (msg.includes('network') || msg.includes('fetch') || msg.includes('connection')) {
    return 'Check your connection and try again.';
  }
  return 'Something went wrong. Please refresh the page.';
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    const { cloudwatchKey, onError } = this.props;
    console.error(`[ErrorBoundary:${cloudwatchKey}]`, error, info.componentStack);
    onError?.(error, info);
    this.logToCloudWatch(error);
  }

  private logToCloudWatch(error: Error) {
    const status = (error as { status?: number; statusCode?: number }).status
      ?? (error as { status?: number; statusCode?: number }).statusCode;
    const isApiError = !!(error as { isApiError?: boolean }).isApiError;
    const shouldLog = (status && status >= 500) || !isApiError;
    if (!shouldLog) return;

    void fetch('/api/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: error.message,
        stack: error.stack,
        boundary_key: this.props.cloudwatchKey,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        url: typeof window !== 'undefined' ? window.location.href : '',
      }),
    }).catch(() => {});
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const { fallback } = this.props;
    if (typeof fallback === 'function') return fallback(error, this.reset);
    if (fallback) return fallback;

    return (
      <div role="alert" className="flex flex-col items-center justify-center py-12 text-center gap-3">
        <p className="text-text-muted text-base">{getUserMessage(error)}</p>
        <button
          onClick={this.reset}
          className="text-primary-action text-sm font-medium hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }
}
