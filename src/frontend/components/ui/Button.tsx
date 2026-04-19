import React from 'react';
import { Spinner } from './Spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:     'bg-primary-action text-white hover:opacity-90 font-bold',
  secondary:   'bg-surface-subtle border border-border-default text-text-primary hover:bg-surface-selected font-medium',
  ghost:       'text-primary-action hover:underline font-normal bg-transparent',
  destructive: 'bg-state-error text-white hover:opacity-90 font-bold',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm rounded-md gap-1.5',
  md: 'px-4 py-2 text-base rounded-xl gap-2',
  lg: 'px-5 py-2.5 text-base rounded-xl gap-2',
};

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const isDisabled = disabled || isLoading;
  return (
    <button
      disabled={isDisabled}
      aria-busy={isLoading || undefined}
      className={`
        inline-flex items-center justify-center transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `.trim()}
      {...props}
    >
      {isLoading && <Spinner size="sm" aria-label="" />}
      {children}
    </button>
  );
}
