'use client';

import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CoverLettersListTable } from '../../components/CoverLettersListTable/CoverLettersListTable';
import { api } from '../../api/methods';
import type { CoverLetterListItem } from '../../lib/types';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    title: 'Cover Letters',
    subtitle: 'All Cover Letters',
  },
  he: {
    title: 'מכתבי פנייה',
    subtitle: 'כל מכתבי הפנייה',
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

export default function CoverLettersPage() {
  const locale = detectLocale();
  const copy = TEXT[locale];

  useEffect(() => {
    if (locale === 'he') {
      document.documentElement.lang = 'he';
    }
  }, [locale]);

  const {
    data: coverLetters,
    isLoading,
    error,
    refetch,
  } = useQuery<CoverLetterListItem[], Error>({
    queryKey: ['coverLetters', 'list'],
    queryFn: () => api.getCoverLettersList(),
    retry: false,
  });

  return (
    <div data-testid="cover-letters-page" dir={locale === 'he' ? 'rtl' : 'ltr'}>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4" data-testid="page-header">
          <div>
            <h1 className="font-bold text-text-primary text-2xl" data-testid="page-header-title">
              {copy.title}
            </h1>
            <p className="text-text-muted text-base mt-1" data-testid="page-header-subheading">
              {copy.subtitle}
            </p>
          </div>
        </div>

        <CoverLettersListTable
          coverLetters={coverLetters ?? []}
          isLoading={isLoading}
          error={error ? error.message : null}
          onRetry={() => {
            void refetch();
          }}
        />
      </div>
    </div>
  );
}
