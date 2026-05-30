'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { Badge } from '../ui/Badge';

type CoverLetterStatus = 'ready' | 'processing' | 'failed';
type SortDirection = 'ascending' | 'descending';
type SortKey = 'company_name' | 'job_title' | 'created_at' | 'status' | 'action';

export interface CoverLetterListItem {
  applicationId: string;
  company_name: string;
  job_title: string;
  status: CoverLetterStatus;
  created_at: string;
}

export interface CoverLettersListTableProps {
  coverLetters: CoverLetterListItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const STATUS_BADGE: Record<CoverLetterStatus, { variant: 'success' | 'info' | 'destructive' }> = {
  ready: { variant: 'success' },
  processing: { variant: 'info' },
  failed: { variant: 'destructive' },
};

const STATUS_LABEL_EN: Record<CoverLetterStatus, string> = {
  ready: 'Ready',
  processing: 'Processing',
  failed: 'Failed',
};

const STATUS_LABEL_HE: Record<CoverLetterStatus, string> = {
  ready: 'מוכן',
  processing: 'בעיבוד',
  failed: 'נכשל',
};

const TEXT = {
  en: {
    action: 'Action',
    company: 'Company',
    date: 'Date',
    empty: 'No cover letters yet',
    emptySearch: 'No matching cover letters',
    errorFallback: 'Failed to load cover letters.',
    jobTitle: 'Job Title',
    retry: 'Retry',
    search: 'Search by company or job title',
    sortAscending: 'sorted ascending',
    sortDescending: 'sorted descending',
    status: 'Status',
    view: 'View',
  },
  he: {
    action: 'פעולה',
    company: 'חברה',
    date: 'תאריך',
    empty: 'אין עדיין מכתבי פנייה',
    emptySearch: 'לא נמצאו מכתבי פנייה תואמים',
    errorFallback: 'טעינת מכתבי הפנייה נכשלה.',
    jobTitle: 'שם המשרה',
    retry: 'נסה שוב',
    search: 'חיפוש לפי חברה או שם משרה',
    sortAscending: 'ממוין בסדר עולה',
    sortDescending: 'ממוין בסדר יורד',
    status: 'סטטוס',
    view: 'צפייה',
  },
};

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function compareValues(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

function formatDate(isoString: string, locale: 'en-US' | 'he-IL'): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
}

export function CoverLettersListTable({
  coverLetters,
  isLoading = false,
  error = null,
  onRetry,
}: CoverLettersListTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'created_at',
    direction: 'descending',
  });

  const isHebrew = isHebrewLocale();
  const copy = isHebrew ? TEXT.he : TEXT.en;
  const statusLabels = isHebrew ? STATUS_LABEL_HE : STATUS_LABEL_EN;
  const intlLocale: 'en-US' | 'he-IL' = isHebrew ? 'he-IL' : 'en-US';

  const columns: Array<{ key: SortKey; label: string }> = [
    { key: 'company_name', label: copy.company },
    { key: 'job_title', label: copy.jobTitle },
    { key: 'created_at', label: copy.date },
    { key: 'status', label: copy.status },
    { key: 'action', label: copy.action },
  ];

  const visibleCoverLetters = useMemo(() => {
    const trimmed = searchQuery.trim().toLowerCase();
    const filtered = trimmed.length === 0
      ? coverLetters
      : coverLetters.filter((letter) =>
        letter.company_name.toLowerCase().includes(trimmed) || letter.job_title.toLowerCase().includes(trimmed),
      );

    return [...filtered].sort((first, second) => {
      const directionMultiplier = sort.direction === 'ascending' ? 1 : -1;
      if (sort.key === 'created_at') {
        const firstTime = Date.parse(first.created_at);
        const secondTime = Date.parse(second.created_at);
        return directionMultiplier * ((firstTime || 0) - (secondTime || 0));
      }
      if (sort.key === 'action') {
        return directionMultiplier * compareValues(first.applicationId, second.applicationId);
      }
      return directionMultiplier * compareValues(first[sort.key], second[sort.key]);
    });
  }, [coverLetters, searchQuery, sort]);

  const hasSearchQuery = searchQuery.trim().length > 0;

  const toggleSort = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'ascending' ? 'descending' : 'ascending',
    }));
  };

  const renderSkeletonRows = () => (
    <>
      {Array.from({ length: 3 }, (_, index) => (
        <tr
          // eslint-disable-next-line react/no-array-index-key
          key={index}
          data-testid="cover-letters-list-table-skeleton-row"
          className="border-b border-border-default last:border-b-0"
        >
          {columns.map((column) => (
            <td key={column.key} className="px-4 py-4">
              <div className="h-5 w-3/4 animate-pulse rounded bg-surface-selected" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );

  const renderEmptyState = () => (
    <tr>
      <td colSpan={columns.length} className="px-4 py-10 text-center text-text-muted text-base">
        {hasSearchQuery ? copy.emptySearch : copy.empty}
      </td>
    </tr>
  );

  const renderErrorState = () => (
    <tr>
      <td colSpan={columns.length} className="px-4 py-10 text-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-base text-state-error">{error || copy.errorFallback}</p>
          <button
            type="button"
            onClick={() => onRetry?.()}
            className="rounded-md border border-border-default bg-card px-4 py-2 text-sm font-semibold text-text-primary hover:bg-surface-subtle focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
          >
            {copy.retry}
          </button>
        </div>
      </td>
    </tr>
  );

  const renderStatusBadge = (status: CoverLetterStatus) => (
    <Badge variant={STATUS_BADGE[status].variant} soft>
      {statusLabels[status]}
    </Badge>
  );

  const renderViewLink = (applicationId: string) => (
    <Link
      href={`/applications/${applicationId}/cover-letter`}
      className="text-text-primary text-base font-bold hover:underline group-hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
    >
      {copy.view}
    </Link>
  );

  return (
    <section className="bg-card border border-border-default rounded-xl overflow-hidden">
      <div className="border-b border-border-default px-6 py-4">
        <label className="sr-only" htmlFor="cover-letters-list-table-search">
          {copy.search}
        </label>
        <input
          id="cover-letters-list-table-search"
          data-testid="cover-letters-list-table-search"
          type="search"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder={copy.search}
          className="w-full max-w-md rounded-md border border-border-default bg-card px-3 py-2 text-base text-text-primary placeholder:text-text-muted focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action"
        />
      </div>

      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse"
          data-testid="cover-letters-list-table"
          data-is-loading={isLoading ? 'true' : 'false'}
          data-has-error={error ? 'true' : 'false'}
          data-cover-letters-count={String(coverLetters.length)}
        >
          <thead className="hidden bg-surface-subtle border-b border-border-default md:table-header-group">
            <tr>
              {columns.map((column) => {
                const isActiveSort = sort.key === column.key;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={isActiveSort ? sort.direction : undefined}
                    className="px-4 py-3 text-left text-base font-medium text-primary-action"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          toggleSort(column.key);
                        }
                      }}
                      className="inline-flex items-center gap-1 font-medium hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
                      aria-label={`${column.label} ${isActiveSort ? copy[sort.direction === 'ascending' ? 'sortAscending' : 'sortDescending'] : ''}`.trim()}
                    >
                      <span>{column.label}</span>
                      <span aria-hidden="true" className="w-4 text-sm">
                        {isActiveSort ? (sort.direction === 'ascending' ? '▲' : '▼') : ''}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {isLoading && renderSkeletonRows()}
            {!isLoading && error && renderErrorState()}
            {!isLoading && !error && visibleCoverLetters.length === 0 && renderEmptyState()}
            {!isLoading && !error && visibleCoverLetters.map((letter, index) => (
              <tr
                key={letter.applicationId}
                data-testid={`cover-letter-row-${letter.applicationId}`}
                className={`group block border-b border-border-default p-4 last:border-b-0 hover:bg-surface-selected md:table-row md:p-0 ${
                  index % 2 === 0 ? 'bg-white' : 'bg-surface-subtle'
                }`}
              >
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.company}</span>
                  <span>{letter.company_name}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.jobTitle}</span>
                  <span>{letter.job_title}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.date}</span>
                  <span>{formatDate(letter.created_at, intlLocale)}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.status}</span>
                  <span>{renderStatusBadge(letter.status)}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.action}</span>
                  <span>{renderViewLink(letter.applicationId)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

