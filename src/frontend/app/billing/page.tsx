'use client';

import React from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { PlansSection } from '../../components/billing/PlansSection';
import { SubscriptionCard } from '../../components/billing/SubscriptionCard';

function BillingContent() {
  return (
    <div className="flex flex-col gap-8 max-w-2xl" data-testid="billing-page">
      <h1 className="text-2xl font-bold text-text-primary">Billing & Plan</h1>

      <SubscriptionCard />

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
