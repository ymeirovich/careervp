'use client';

import React from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { useUserContext } from '../../hooks/useUserContext';
import { Spinner } from '../../components/ui/Spinner';

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
              <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-state-success/10 text-state-success capitalize">{sub.plan_type}</span>
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

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
          <h3 className="text-base font-bold text-text-primary">Monthly</h3>
          <div className="flex flex-col gap-1">
            <p className="text-2xl font-bold text-text-primary">$20<span className="text-sm font-normal text-text-muted">/month</span></p>
            <p className="text-xs text-text-muted">Billed monthly</p>
          </div>
          <ul className="flex flex-col gap-2 text-sm text-text-primary">
            <li>✓ Unlimited applications</li>
            <li>✓ All AI features</li>
            <li>✓ Cancel anytime</li>
          </ul>
          <a
            href="/billing/checkout?plan=monthly"
            className="rounded-md bg-brand-primary px-4 py-2 text-sm font-bold text-white text-center hover:opacity-90"
          >
            Get Monthly
          </a>
        </div>

        <div className="rounded-md border-2 border-brand-primary bg-card p-6 flex flex-col gap-4 relative">
          <div className="absolute -top-3 left-4">
            <span className="inline-flex px-2 py-0.5 rounded text-xs font-bold bg-brand-primary text-white">Save 20%</span>
          </div>
          <h3 className="text-base font-bold text-text-primary">Annual</h3>
          <div className="flex flex-col gap-1">
            <p className="text-2xl font-bold text-text-primary">$16<span className="text-sm font-normal text-text-muted">/month</span></p>
            <p className="text-xs text-text-muted">Billed $192/year</p>
          </div>
          <ul className="flex flex-col gap-2 text-sm text-text-primary">
            <li>✓ Unlimited applications</li>
            <li>✓ All AI features</li>
            <li>✓ Best value</li>
          </ul>
          <a
            href="/billing/checkout?plan=annual"
            className="rounded-md bg-brand-primary px-4 py-2 text-sm font-bold text-white text-center hover:opacity-90"
          >
            Get Annual
          </a>
        </div>
      </div>

      <p className="text-xs text-text-muted text-center">
        Questions? <a href="mailto:support@careervp.com" className="underline">Contact us</a>
      </p>
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
