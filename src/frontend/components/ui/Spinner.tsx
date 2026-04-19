import React from 'react';

export type SpinnerSize = 'sm' | 'md' | 'lg';

export interface SpinnerProps {
  size?: SpinnerSize;
  'aria-label'?: string;
  className?: string;
}

const sizeMap: Record<SpinnerSize, string> = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-7 w-7',
};

export function Spinner({ size = 'md', 'aria-label': ariaLabel = 'Loading…', className = '' }: SpinnerProps) {
  return (
    <span
      data-testid="spinner"
      role="status"
      aria-label={ariaLabel || undefined}
      aria-live="polite"
      className={`inline-flex items-center justify-center ${className}`}
    >
      <svg
        className={`animate-spin text-text-muted ${sizeMap[size]}`}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
    </span>
  );
}
