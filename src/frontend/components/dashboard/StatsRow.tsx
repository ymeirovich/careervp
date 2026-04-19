import React from 'react';

interface StatsRowProps {
  plan: string;
  creditsUsed: number;
  creditsTotal: number;
  isActive: boolean;
}

export function StatsRow({ plan, creditsUsed, creditsTotal, isActive }: StatsRowProps) {
  return (
    <div className="flex items-center gap-6">
      <div className="flex items-center gap-2 bg-surface-subtle border border-border-default rounded-lg px-4 py-3">
        <span className="text-text-primary text-base font-medium">Plan:</span>
        <span className="text-text-primary text-base font-medium">{plan}</span>
      </div>

      <div className="flex items-center gap-2 bg-surface-subtle border border-border-default rounded-lg px-4 py-3">
        <span className="text-text-primary text-base font-medium">Credits Remaining:</span>
        <span className="text-text-primary text-base font-medium">
          {creditsUsed} / {creditsTotal}
        </span>
      </div>

      <div className="flex items-center gap-2 bg-surface-subtle border border-border-default rounded-lg px-4 py-3">
        <span className="text-text-primary text-base font-medium">Status:</span>
        <span className="flex items-center gap-2 text-text-primary text-base font-medium">
          {isActive ? 'Active' : 'Inactive'}
          <span
            className={`w-2 h-2 rounded-full ${isActive ? 'bg-state-active' : 'bg-text-muted'}`}
            aria-hidden="true"
          />
        </span>
      </div>
    </div>
  );
}
