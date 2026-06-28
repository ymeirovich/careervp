'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/methods';
import type { SubscriptionResponse } from '../../lib/types';
import { Button } from '../ui/Button';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    heading: 'Billing Info',
    paymentMethod: 'Payment method',
    paymentMethodAria: (last4: string, brand: string) => `Payment method ending in ${last4}, ${brand}`,
    trustLine: 'Billing handled securely via Stripe.',
    noPaymentMethod: 'No payment method',
    manageBilling: 'Manage Billing',
    addPaymentMethod: 'Add Payment Method',
    loadingLabel: 'Loading billing info',
    errorFallback: 'Unable to load billing info. Please try again.',
    retry: 'Retry',
    portalErrorFallback: 'Unable to open billing portal. Please try again.',
  },
  he: {
    heading: 'פרטי חיוב',
    paymentMethod: 'אמצעי תשלום',
    paymentMethodAria: (last4: string, brand: string) => `אמצעי תשלום המסתיים ב-${last4}, ${brand}`,
    trustLine: 'החיוב מטופל בצורה מאובטחת באמצעות Stripe.',
    noPaymentMethod: 'אין אמצעי תשלום',
    manageBilling: 'ניהול חיוב',
    addPaymentMethod: 'הוספת אמצעי תשלום',
    loadingLabel: 'טוען פרטי חיוב',
    errorFallback: 'לא ניתן לטעון את פרטי החיוב. נסו שוב.',
    retry: 'נסו שוב',
    portalErrorFallback: 'לא ניתן לפתוח את פורטל החיוב. נסו שוב.',
  },
} satisfies Record<
  Locale,
  {
    heading: string;
    paymentMethod: string;
    paymentMethodAria: (last4: string, brand: string) => string;
    trustLine: string;
    noPaymentMethod: string;
    manageBilling: string;
    addPaymentMethod: string;
    loadingLabel: string;
    errorFallback: string;
    retry: string;
    portalErrorFallback: string;
  }
>;

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getLocale(): Locale {
  return isHebrewLocale() ? 'he' : 'en';
}

function normaliseBrand(brand: string | null | undefined): string {
  const raw = String(brand ?? '').trim().toLowerCase();
  if (!raw) return 'Card';
  if (raw === 'visa') return 'Visa';
  if (raw === 'mastercard') return 'Mastercard';
  if (raw === 'amex' || raw === 'american_express' || raw === 'american express') return 'Amex';
  if (raw === 'discover') return 'Discover';
  if (raw === 'diners' || raw === 'diners_club' || raw === 'diners club') return 'Diners Club';
  if (raw === 'jcb') return 'JCB';
  if (raw === 'unionpay') return 'UnionPay';
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

async function openPortal(): Promise<void> {
  const returnUrl = typeof window !== 'undefined' ? window.location.href : undefined;
  const result = await api.createBillingPortal(returnUrl ? { return_url: returnUrl } : undefined);
  const portalUrl = result?.portal_url;
  if (!portalUrl) throw new Error('Missing portal URL');
  window.open(portalUrl, '_blank', 'noopener,noreferrer');
}

export function BillingInfoCard() {
  const locale = getLocale();
  const copy = TEXT[locale];
  const rtl = locale === 'he';

  const [portalError, setPortalError] = useState<string | null>(null);
  const [isPortalLoading, setIsPortalLoading] = useState(false);

  const subscriptionQuery = useQuery<SubscriptionResponse, Error>({
    queryKey: ['user', 'subscription'],
    queryFn: () => api.getSubscription(),
    retry: false,
  });

  const paymentMethod = subscriptionQuery.data?.subscription?.payment_method ?? null;
  const last4 = paymentMethod?.last4 ? String(paymentMethod.last4) : null;
  const brand = useMemo(() => normaliseBrand(paymentMethod?.brand ?? null), [paymentMethod?.brand]);
  const hasPaymentMethod = Boolean(last4);

  if (subscriptionQuery.isLoading) {
    return (
      <section
        data-testid="billing-info-card"
        aria-label={copy.loadingLabel}
        dir={rtl ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <div data-testid="billing-info-skeleton" className="animate-pulse flex flex-col gap-4">
          <div className="h-5 w-28 rounded bg-surface-subtle" />
          <div className="h-4 w-72 rounded bg-surface-subtle" />
          <div className="h-4 w-56 rounded bg-surface-subtle" />
          <div className="h-10 w-40 rounded-xl bg-surface-subtle" />
        </div>
      </section>
    );
  }

  if (subscriptionQuery.isError) {
    return (
      <section
        data-testid="billing-info-card"
        aria-labelledby="billing-info-card-heading"
        dir={rtl ? 'rtl' : 'ltr'}
        className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
      >
        <h2 id="billing-info-card-heading" className="text-base font-bold text-text-primary">
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
      data-testid="billing-info-card"
      aria-labelledby="billing-info-card-heading"
      dir={rtl ? 'rtl' : 'ltr'}
      className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4"
    >
      <h2 id="billing-info-card-heading" className="text-base font-bold text-text-primary">
        {copy.heading}
      </h2>

      <div className="flex flex-col gap-2">
        {hasPaymentMethod ? (
          <p
            data-testid="billing-info-payment-method"
            aria-label={copy.paymentMethodAria(last4!, brand)}
            className="text-sm text-text-primary font-semibold"
          >
            {copy.paymentMethod} •••• {last4} ({brand})
          </p>
        ) : (
          <p data-testid="billing-info-empty" className="text-sm text-text-primary font-semibold">
            {copy.noPaymentMethod}
          </p>
        )}

        <p data-testid="billing-info-trust-line" className="text-sm text-text-secondary">
          {copy.trustLine}
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <Button
          type="button"
          variant="primary"
          size="md"
          isLoading={isPortalLoading}
          onClick={() => {
            setPortalError(null);
            setIsPortalLoading(true);
            void openPortal()
              .catch((err: unknown) => {
                const message = err instanceof Error ? err.message : null;
                setPortalError(message || copy.portalErrorFallback);
              })
              .finally(() => {
                setIsPortalLoading(false);
              });
          }}
        >
          {hasPaymentMethod ? copy.manageBilling : copy.addPaymentMethod}
        </Button>

        {portalError && (
          <p data-testid="billing-info-portal-error" className="text-sm text-state-error">
            {portalError}
          </p>
        )}
      </div>
    </section>
  );
}

