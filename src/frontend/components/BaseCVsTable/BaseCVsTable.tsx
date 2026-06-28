'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { Badge } from '../ui/Badge';

export type BaseCVStatus = 'ready' | 'processing' | 'failed';
type SortDirection = 'ascending' | 'descending';
type SortKey = 'full_name' | 'created_at' | 'language' | 'updated_at' | 'status' | 'used_in' | 'actions';

export interface BaseCVListItem {
  cv_id?: string;
  id?: string;
  full_name: string;
  language: string;
  created_at?: string;
  uploaded_at?: string;
  updated_at?: string;
  status?: BaseCVStatus | string;
  used_in?: number | string | string[] | Array<{ id?: string; title?: string; name?: string }>;
  used_in_count?: number;
  applications_count?: number;
}

export interface BaseCVsTableProps {
  cvs: BaseCVListItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onUploadNew?: () => void;
  onSetDefault?: (cvId: string) => void;
  onDelete?: (cvId: string) => void;
}

const STATUS_BADGE: Record<BaseCVStatus, { variant: 'success' | 'info' | 'destructive' }> = {
  ready: { variant: 'success' },
  processing: { variant: 'info' },
  failed: { variant: 'destructive' },
};

const STATUS_LABEL_EN: Record<BaseCVStatus, string> = {
  ready: 'Ready',
  processing: 'Processing',
  failed: 'Failed',
};

const STATUS_LABEL_HE: Record<BaseCVStatus, string> = {
  ready: 'מוכן',
  processing: 'בעיבוד',
  failed: 'נכשל',
};

const TEXT = {
  en: {
    actions: 'Actions',
    delete: 'Delete',
    empty: 'No primary CVs uploaded yet',
    errorFallback: 'Failed to load base CVs.',
    fileName: 'File Name',
    language: 'Language',
    lastUpdated: 'Last Updated',
    retry: 'Retry',
    setAsDefault: 'Set as Default',
    sortAscending: 'sorted ascending',
    sortDescending: 'sorted descending',
    status: 'Status',
    uploadDate: 'Upload Date',
    uploadNew: '+ Upload New CV',
    usedIn: 'Used In',
    view: 'View',
  },
  he: {
    actions: 'פעולות',
    delete: 'מחיקה',
    empty: 'לא הועלו עדיין קורות חיים ראשיים',
    errorFallback: 'טעינת קורות החיים הבסיסיים נכשלה.',
    fileName: 'שם הקובץ',
    language: 'שפה',
    lastUpdated: 'עודכן לאחרונה',
    retry: 'נסה שוב',
    setAsDefault: 'הגדר כברירת מחדל',
    sortAscending: 'ממוין בסדר עולה',
    sortDescending: 'ממוין בסדר יורד',
    status: 'סטטוס',
    uploadDate: 'תאריך העלאה',
    uploadNew: '+ העלאת קורות חיים חדשים',
    usedIn: 'בשימוש ב',
    view: 'צפייה',
  },
};

