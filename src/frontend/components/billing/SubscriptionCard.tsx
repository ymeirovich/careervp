'use client';

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/methods';
import type { SubscriptionDetails, SubscriptionResponse } from '../../lib/types';
import { Badge } from '../ui/Badge';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    heading: 'Current Subscription',
    active: 'Active',
    cancelling: 'Cancelling',
    trial: 'Trial',
    pastDue: 'Past Due',
    noActive: 'No active subscription',
    renews: 'Renews',
    activeUntil: 'Active until',
    nextCharge: 'Next charge',
    viewPlans: 'View Plans',
    resubscribe: 'Resubscribe',
    choosePlan: 'Choose a Plan',
    updatePayment: 'Update Payment',
    retry: 'Retry',
    errorFallback: 'Unable to load subscription. Please try again.',
    trialDaysRemaining: (days: number) => `${days} days remaining`,
    statusAria: (label: string) => `Subscription status: ${label}`,
    planPill: (planLabel: string) => `Pro ${planLabel}`,
  },
  he: {
    heading: 'המנוי הנוכחי',
    active: 'פעיל',
    cancelling: 'בביטול',
    trial: 'ניסיון',
    pastDue: 'באיחור תשלום',
    noActive: 'אין מנוי פעיל',
    renews: 'מתחדש',
    activeUntil: 'פעיל עד',
    nextCharge: 'חיוב הבא',
    viewPlans: 'צפייה בתוכניות',
    resubscribe: 'הירשמות מחדש',
    choosePlan: 'בחרו תוכנית',
    updatePayment: 'עדכון תשלום',
    retry: 'נסו שוב',
    errorFallback: 'לא ניתן לטעון את פרטי המנוי. נסו שוב.',
    trialDaysRemaining: (days: number) => `נותרו ${days} ימים`,
    statusAria: (label: string) => `סטטוס מנוי: ${label}`,
    planPill: (planLabel: string) => `Pro ${planLabel}`,
  },
} satisfies Record<
  Locale,
  {
    heading: string;
    active: string;
    cancelling: string;
    trial: string;
    pastDue: string;
    noActive: string;
    renews: string;
    activeUntil: string;
    nextCharge: string;
    viewPlans: string;
    resubscribe: string;
    choosePlan: string;
    updatePayment: string;
    retry: string;
    errorFallback: string;
    trialDaysRemaining: (days: number) => string;
    statusAria: (label: string) => string;
    planPill: (planLabel: string) => string;
  }
>;

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getLocale(): Locale {
  return isHebrewLocale() ? 'he' : 'en';
}

function normalisePlanType(planType: unknown): string {
  const raw = String(planType ?? '').trim().toLowerCase();
  if (raw === 'monthly') return 'Monthly';
  if (raw === '3month' || raw === 'quarterly') return '3-Month';
  if (raw === '6month') return '6-Month';
  if (raw === 'annual') return 'Annual';
  return raw ? raw : 'Plan';
}

function formatDate(dateValue: string | undefined, locale: Locale): string {
  if (!dateValue) return '';
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return dateValue;
  return date.toLocaleDateString(locale === 'he' ? 'he-IL' : undefined);
}

