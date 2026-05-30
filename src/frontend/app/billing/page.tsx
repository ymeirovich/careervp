'use client';

import React from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { useUserContext } from '../../hooks/useUserContext';
import { Spinner } from '../../components/ui/Spinner';
import { PlansSection } from '../../components/billing/PlansSection';

function BillingContent() {
  const { usage, subscription, isLoading } = useUserContext();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading billing info…" />
      </div>
    );
  }

  const trial = usage?.trial;
  const sub = subscription?.subscription;
  const hasActiveSubscription = subscription?.has_active_subscription ?? false;
  const isTrialActive = trial?.active ?? false;

  return (
    <div className="flex flex-col gap-8 max-w-2xl" data-testid="billing-page">
      <h1 className="text-2xl font-bold text-text-primary">Billing & Plan</h1>

      {/* Current plan card */}
      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4" data-testid="current-plan-card">
        <h2 className="text-base font-bold text-text-primary">Your Current Plan</h2>

        {isTrialActive && !hasActiveSubscription && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-state-info/10 text-state-info">Trial</span>
              <p className="text-sm text-text-primary font-medium">
                {trial?.days_remaining ?? 0} days remaining in your trial
              </p>
            </div>
            <p className="text-sm text-text-muted">Choose a plan below to continue after your trial ends.</p>
          </div>
        )}

        {hasActiveSubscription && sub && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-state-active/10 text-state-active capitalize">{sub.plan_type}</span>
              <p className="text-sm text-text-primary font-medium">
                {sub.plan_type === 'annual' ? '$16/month (billed annually)' : '$20/month'}
              </p>
            </div>
            <p className="text-sm text-text-muted capitalize">
              Status: {sub.status}
              {sub.current_period_end ? ` · Renews ${new Date(sub.current_period_end).toLocaleDateString()}` : ''}
            </p>
            <button
              disabled
              className="mt-2 w-fit rounded-md border border-border-default px-3 py-2 text-sm text-text-primary opacity-50 cursor-not-allowed"
              title="Coming soon"
            >
              Manage Subscription
            </button>
          </div>
        )}

        {!isTrialActive && !hasActiveSubscription && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-text-primary font-medium">Your trial has ended.</p>
            <p className="text-sm text-text-muted">Choose a plan below to continue using CareerVP.</p>
          </div>
        )}
      </div>

      <PlansSection />
    </div>
  );
}

export default function BillingPage() {
  return (
    <ErrorBoundary cloudwatchKey="billing-page">
      <BillingContent />
    </ErrorBoundary>
  );
}
