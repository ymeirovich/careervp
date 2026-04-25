'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useDashboard } from '../../contexts/DashboardContext';
import { Button } from '../ui/Button';

interface UsageGateProps {
  children: React.ReactNode;
  action: 'new_application' | 'generate_module';
}

export function UsageGate({ children }: UsageGateProps) {
  const { hasActiveAccess, applicationsRemaining, usage } = useDashboard();
  const router = useRouter();

  if (!hasActiveAccess) {
    return (
      <div data-testid="usage-gate-no-subscription" className="flex flex-col items-center gap-3 py-4">
        <p className="text-text-muted text-sm text-center">
          Your free trial has ended. Upgrade to continue building your applications.
        </p>
        <Button variant="primary" size="sm" onClick={() => router.push('/billing')}>
          View Plans
        </Button>
      </div>
    );
  }

  const quotaOk = applicationsRemaining === null || applicationsRemaining > 0;
  if (!quotaOk) {
    const resetDate = usage?.trial?.ends_at
      ? new Date(usage.trial.ends_at).toLocaleDateString()
      : 'next month';
    return (
      <div data-testid="usage-gate-quota-exhausted" className="flex flex-col items-center gap-3 py-4">
        <p className="text-text-muted text-sm text-center">
          {`You've used all your applications this month. Your quota resets on ${resetDate}.`}
        </p>
        <Button variant="primary" size="sm" onClick={() => router.push('/billing')}>
          Upgrade Plan
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}