function isHebrewLocale(): boolean {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function compareValues(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

function formatDate(isoString: string | undefined, locale: 'en-US' | 'he-IL'): string {
  if (!isoString) return '—';

  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
}

function getCvId(cv: BaseCVListItem): string {
  return cv.cv_id ?? cv.id ?? cv.full_name;
}

function getUploadDate(cv: BaseCVListItem): string | undefined {
  return cv.created_at ?? cv.uploaded_at ?? cv.updated_at;
}

function getLastUpdated(cv: BaseCVListItem): string | undefined {
  return cv.updated_at ?? cv.created_at ?? cv.uploaded_at;
}

function normalizeStatus(status: BaseCVListItem['status']): BaseCVStatus {
  const normalized = `${status ?? 'ready'}`.toLowerCase();
  if (normalized === 'processing' || normalized === 'failed') return normalized;
  return 'ready';
}

function getUsedInCount(cv: BaseCVListItem): number | null {
  if (typeof cv.used_in_count === 'number') return cv.used_in_count;
  if (typeof cv.applications_count === 'number') return cv.applications_count;
  if (typeof cv.used_in === 'number') return cv.used_in;
  if (Array.isArray(cv.used_in)) return cv.used_in.length;
  return null;
}

function getUsedInDisplay(cv: BaseCVListItem): string {
  if (Array.isArray(cv.used_in)) {
    if (cv.used_in.length === 0) return '0';
    if (typeof cv.used_in[0] === 'string') return (cv.used_in as string[]).join(', ');
    return (cv.used_in as Array<{ id?: string; title?: string; name?: string }>)
      .map((application) => application.title ?? application.name ?? application.id)
      .filter((value): value is string => Boolean(value))
      .join(', ') || String(cv.used_in.length);
  }

  if (typeof cv.used_in === 'string') return cv.used_in;

  const count = getUsedInCount(cv);
  return count === null ? '—' : String(count);
}

function dateSortValue(value: string | undefined): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function BaseCVsTable({
  cvs,
  isLoading = false,
  error = null,
  onRetry,
  onUploadNew,
  onSetDefault,
  onDelete,
}: BaseCVsTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'updated_at',
    direction: 'descending',
  });

  const isHebrew = isHebrewLocale();
  const copy = isHebrew ? TEXT.he : TEXT.en;
  const statusLabels = isHebrew ? STATUS_LABEL_HE : STATUS_LABEL_EN;
  const intlLocale: 'en-US' | 'he-IL' = isHebrew ? 'he-IL' : 'en-US';

  const columns: Array<{ key: SortKey; label: string }> = [
    { key: 'full_name', label: copy.fileName },
    { key: 'created_at', label: copy.uploadDate },
    { key: 'language', label: copy.language },
    { key: 'updated_at', label: copy.lastUpdated },
    { key: 'status', label: copy.status },
    { key: 'used_in', label: copy.usedIn },
    { key: 'actions', label: copy.actions },
  ];

  const visibleCvs = useMemo(() => {
    return [...cvs].sort((first, second) => {
      const directionMultiplier = sort.direction === 'ascending' ? 1 : -1;

      if (sort.key === 'created_at') {
        return directionMultiplier * (dateSortValue(getUploadDate(first)) - dateSortValue(getUploadDate(second)));
      }

      if (sort.key === 'updated_at') {
        return directionMultiplier * (dateSortValue(getLastUpdated(first)) - dateSortValue(getLastUpdated(second)));
      }

      if (sort.key === 'status') {
        return directionMultiplier * compareValues(normalizeStatus(first.status), normalizeStatus(second.status));
      }

      if (sort.key === 'used_in') {
        const firstCount = getUsedInCount(first);
        const secondCount = getUsedInCount(second);
        if (firstCount !== null && secondCount !== null) return directionMultiplier * (firstCount - secondCount);
        return directionMultiplier * compareValues(getUsedInDisplay(first), getUsedInDisplay(second));
      }

      if (sort.key === 'actions') {
        return directionMultiplier * compareValues(getCvId(first), getCvId(second));
      }

      return directionMultiplier * compareValues(first[sort.key], second[sort.key]);
    });
  }, [cvs, sort]);

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
          data-testid="base-cvs-table-skeleton-row"
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

  const renderEmptyState = () => (
    <tr>
      <td colSpan={columns.length} className="px-4 py-10 text-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-base text-text-muted">{copy.empty}</p>
          <button
            type="button"
            onClick={() => onUploadNew?.()}
            className="rounded-md bg-primary-action px-4 py-2 text-sm font-bold text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
          >
            {copy.uploadNew}
          </button>
        </div>
      </td>
    </tr>
  );

  const renderStatusBadge = (status: BaseCVListItem['status']) => {
    const normalizedStatus = normalizeStatus(status);
    return (
      <Badge variant={STATUS_BADGE[normalizedStatus].variant} soft>
        {statusLabels[normalizedStatus]}
      </Badge>
    );
  };

  const renderActions = (cvId: string) => (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => onSetDefault?.(cvId)}
        className="rounded-md border border-border-default px-3 py-1.5 text-sm font-semibold text-text-primary hover:bg-surface-subtle focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
      >
        {copy.setAsDefault}
      </button>
      <button
        type="button"
        onClick={() => onDelete?.(cvId)}
        className="rounded-md border border-state-error px-3 py-1.5 text-sm font-semibold text-state-error hover:bg-state-error/10 focus:outline-none focus:ring-2 focus:ring-state-error focus:ring-offset-2"
      >
        {copy.delete}
      </button>
      <Link
        href={`/cv-center/${cvId}`}
        className="text-text-primary text-base font-bold hover:underline group-hover:underline focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2"
      >
        {copy.view}
      </Link>
    </div>
  );

  return (
    <section className="overflow-hidden rounded-xl border border-border-default bg-card">
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse"
          data-testid="base-cvs-table"
          data-is-loading={isLoading ? 'true' : 'false'}
          data-has-error={error ? 'true' : 'false'}
          data-base-cvs-count={String(cvs.length)}
        >
          <thead className="hidden border-b border-border-default bg-surface-subtle md:table-header-group">
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
            {!isLoading && !error && visibleCvs.length === 0 && renderEmptyState()}
            {!isLoading && !error && visibleCvs.map((cv, index) => {
              const cvId = getCvId(cv);
              return (
                <tr
                  key={cvId}
                  data-testid={`base-cv-row-${cvId}`}
                  className={`group block border-b border-border-default p-4 last:border-b-0 hover:bg-surface-selected md:table-row md:p-0 ${
                    index % 2 === 0 ? 'bg-white' : 'bg-surface-subtle'
                  }`}
                >
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-base font-medium text-text-primary md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.fileName}</span>
                    <span>{cv.full_name}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-base font-medium text-text-primary md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.uploadDate}</span>
                    <span>{formatDate(getUploadDate(cv), intlLocale)}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-base font-medium text-text-primary md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.language}</span>
                    <span>{cv.language}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-base font-medium text-text-primary md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.lastUpdated}</span>
                    <span>{formatDate(getLastUpdated(cv), intlLocale)}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.status}</span>
                    <span>{renderStatusBadge(cv.status)}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-base font-medium text-text-primary md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.usedIn}</span>
                    <span>{getUsedInDisplay(cv)}</span>
                  </td>
                  <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                    <span className="text-sm font-medium text-text-muted md:hidden">{copy.actions}</span>
                    {renderActions(cvId)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
