'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ChooseBaseCVModal,
  type ChooseBaseCVItem,
  type ChooseBaseCVKind,
} from '../../../components/ChooseBaseCVModal';
import { Button } from '../../../components/ui/Button';
import { useJobs } from '../../../hooks/useJobs';
import { api } from '../../../api/methods';

type Locale = 'en' | 'he';

type Copy = {
  back: string;
  title: string;
  errorFallback: string;
  titleLabel: string;
  companyLabel: string;
  descriptionLabel: string;
  descriptionPlaceholder: string;
  urlLabel: string;
  baseCvHeading: string;
  baseCvPlaceholder: string;
  baseCvKindUploaded: string;
  baseCvKindGenerated: string;
  change: string;
  cancel: string;
  create: string;
  creating: string;
  analyzing: string;
};

const TEXT: Record<Locale, Copy> = {
  en: {
    back: '← Back',
    baseCvHeading: 'Base CV',
    baseCvKindGenerated: 'Generated CV',
    baseCvKindUploaded: 'Uploaded CV',
    baseCvPlaceholder: 'No CV selected',
    cancel: 'Cancel',
    change: 'Change',
    companyLabel: 'Company Name',
    create: 'Create Application',
    creating: 'Creating...',
    analyzing: 'Analyzing application...',
    descriptionLabel: 'Job Description',
    descriptionPlaceholder: 'Paste the full job posting here',
    errorFallback: 'Failed to create application',
    title: 'New Application',
    titleLabel: 'Job Title',
    urlLabel: 'Job URL',
  },
  he: {
    back: '← חזרה',
    baseCvHeading: 'קורות חיים בסיסיים',
    baseCvKindGenerated: 'קורות חיים שנוצרו',
    baseCvKindUploaded: 'קורות חיים שהועלו',
    baseCvPlaceholder: 'לא נבחרו קורות חיים',
    cancel: 'ביטול',
    change: 'שנה',
    companyLabel: 'שם החברה',
    create: 'צור הגשה',
    creating: 'יוצר...',
    analyzing: 'מנתח הגשה...',
    descriptionLabel: 'תיאור המשרה',
    descriptionPlaceholder: 'הדבק כאן את פרסום המשרה המלא',
    errorFallback: 'יצירת ההגשה נכשלה',
    title: 'הגשה חדשה',
    titleLabel: 'שם המשרה',
    urlLabel: 'קישור למשרה',
  },
};

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

function getCvName(cv: ChooseBaseCVItem | null): string | null {
  if (!cv) return null;
  return cv.file_name ?? cv.full_name ?? cv.name ?? cv.title ?? cv.cv_id ?? cv.id ?? null;
}

