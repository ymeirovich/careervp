'use client';

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/methods';
import type { SubscriptionResponse } from '../../lib/types';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    heading: 'Usage',
    unlimited: 'Unlimited credits',
    upgradeLink: 'Upgrade subscription to save money',
    loadingLabel: 'Loading usage',
    errorFallback: 'Failed to load usage',
    retry: 'Retry',
    trialLabel: (used: number, limit: number) => `${used} of ${limit} applications used`,
  },
  he: {
    heading: 'שימוש',
    unlimited: 'קרדיטים ללא הגבלה',
    upgradeLink: 'שדרגו את המנוי כדי לחסוך כסף',
    loadingLabel: 'טוען שימוש',
    errorFallback: 'נכשל בטעינת שימוש',
    retry: 'נסה שוב',
    trialLabel: (used: number, limit: number) => `${used} מתוך ${limit} בקשות נוצלו`,
  },
} satisfies Record<
  Locale,
  {
    heading: string;
    unlimited: string;
    upgradeLink: string;
    loadingLabel: string;
    errorFallback: string;
    retry: string;
    trialLabel: (used: number, limit: number) => string;
  }
>;

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getLocale(): Locale {
  return isHebrewLocale() ? 'he' : 'en';
}

type UsageApiResponse = {
  credits_used?: number;
  credits_total?: number;
  trial?: {
    active?: boolean;
    applications_used?: number;
    applications_limit?: number;
  };
  applications?: {
    used?: number;
    remaining?: number;
  };
};

function scrollToPlans(): void {
  if (typeof document === 'undefined') return;
  const target = document.getElementById('plans');
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function normaliseTrialUsage(usage: UsageApiResponse | null): { isTrial: boolean; used: number; limit: number } {
  const isTrial = usage?.trial?.active === true;

  const used =
    (usage?.trial?.applications_used ??
      usage?.applications?.used ??
      usage?.credits_used ??
      0) || 0;

  const limitFromSpec = usage?.trial?.applications_limit;
  const limitFromRemaining =
    typeof usage?.applications?.remaining === 'number' ? used + usage.applications.remaining : null;

  const limit =
    (typeof limitFromSpec === 'number' && limitFromSpec > 0
      ? limitFromSpec
      : typeof limitFromRemaining === 'number' && limitFromRemaining > 0
      ? limitFromRemaining
      : 3) || 3;

  return { isTrial, used, limit };
}

function UsageProgressBar({
  used,
  limit,
  rtl,
}: {
  used: number;
  limit: number;
  rtl: boolean;
}) {
  const safeLimit = limit > 0 ? limit : 1;
  const ratio = Math.min(1, Math.max(0, used / safeLimit));
  const percent = Math.round(ratio * 100);

  return (
    <div
      data-testid="usage-progress"
      role="progressbar"
      aria-valuenow={used}
      aria-valuemin={0}
      aria-valuemax={safeLimit}
      className="w-full"
    >
      <div className="w-full h-2 bg-surface-subtle rounded-full overflow-hidden">
        <div
          data-testid="usage-progress-fill"
          className={`h-full rounded-full transition-all duration-300 bg-primary-action ${rtl ? 'ml-auto' : ''}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export function UsageCard() {
  const locale = getLocale();
  const copy = TEXT[locale];

  const usageQuery = useQuery<UsageApiResponse, Error>({
    queryKey: ['user', 'usage'],
    queryFn: async () => (await api.getUsage()) as unknown as UsageApiResponse,
    retry: false,
  });

  const subscriptionQuery = useQuery<SubscriptionResponse, Error>({
    queryKey: ['user', 'subscription'],
    queryFn: () => api.getSubscription(),
    retry: false,
  });

  const isLoading = usageQuery.isLoading || subscriptionQuery.isLoading;

  const trialUsage = useMemo(() => normaliseTrialUsage(usageQuery.data ?? null), [usageQuery.data]);
  const isPaid = subscriptionQuery.data?.has_active_subscription === true;
  const isTrial = !isPaid && trialUsage.isTrial;
  const rtl = locale === 'he';

  if (isLoading) {
    return (
      <section
        data-testid="usage-card"
        aria-label={copy.loadingLabel}
        dir={rtl ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <div data-testid="usage-skeleton" className="animate-pulse flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="h-5 w-20 rounded bg-surface-subtle" />
            <div className="h-4 w-52 rounded bg-surface-subtle" />
          </div>
          <div className="h-4 w-44 rounded bg-surface-subtle" />
          <div className="h-2 w-full rounded-full bg-surface-subtle" />
        </div>
      </section>
    );
  }

  if (usageQuery.isError || subscriptionQuery.isError) {
    const message =
      (usageQuery.isError ? usageQuery.error?.message : null) ??
      (subscriptionQuery.isError ? subscriptionQuery.error?.message : null) ??
      copy.errorFallback;

    return (
      <section
        data-testid="usage-card"
        aria-labelledby="usage-card-heading"
        dir={rtl ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <h2 id="usage-card-heading" className="text-base font-bold text-text-primary">
          {copy.heading}
        </h2>
        <div className="flex flex-col gap-4">
          <p className="text-base text-state-error">{message}</p>
          <button
            type="button"
            onClick={() => {
              void usageQuery.refetch();
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
      data-testid="usage-card"
      aria-labelledby="usage-card-heading"
      dir={rtl ? 'rtl' : 'ltr'}
      className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-4">
        <h2 id="usage-card-heading" className="text-base font-bold text-text-primary">
          {copy.heading}
        </h2>

        <a
          href="#plans"
          data-testid="usage-upgrade-link"
          className="text-sm font-semibold text-primary-action hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2 rounded"
          onClick={(e) => {
            e.preventDefault();
            scrollToPlans();
          }}
        >
          {copy.upgradeLink}
        </a>
      </div>

      {isPaid ? (
        <div data-testid="usage-unlimited" aria-label={copy.unlimited} className="text-sm text-text-primary font-semibold">
          {copy.unlimited}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p data-testid="usage-trial-label" className="text-sm text-text-primary font-semibold">
            {copy.trialLabel(trialUsage.used, trialUsage.limit)}
          </p>

          {(isTrial || !trialUsage.isTrial) && (
            <UsageProgressBar used={trialUsage.used} limit={trialUsage.limit} rtl={rtl} />
          )}
        </div>
      )}
    </section>
  );
}

