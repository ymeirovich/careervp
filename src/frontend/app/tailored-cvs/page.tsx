'use client';

import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TailoredCVsListTable } from '../../components/TailoredCVsListTable/TailoredCVsListTable';
import { api } from '../../api/methods';
import type { TailoredCvListItem } from '../../lib/types';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    title: 'Tailored CVs',
    subtitle: 'All Tailored CVs',
  },
  he: {
    title: 'קורות חיים מותאמים',
    subtitle: 'כל קורות החיים המותאמים',
  },
} satisfies Record<Locale, { title: string; subtitle: string }>;

function detectLocale(): Locale {
  if (typeof window !== 'undefined') {
    const locale = new URLSearchParams(window.location.search).get('locale');
    if (locale?.toLowerCase().startsWith('he')) return 'he';
  }

  if (typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he')) {
    return 'he';
  }

  return 'en';
}

export default function TailoredCVsPage() {
  const locale = detectLocale();
  const copy = TEXT[locale];

  useEffect(() => {
    if (locale === 'he') {
      document.documentElement.lang = 'he';
    }
  }, [locale]);

  const {
    data: tailoredCvs,
    isLoading,
    error,
    refetch,
  } = useQuery<TailoredCvListItem[], Error>({
    queryKey: ['tailoredCvs', 'list'],
    queryFn: () => api.getTailoredCvsList(),
    retry: false,
  });

  return (
    <div data-testid="tailored-cvs-page" dir={locale === 'he' ? 'rtl' : 'ltr'}>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4" data-testid="page-header">
          <div>
            <h1 className="font-bold text-text-primary text-2xl" data-testid="page-header-title">
              {copy.title}
            </h1>
          </div>
        </div>

        <div className="rounded-xl border border-border-default bg-card p-6 flex flex-col gap-4" data-testid="tailored-cvs-card">
          <p className="text-text-muted text-base" data-testid="page-header-subheading">
            {copy.subtitle}
          </p>

          <TailoredCVsListTable
            tailoredCvs={tailoredCvs ?? []}
            isLoading={isLoading}
            error={error ? error.message : null}
            onRetry={() => {
              void refetch();
            }}
          />
        </div>
      </div>
    </div>
  );
}

