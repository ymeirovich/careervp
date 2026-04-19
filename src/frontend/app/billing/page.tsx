'use client';

import React from 'react';

// TODO: Wire to useSubscription hook (spec-03)

export default function BillingPage() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="font-bold text-text-primary text-2xl">Billing</h2>
      {/* TODO: Subscription plan display, upgrade/cancel, invoice history */}
      <p className="text-text-muted">Manage your subscription and billing here.</p>
    </div>
  );
}
