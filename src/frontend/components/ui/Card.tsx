import React from 'react';

export type CardVariant = 'default' | 'elevated' | 'bordered';

export interface CardProps {
  variant?: CardVariant;
  className?: string;
  children: React.ReactNode;
}

const variantStyles: Record<CardVariant, string> = {
  default:  'bg-card border border-border-default rounded-xl',
  elevated: 'bg-card rounded-xl shadow-md',
  bordered: 'bg-card border-2 border-border-strong rounded-xl',
};

export function Card({ variant = 'default', className = '', children }: CardProps) {
  return (
    <div className={`${variantStyles[variant]} ${className}`}>
      {children}
    </div>
  );
}
