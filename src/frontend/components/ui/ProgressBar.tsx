import React from 'react';

export interface ProgressBarProps {
  value: number;
  label?: string;
  color?: 'primary' | 'warning' | 'error';
}

const colorMap = {
  primary: 'bg-primary-action',
  warning: 'bg-state-warning',
  error:   'bg-state-error',
};

export function ProgressBar({ value, label, color = 'primary' }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="w-full h-2 bg-surface-subtle rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${colorMap[color]}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {label && <span className="sr-only">{label}: {clamped}%</span>}
    </div>
  );
}