export default function NewApplicationPage() {
  const router = useRouter();
  const { createJob, isCreating } = useJobs();
  const locale = detectLocale();
  const copy = TEXT[locale];

  const [title, setTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [description, setDescription] = useState('');
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isCvModalOpen, setIsCvModalOpen] = useState(false);
  const [selectedCv, setSelectedCv] = useState<{ cv: ChooseBaseCVItem; kind: ChooseBaseCVKind } | null>(null);

  useEffect(() => {
    if (locale === 'he') {
      document.documentElement.lang = 'he';
    }
  }, [locale]);

  const selectedCvName = getCvName(selectedCv?.cv ?? null);
  const isBusy = isCreating || isAnalyzing;
  const isFormComplete = useMemo(
    () => title.trim().length > 0 && companyName.trim().length > 0 && description.trim().length > 0,
    [companyName, description, title],
  );

  const clearError = () => {
    if (error) setError(null);
  };

  const goDashboard = () => {
    router.push('/dashboard');
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isFormComplete || isBusy) return;

    setError(null);

    try {
      const job = await createJob({
        title: title.trim(),
        company_name: companyName.trim(),
        description: description.trim(),
        url: url.trim() || undefined,
      });

      const jobId = job.job_id || job.id;

      // Attempt to trigger gap analysis immediately. Prefer the CV the user
      // selected in this form; fall back to their account's default CV.
      const cvId = selectedCv?.cv?.cv_id ?? (await api.getCV().catch(() => null))?.cv_id;

      if (cvId && jobId) {
        setIsAnalyzing(true);
        try {
          await api.generateGapQuestions({ job_id: jobId, cv_id: cvId });
          router.push(`/applications/${jobId}/gap-analysis`);
          return;
        } catch {
          // Non-fatal — questions can be generated later from the hub.
        } finally {
          setIsAnalyzing(false);
        }
      }

      router.push(`/applications/${jobId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.errorFallback);
    }
  };

  return (
    <div
      className="mx-auto flex w-full max-w-3xl flex-col gap-5"
      dir={locale === 'he' ? 'rtl' : 'ltr'}
      data-testid="new-application-page"
    >
      <button
        type="button"
        onClick={goDashboard}
        className="w-fit text-base font-medium text-primary-action hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action"
      >
        {copy.back}
      </button>

      <section className="rounded-lg border border-border-default bg-card p-5 shadow-sm sm:p-6" data-testid="new-application-card">
        <h1 className="text-2xl font-bold text-text-primary">{copy.title}</h1>

        <form onSubmit={(event) => void handleSubmit(event)} className="mt-5 flex flex-col gap-4">
          {error && (
            <div
              role="alert"
              className="rounded-md border border-state-error bg-red-50 px-4 py-3 text-sm font-medium text-state-error"
            >
              {error}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-app-title" className="text-sm font-medium text-text-primary">
              {copy.titleLabel} <span aria-hidden="true">*</span>
            </label>
            <input
              id="new-app-title"
              data-testid="new-app-title-input"
              type="text"
              required
              value={title}
              disabled={isBusy}
              onChange={(event) => {
                clearError();
                setTitle(event.target.value);
              }}
              className="rounded-md border border-border-default bg-surface-subtle px-3 py-2 text-sm text-text-primary focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-app-company" className="text-sm font-medium text-text-primary">
              {copy.companyLabel} <span aria-hidden="true">*</span>
            </label>
            <input
              id="new-app-company"
              data-testid="new-app-company-input"
              type="text"
              required
              value={companyName}
              disabled={isBusy}
              onChange={(event) => {
                clearError();
                setCompanyName(event.target.value);
              }}
              className="rounded-md border border-border-default bg-surface-subtle px-3 py-2 text-sm text-text-primary focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-app-description" className="text-sm font-medium text-text-primary">
              {copy.descriptionLabel} <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="new-app-description"
              data-testid="new-app-description-input"
              required
              rows={7}
              placeholder={copy.descriptionPlaceholder}
              value={description}
              disabled={isBusy}
              onChange={(event) => {
                clearError();
                setDescription(event.target.value);
              }}
              className="min-h-40 resize-y rounded-md border border-border-default bg-surface-subtle px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-app-url" className="text-sm font-medium text-text-primary">
              {copy.urlLabel}
            </label>
            <input
              id="new-app-url"
              data-testid="new-app-url-input"
              type="url"
              value={url}
              disabled={isBusy}
              onChange={(event) => {
                clearError();
                setUrl(event.target.value);
              }}
              className="rounded-md border border-border-default bg-surface-subtle px-3 py-2 text-sm text-text-primary focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          <section className="rounded-md border border-border-default bg-surface-subtle p-4" aria-labelledby="base-cv-heading">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h2 id="base-cv-heading" className="text-base font-bold text-text-primary">
                  {copy.baseCvHeading}
                </h2>
                <p className="mt-1 break-words text-sm text-text-muted" data-testid="selected-base-cv-name">
                  {selectedCvName ?? copy.baseCvPlaceholder}
                </p>
                {selectedCv && (
                  <p className="mt-1 text-xs font-medium uppercase text-text-muted">
                    {selectedCv.kind === 'generated' ? copy.baseCvKindGenerated : copy.baseCvKindUploaded}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="secondary"
                size="md"
                disabled={isBusy}
                onClick={() => setIsCvModalOpen(true)}
              >
                {copy.change}
              </Button>
            </div>
          </section>

          <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="secondary" size="md" onClick={goDashboard} disabled={isBusy}>
              {copy.cancel}
            </Button>
            <Button type="submit" variant="primary" size="md" disabled={!isFormComplete || isBusy}>
              {isAnalyzing ? copy.analyzing : isCreating ? copy.creating : copy.create}
            </Button>
          </div>
        </form>
      </section>

      <ChooseBaseCVModal
        isOpen={isCvModalOpen}
        onClose={() => setIsCvModalOpen(false)}
        showChoices
        onSelectCV={(cv, kind) => {
          setSelectedCv({ cv, kind });
          setIsCvModalOpen(false);
        }}
      />
    </div>
  );
}
