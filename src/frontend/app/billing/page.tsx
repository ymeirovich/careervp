'use client';

import React from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { BillingInfoCard } from '../../components/billing/BillingInfoCard';
import { PlansSection } from '../../components/billing/PlansSection';
import { SubscriptionCard } from '../../components/billing/SubscriptionCard';
import { UsageCard } from '../../components/billing/UsageCard';

function BillingContent() {
  return (
    <div className="flex flex-col gap-8 max-w-2xl" data-testid="billing-page">
      <h1 className="text-2xl font-bold text-text-primary">Billing & Plan</h1>

      <SubscriptionCard />

      <BillingInfoCard />

      <UsageCard />

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