function formatCurrency(amount: number, locale: Locale): string {
  return new Intl.NumberFormat(locale === 'he' ? 'he-IL' : undefined, {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

type StatusView = {
  badgeLabel: string | null;
  badgeVariant: 'success' | 'warning' | 'info' | 'error';
  ctaLabel: string;
  subline: string | null;
};

function deriveStatusView(subscription: SubscriptionDetails | null, locale: Locale): StatusView {
  const copy = TEXT[locale];
  if (!subscription) {
    return {
      badgeLabel: null,
      badgeVariant: 'info',
      ctaLabel: copy.choosePlan,
      subline: copy.noActive,
    };
  }

  const status = subscription.status;
  const isCancelling = status === 'active' && subscription.cancel_at_period_end === true;

  if (isCancelling) {
    const until = formatDate(subscription.current_period_end, locale);
    return {
      badgeLabel: copy.cancelling,
      badgeVariant: 'warning',
      ctaLabel: copy.resubscribe,
      subline: until ? `${copy.activeUntil} ${until}` : copy.cancelling,
    };
  }

  if (status === 'active') {
    const renews = formatDate(subscription.current_period_end, locale);
    return {
      badgeLabel: copy.active,
      badgeVariant: 'success',
      ctaLabel: copy.viewPlans,
      subline: renews ? `${copy.renews} ${renews}` : null,
    };
  }

  if (status === 'trialing') {
    const days = subscription.trial_days_remaining ?? null;
    return {
      badgeLabel: copy.trial,
      badgeVariant: 'info',
      ctaLabel: copy.viewPlans,
      subline: typeof days === 'number' ? copy.trialDaysRemaining(days) : null,
    };
  }

  if (status === 'past_due') {
    return {
      badgeLabel: copy.pastDue,
      badgeVariant: 'error',
      ctaLabel: copy.updatePayment,
      subline: null,
    };
  }

  return {
    badgeLabel: null,
    badgeVariant: 'info',
    ctaLabel: copy.choosePlan,
    subline: copy.noActive,
  };
}

function scrollToPlans(): void {
  if (typeof document === 'undefined') return;
  const target = document.getElementById('plans');
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function SubscriptionCard() {
  const locale = getLocale();
  const copy = TEXT[locale];

  const subscriptionQuery = useQuery<SubscriptionResponse, Error>({
    queryKey: ['user', 'subscription'],
    queryFn: () => api.getSubscription(),
    retry: false,
  });

  const subscription = subscriptionQuery.data?.subscription ?? null;
  const view = useMemo(() => deriveStatusView(subscription, locale), [subscription, locale]);

  const planPill = subscription ? copy.planPill(normalisePlanType(subscription.plan_type)) : null;
  const nextCharge = subscription?.next_charge_amount ?? null;

  if (subscriptionQuery.isLoading) {
    return (
      <section
        data-testid="subscription-card"
        aria-labelledby="subscription-card-heading"
        dir={locale === 'he' ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <div data-testid="subscription-skeleton" className="animate-pulse flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="h-5 w-44 rounded bg-surface-subtle" />
            <div className="h-7 w-20 rounded-md bg-surface-subtle" />
          </div>
          <div className="h-4 w-36 rounded bg-surface-subtle" />
          <div className="h-4 w-52 rounded bg-surface-subtle" />
          <div className="h-10 w-full rounded-xl bg-surface-subtle" />
        </div>
      </section>
    );
  }

  if (subscriptionQuery.isError) {
    return (
      <section
        data-testid="subscription-card"
        aria-labelledby="subscription-card-heading"
        dir={locale === 'he' ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <h2 id="subscription-card-heading" className="text-base font-bold text-text-primary">
          {copy.heading}
        </h2>
        <div className="flex flex-col gap-4">
          <p className="text-base text-state-error">{subscriptionQuery.error?.message || copy.errorFallback}</p>
          <button
            type="button"
            onClick={() => {
              void subscriptionQuery.refetch();
            }}
            className="w-fit rounded-md border border-border-default bg-card px-4 py-2 text-sm font-semibold text-text-primary hover:bg-surface-subtle focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
          >
            {copy.retry}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section
      data-testid="subscription-card"
      aria-labelledby="subscription-card-heading"
      dir={locale === 'he' ? 'rtl' : 'ltr'}
      className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-4">
        <h2 id="subscription-card-heading" className="text-base font-bold text-text-primary">
          {copy.heading}
        </h2>

        {view.badgeLabel && (
          <span role="status" aria-label={copy.statusAria(view.badgeLabel)}>
            <Badge variant={view.badgeVariant} soft>
              {view.badgeLabel}
            </Badge>
          </span>
        )}
      </div>

      {planPill && (
        <div>
          <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-surface-subtle text-text-primary">
            {planPill}
          </span>
        </div>
      )}

      {view.subline && <p className="text-sm text-text-muted">{view.subline}</p>}

      {typeof nextCharge === 'number' && (
        <p className="text-sm text-text-muted">
          {copy.nextCharge}: <span className="text-text-primary font-semibold">{formatCurrency(nextCharge, locale)}</span>
        </p>
      )}

      <button
        type="button"
        onClick={() => scrollToPlans()}
        className="w-full rounded-xl bg-primary-action px-4 py-2 text-base font-bold text-white text-center hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
      >
        {view.ctaLabel}
      </button>
    </section>
  );
}

