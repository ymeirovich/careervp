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
  soft?: boolean;
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

const softVariantStyles: Record<BadgeVariant, string> = {
  success: 'bg-green-50 text-green-700 border border-green-200',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200',
  error:   'bg-state-error text-white',
  info:    'bg-blue-50 text-blue-700 border border-blue-200',
  neutral: 'bg-gray-50 text-gray-700 border border-gray-200',
  final:   'bg-green-50 text-green-700 border border-green-200',
  edited:  'bg-green-50 text-green-700 border border-green-200',
  stale:   'bg-amber-50 text-amber-700 border border-amber-200',
};

export function Badge({
  variant,
  soft = false,
  label,
  icon,
  children,
  className = '',
  'data-testid': testId,
}: BadgeProps) {
  const content = label ?? children;
  const styleClasses = soft ? softVariantStyles[variant] : variantStyles[variant];
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 px-3 py-1 rounded-md text-sm font-medium ${styleClasses} ${className}`}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {content}
    </span>
  );
}
