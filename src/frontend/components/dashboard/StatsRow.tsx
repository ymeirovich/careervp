import React from 'react';

interface StatsRowProps {
  plan: string;
  creditsUsed: number;
  creditsTotal: number;
  isActive: boolean;
  isLoading?: boolean;
}

interface StatsPillProps {
  label: string;
  value: React.ReactNode;
}

interface StatsSkeletonPillProps {
  skeletonWidthClassName: string;
}

function StatsPill({ label, value }: StatsPillProps) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border-default bg-surface-subtle px-4 py-3">
      <span className="text-base font-medium text-text-primary">{label}</span>
      <span className="text-base font-medium text-text-primary">{value}</span>
    </div>
  );
}

function StatsSkeletonPill({ skeletonWidthClassName }: StatsSkeletonPillProps) {
  return (
    <div
      className="flex items-center gap-2 rounded-xl border border-border-default bg-surface-subtle px-4 py-3"
      data-testid="stats-pill-skeleton"
      aria-hidden="true"
    >
      <span className="h-5 w-16 animate-pulse rounded-xl bg-border-default/70" />
      <span className={`h-5 animate-pulse rounded-xl bg-border-default/70 ${skeletonWidthClassName}`} />
    </div>
  );
}

function getStatsRowCopy() {
  const isHebrew = typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');

  if (isHebrew) {
    return {
      planLabel: 'תוכנית:',
      creditsLabel: 'יתרת קרדיטים:',
      statusLabel: 'סטטוס:',
      activeLabel: 'פעיל',
      inactiveLabel: 'לא פעיל',
    };
  }

  return {
    planLabel: 'Plan:',
    creditsLabel: 'Credits Remaining:',
    statusLabel: 'Status:',
    activeLabel: 'Active',
    inactiveLabel: 'Inactive',
  };
}

export function StatsRow({ plan, creditsUsed, creditsTotal, isActive, isLoading = false }: StatsRowProps) {
  const copy = getStatsRowCopy();

  if (isLoading) {
    return (
      <div className="flex items-center gap-6">
        <StatsSkeletonPill skeletonWidthClassName="w-24" />
        <StatsSkeletonPill skeletonWidthClassName="w-28" />
        <StatsSkeletonPill skeletonWidthClassName="w-20" />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-6">
      <StatsPill label={copy.planLabel} value={plan} />

      <StatsPill label={copy.creditsLabel} value={`${creditsUsed} / ${creditsTotal}`} />

      <StatsPill
        label={copy.statusLabel}
        value={
          <span className="flex items-center gap-2 text-base font-medium text-text-primary">
            {isActive ? copy.activeLabel : copy.inactiveLabel}
            <span
              className={`h-2 w-2 rounded-full ${isActive ? 'bg-state-active' : 'bg-text-muted'}`}
              aria-hidden="true"
            />
          </span>
        }
      />
    </div>
  );
}
