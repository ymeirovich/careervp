'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { BaseCVsTable, type BaseCVListItem } from '../../components/BaseCVsTable';
import { ChooseBaseCVModal } from '../../components/ChooseBaseCVModal';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';

type Locale = 'en' | 'he';

const TEXT = {
  en: {
    allBaseCvs: 'All Base CVs',
    title: 'Base CVs',
    uploadNew: '+ Upload New CV',
  },
  he: {
    allBaseCvs: 'כל קורות החיים הבסיסיים',
    title: 'קורות חיים בסיסיים',
    uploadNew: '+ העלאת קורות חיים חדשים',
  },
} satisfies Record<Locale, { allBaseCvs: string; title: string; uploadNew: string }>;

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

function parseBaseCVs(data: unknown): BaseCVListItem[] {
  if (Array.isArray(data)) {
    return data.filter((item): item is BaseCVListItem => typeof item === 'object' && item !== null);
  }

  if (typeof data !== 'object' || data === null) return [];

  const payload = data as { cvs?: unknown };
  if (!Array.isArray(payload.cvs)) return [];

  return payload.cvs.filter((item): item is BaseCVListItem => typeof item === 'object' && item !== null);
}

async function getBaseCVs(): Promise<BaseCVListItem[]> {
  const response = await apiClient.get<unknown>('/users/me/cv');
  return parseBaseCVs(response.data);
}

function getFileExtension(fileName: string): 'pdf' | 'docx' | 'txt' | undefined {
  const extension = fileName.split('.').pop()?.toLowerCase();
  if (extension === 'pdf' || extension === 'docx' || extension === 'txt') return extension;
  return undefined;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read CV file'));
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      resolve(result.split(',')[1] ?? result);
    };
    reader.readAsDataURL(file);
  });
}

async function uploadBaseCV(file: File): Promise<void> {
  const fileContent = await fileToBase64(file);
  const fileType = getFileExtension(file.name);

  await apiClient.post('/users/me/cv', {
    cv_content: fileContent,
    file_name: file.name,
    ...(fileType ? { file_type: fileType } : {}),
  });
}

export function CVCenterContent() {
  const locale = detectLocale();
  const copy = TEXT[locale];
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  useEffect(() => {
    if (locale === 'he') {
      document.documentElement.lang = 'he';
    }
  }, [locale]);

  const {
    data: cvs,
    isLoading,
    error,
    refetch,
  } = useQuery<BaseCVListItem[], Error>({
    queryKey: ['baseCvs', 'list'],
    queryFn: getBaseCVs,
    retry: false,
  });

  const handleUpload = async (file: File) => {
    await uploadBaseCV(file);
    setIsUploadModalOpen(false);
    await refetch();
  };

  return (
    <div data-testid="cv-center-page" dir={locale === 'he' ? 'rtl' : 'ltr'}>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4" data-testid="page-header">
          <h1 className="text-2xl font-bold text-text-primary" data-testid="page-header-title">
            {copy.title}
          </h1>
        </div>

        <section className="rounded-xl border border-border-default bg-card p-6" data-testid="base-cvs-card">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-base font-semibold text-text-muted" data-testid="base-cvs-card-heading">
              {copy.allBaseCvs}
            </h2>
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(true)}
              className="inline-flex items-center justify-center rounded-md bg-primary-action px-4 py-2 text-sm font-bold text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
            >
              {copy.uploadNew}
            </button>
          </div>

          <BaseCVsTable
            cvs={cvs ?? []}
            isLoading={isLoading}
            error={error ? error.message : null}
            onRetry={() => {
              void refetch();
            }}
            onUploadNew={() => setIsUploadModalOpen(true)}
          />
        </section>
      </div>

      <ChooseBaseCVModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        showChoices={false}
        onUpload={handleUpload}
      />
    </div>
  );
}

export default function CVCenterPage() {
  return (
    <ErrorBoundary cloudwatchKey="cv-center-page">
      <CVCenterContent />
    </ErrorBoundary>
  );
}
