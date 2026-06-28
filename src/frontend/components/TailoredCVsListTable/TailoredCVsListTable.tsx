'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { Badge } from '../ui/Badge';
import type { TailoredCvListItem, TailoredCvListStatus } from '../../lib/types';

type SortDirection = 'ascending' | 'descending';
type SortKey = 'title' | 'language' | 'updated_at' | 'status' | 'action';

export interface TailoredCVsListTableProps {
  tailoredCvs: TailoredCvListItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const STATUS_BADGE: Record<TailoredCvListStatus, { variant: 'success' | 'info' | 'destructive' }> = {
  ready: { variant: 'success' },
  processing: { variant: 'info' },
  failed: { variant: 'destructive' },
  edited: { variant: 'info' },
};

const STATUS_LABEL_EN: Record<TailoredCvListStatus, string> = {
  ready: 'Ready',
  processing: 'Processing',
  failed: 'Failed',
  edited: 'Edited',
};

const STATUS_LABEL_HE: Record<TailoredCvListStatus, string> = {
  ready: 'מוכן',
  processing: 'בעיבוד',
  failed: 'נכשל',
  edited: 'נערך',
};

const TEXT = {
  en: {
    action: 'Action',
    emptySearch: 'No matching tailored CVs',
    errorFallback: 'Failed to load tailored CVs.',
    language: 'Language',
    lastUpdated: 'Last Updated',
    retry: 'Retry',
    search: 'Search by title or language',
    sortAscending: 'sorted ascending',
    sortDescending: 'sorted descending',
    status: 'Status',
    title: 'Title',
    view: 'View',
  },
  he: {
    action: 'פעולה',
    emptySearch: 'לא נמצאו קורות חיים מותאמים תואמים',
    errorFallback: 'טעינת קורות החיים המותאמים נכשלה.',
    language: 'שפה',
    lastUpdated: 'עודכן לאחרונה',
    retry: 'נסה שוב',
    search: 'חיפוש לפי כותרת או שפה',
    sortAscending: 'ממוין בסדר עולה',
    sortDescending: 'ממוין בסדר יורד',
    status: 'סטטוס',
    title: 'כותרת',
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

export function TailoredCVsListTable({
  tailoredCvs,
  isLoading = false,
  error = null,
  onRetry,
}: TailoredCVsListTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'updated_at',
    direction: 'descending',
  });

  const isHebrew = isHebrewLocale();
  const copy = isHebrew ? TEXT.he : TEXT.en;
  const statusLabels = isHebrew ? STATUS_LABEL_HE : STATUS_LABEL_EN;
  const intlLocale: 'en-US' | 'he-IL' = isHebrew ? 'he-IL' : 'en-US';

  const columns: Array<{ key: SortKey; label: string }> = [
    { key: 'title', label: copy.title },
    { key: 'language', label: copy.language },
    { key: 'updated_at', label: copy.lastUpdated },
    { key: 'status', label: copy.status },
    { key: 'action', label: copy.action },
  ];

  const visibleTailoredCvs = useMemo(() => {
    const trimmed = searchQuery.trim().toLowerCase();
    const filtered = trimmed.length === 0
      ? tailoredCvs
      : tailoredCvs.filter((cv) =>
        cv.title.toLowerCase().includes(trimmed) || cv.language.toLowerCase().includes(trimmed),
      );

    return [...filtered].sort((first, second) => {
      const directionMultiplier = sort.direction === 'ascending' ? 1 : -1;
      if (sort.key === 'updated_at') {
        const firstTime = Date.parse(first.updated_at);
        const secondTime = Date.parse(second.updated_at);
        return directionMultiplier * ((firstTime || 0) - (secondTime || 0));
      }
      if (sort.key === 'action') {
        return directionMultiplier * compareValues(first.applicationId, second.applicationId);
      }
      return directionMultiplier * compareValues(first[sort.key], second[sort.key]);
    });
  }, [tailoredCvs, searchQuery, sort]);

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
          data-testid="tailored-cvs-list-table-skeleton-row"
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
        {hasSearchQuery ? (
          copy.emptySearch
        ) : (
          <span>
            {isHebrew ? (
              <>
                {'אין עדיין קורות חיים מותאמים. צרו אחד מתוך '}
                <Link href="/applications" className="font-semibold text-primary-action hover:underline">
                  הגשה
                </Link>
                .
              </>
            ) : (
              <>
                {'No tailored CVs yet. Create one from an '}
                <Link href="/applications" className="font-semibold text-primary-action hover:underline">
                  application
                </Link>
                .
              </>
            )}
          </span>
        )}
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

  const renderStatusBadge = (status: TailoredCvListStatus) => (
    <Badge variant={STATUS_BADGE[status].variant} soft>
      {statusLabels[status]}
    </Badge>
  );

  const renderViewLink = (cv: TailoredCvListItem) => (
    <Link
      href={`/applications/${cv.applicationId}/cv-tailored?id=${cv.id}`}
      className="text-text-primary text-base font-bold hover:underline group-hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
    >
      {copy.view}
    </Link>
  );

  return (
    <section className="bg-card border border-border-default rounded-xl overflow-hidden">
      <div className="border-b border-border-default px-6 py-4">
        <label className="sr-only" htmlFor="tailored-cvs-list-table-search">
          {copy.search}
        </label>
        <input
          id="tailored-cvs-list-table-search"
          data-testid="tailored-cvs-list-table-search"
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
          data-testid="tailored-cvs-list-table"
          data-is-loading={isLoading ? 'true' : 'false'}
          data-has-error={error ? 'true' : 'false'}
          data-tailored-cvs-count={String(tailoredCvs.length)}
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
            {!isLoading && !error && visibleTailoredCvs.length === 0 && renderEmptyState()}
            {!isLoading && !error && visibleTailoredCvs.map((cv, index) => (
              <tr
                key={cv.id}
                data-testid={`tailored-cv-row-${cv.id}`}
                className={`group block border-b border-border-default p-4 last:border-b-0 hover:bg-surface-selected md:table-row md:p-0 ${
                  index % 2 === 0 ? 'bg-white' : 'bg-surface-subtle'
                }`}
              >
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.title}</span>
                  <span>{cv.title}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.language}</span>
                  <span>{cv.language}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.lastUpdated}</span>
                  <span>{formatDate(cv.updated_at, intlLocale)}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.status}</span>
                  <span>{renderStatusBadge(cv.status)}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.action}</span>
                  <span>{renderViewLink(cv)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
