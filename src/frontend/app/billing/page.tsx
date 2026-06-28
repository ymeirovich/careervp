'use client';

import React from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { BillingInfoCard } from '../../components/billing/BillingInfoCard';
import { PlansSection } from '../../components/billing/PlansSection';
import { SubscriptionCard } from '../../components/billing/SubscriptionCard';
import { UsageCard } from '../../components/billing/UsageCard';
import { Spinner } from '../../components/ui/Spinner';
import { useUserContext } from '../../hooks/useUserContext';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    title: 'Billing',
    loadingLabel: 'Loading billing info…',
  },
  he: {
    title: 'חיוב',
    loadingLabel: 'טוען פרטי חיוב…',
  },
} satisfies Record<Locale, { title: string; loadingLabel: string }>;

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getLocale(): Locale {
  return isHebrewLocale() ? 'he' : 'en';
}

function BillingContent() {
  const { isLoading } = useUserContext();
  const locale = getLocale();
  const copy = TEXT[locale];

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center" data-testid="billing-page-loading">
        <Spinner size="lg" aria-label={copy.loadingLabel} />
      </div>
    );
  }

  return (
    <div className="flex max-w-5xl flex-col gap-8" data-testid="billing-page" dir={locale === 'he' ? 'rtl' : 'ltr'}>
      <h1 className="text-2xl font-bold text-text-primary">{copy.title}</h1>

      <div className="flex max-w-2xl flex-col gap-6" data-testid="billing-overview-cards">
        <SubscriptionCard />

        <UsageCard />

        <BillingInfoCard />
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
