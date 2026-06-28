'use client';

import React from 'react';
import { PlanCard } from './PlanCard';
import { useUserContext } from '../../hooks/useUserContext';
import { apiClient } from '../../api/client';

type Locale = 'en' | 'he';
type PlanKey = 'monthly' | '3month' | '6month';

const TEXT = {
  en: {
    heading: 'Choose Your Plan',
    plans: {
      monthly: { displayName: 'Monthly', billingPeriodLabel: 'Billed monthly' },
      '3month': { displayName: '3-Month', billingPeriodLabel: 'Billed $75 every 3 months' },
      '6month': { displayName: '6-Month', billingPeriodLabel: 'Billed $120 every 6 months' },
    },
    questions: 'Questions?',
    contactUs: 'Contact us',
  },
  he: {
    heading: 'בחרו את התוכנית שלכם',
    plans: {
      monthly: { displayName: 'חודשי', billingPeriodLabel: 'חיוב חודשי' },
      '3month': { displayName: 'ל-3 חודשים', billingPeriodLabel: 'חיוב בסך $75 כל 3 חודשים' },
      '6month': { displayName: 'ל-6 חודשים', billingPeriodLabel: 'חיוב בסך $120 כל 6 חודשים' },
    },
    questions: 'שאלות?',
    contactUs: 'צרו קשר',
  },
} satisfies Record<
  Locale,
  {
    heading: string;
    plans: Record<PlanKey, { displayName: string; billingPeriodLabel: string }>;
    questions: string;
    contactUs: string;
  }
>;

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getLocale(): Locale {
  return isHebrewLocale() ? 'he' : 'en';
}

function normalisePlanKey(value: unknown): PlanKey | null {
  if (!value) return null;
  const raw = String(value).trim().toLowerCase();
  if (raw === 'monthly') return 'monthly';
  if (raw === '3month') return '3month';
  if (raw === '6month') return '6month';
  return null;
}

type CheckoutResponse = { checkout_url?: string };

export function PlansSection() {
  const { subscription } = useUserContext();
  const locale = getLocale();
  const copy = TEXT[locale];

  const currentPlanKey = normalisePlanKey(subscription?.subscription?.plan_type as unknown);

  const onChoosePlan = async (planKey: string): Promise<void> => {
    const resolvedKey = normalisePlanKey(planKey);
    if (!resolvedKey) return;
    if (typeof window === 'undefined') return;

    try {
      const returnBase = `${window.location.origin}/billing`;
      const response = await apiClient.post<CheckoutResponse>('/billing/checkout', {
        plan: resolvedKey,
        success_url: `${returnBase}?checkout=success`,
        cancel_url: `${returnBase}?checkout=cancel`,
      });

      const checkoutUrl = response.data?.checkout_url;
      if (checkoutUrl) {
        window.location.href = checkoutUrl;
      }
    } catch (err) {
      // No toast UX for v1 — keep this non-blocking for the page
      console.error('Failed to create checkout session', err);
    }
  };

  return (
    <section
      id="plans"
      data-testid="plans-section"
      aria-labelledby="plans-section-heading"
      dir={locale === 'he' ? 'rtl' : 'ltr'}
      className="flex flex-col gap-6 scroll-mt-24"
    >
      <h2 id="plans-section-heading" className="text-base font-bold text-text-primary">
        {copy.heading}
      </h2>

      <div data-testid="plans-grid" className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div data-testid="plan-card-wrap-3month" className="order-1 md:order-2">
          <PlanCard
            planKey="3month"
            displayName={copy.plans['3month'].displayName}
            pricePerMonth={25}
            billingPeriodLabel={copy.plans['3month'].billingPeriodLabel}
            isCurrentPlan={currentPlanKey === '3month'}
            isRecommended
            onChoosePlan={onChoosePlan}
          />
        </div>

        <div data-testid="plan-card-wrap-monthly" className="order-2 md:order-1">
          <PlanCard
            planKey="monthly"
            displayName={copy.plans.monthly.displayName}
            pricePerMonth={30}
            billingPeriodLabel={copy.plans.monthly.billingPeriodLabel}
            isCurrentPlan={currentPlanKey === 'monthly'}
            isRecommended={false}
            onChoosePlan={onChoosePlan}
          />
        </div>

        <div data-testid="plan-card-wrap-6month" className="order-3 md:order-3">
          <PlanCard
            planKey="6month"
            displayName={copy.plans['6month'].displayName}
            pricePerMonth={20}
            billingPeriodLabel={copy.plans['6month'].billingPeriodLabel}
            isCurrentPlan={currentPlanKey === '6month'}
            isRecommended={false}
            onChoosePlan={onChoosePlan}
          />
        </div>
      </div>

      <p className="text-xs text-text-muted text-center">
        {copy.questions}{' '}
        <a href="mailto:support@careervp.com" className="underline">
          {copy.contactUs}
        </a>
      </p>
    </section>
  );
}
