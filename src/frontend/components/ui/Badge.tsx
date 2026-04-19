import React from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'error'
  | 'info'
  | 'neutral'
  | 'final'
  | 'edited'
  | 'stale';

export interface BadgeProps {
  variant: BadgeVariant;
  label?: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  'data-testid'?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-state-active text-white',
  warning: 'bg-state-warning text-white',
  error:   'bg-state-error text-white',
  info:    'bg-state-info text-white',
  neutral: 'bg-surface-subtle border border-border-default text-text-primary',
  final:   'bg-state-active text-white',
  edited:  'bg-state-info text-white',
  stale:   'bg-state-warning text-white',
};

export function Badge({
  variant,
  label,
  icon,
  children,
  className = '',
  'data-testid': testId,
}: BadgeProps) {
  const content = label ?? children;
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 px-3 py-1 rounded-md text-sm font-medium ${variantStyles[variant]} ${className}`}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {content}
    </span>
  );
}
