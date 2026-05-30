import React, { useMemo, useState } from 'react';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

type JobStatus = 'active' | 'draft' | 'archived';
type JobsTableMode = 'dashboard' | 'full-list';
type SortDirection = 'ascending' | 'descending';
type SortKey = 'title' | 'company' | 'status' | 'updatedAt' | 'action';

interface Job {
  id: string;
  title: string;
  company: string;
  status: JobStatus;
  updatedAt: string;
}

interface JobsTableProps {
  jobs: Job[];
  mode?: JobsTableMode;
  isLoading?: boolean;
  error?: string | null;
  onViewJob?: (jobId: string) => void;
  onNewApplication?: () => void;
  onRetry?: () => void;
}

const STATUS_BADGE: Record<JobStatus, { variant: 'success' | 'warning' | 'neutral'; className: string }> = {
  active: { variant: 'success', className: '' },
  draft: { variant: 'warning', className: 'bg-[#FED7AA] text-[#9A3412] border border-[#FDBA74]' },
  archived: { variant: 'neutral', className: 'bg-[#D1D5DB] text-[#374151] border border-[#D1D5DB]' },
};

const STATUS_LABEL: Record<JobStatus, string> = {
  active: 'Active',
  draft: 'Draft',
  archived: 'Archived',
};

const STATUS_LABEL_HE: Record<JobStatus, string> = {
  active: 'פעיל',
  draft: 'טיוטה',
  archived: 'בארכיון',
};

const TEXT = {
  en: {
    action: 'Action',
    company: 'Company',
    emptyDashboard: 'No applications yet. Click + New Application to get started.',
    emptyFullList: 'No applications yet',
    emptySearch: 'No matching jobs',
    errorFallback: 'Failed to load jobs.',
    headingDashboard: 'Most Recent Jobs',
    headingFullList: 'My Jobs',
    jobTitle: 'Job Title',
    newApplication: '+ New Application',
    retry: 'Retry',
    search: 'Search by job title',
    sortAscending: 'sorted ascending',
    sortDescending: 'sorted descending',
    status: 'Status',
    updated: 'Updated',
    view: 'View',
    viewAll: 'View All',
  },
  he: {
    action: 'פעולה',
    company: 'חברה',
    emptyDashboard: 'אין עדיין הגשות. לחצו על + הגשה חדשה כדי להתחיל.',
    emptyFullList: 'אין עדיין הגשות',
    emptySearch: 'לא נמצאו משרות תואמות',
    errorFallback: 'טעינת המשרות נכשלה.',
    headingDashboard: 'המשרות האחרונות',
    headingFullList: 'המשרות שלי',
    jobTitle: 'שם המשרה',
    newApplication: '+ הגשה חדשה',
    retry: 'נסה שוב',
    search: 'חיפוש לפי שם משרה',
    sortAscending: 'ממוין בסדר עולה',
    sortDescending: 'ממוין בסדר יורד',
    status: 'סטטוס',
    updated: 'עודכן',
    view: 'צפייה',
    viewAll: 'הצג הכל',
  },
};

const DASHBOARD_ROW_LIMIT = 3;

function isHebrewLocale() {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function compareValues(a: string, b: string) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

export function JobsTable({
  jobs,
  mode = 'dashboard',
  isLoading = false,
  error = null,
  onViewJob,
  onNewApplication,
  onRetry,
}: JobsTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'updatedAt',
    direction: 'descending',
  });
  const copy = isHebrewLocale() ? TEXT.he : TEXT.en;
  const statusLabels = isHebrewLocale() ? STATUS_LABEL_HE : STATUS_LABEL;
  const isFullList = mode === 'full-list';

  const columns: Array<{ key: SortKey; label: string }> = [
    { key: 'title', label: copy.jobTitle },
    { key: 'company', label: copy.company },
    { key: 'status', label: copy.status },
    { key: 'updatedAt', label: copy.updated },
    { key: 'action', label: copy.action },
  ];

  const visibleJobs = useMemo(() => {
    const filteredJobs = isFullList && searchQuery.trim().length > 0
      ? jobs.filter((job) => job.title.toLowerCase().includes(searchQuery.trim().toLowerCase()))
      : jobs;

    if (!isFullList) {
      return filteredJobs.slice(0, DASHBOARD_ROW_LIMIT);
    }

    return [...filteredJobs].sort((first, second) => {
      const firstValue = sort.key === 'action' ? first.id : first[sort.key];
      const secondValue = sort.key === 'action' ? second.id : second[sort.key];
      const result = compareValues(firstValue, secondValue);
      return sort.direction === 'ascending' ? result : -result;
    });
  }, [isFullList, jobs, searchQuery, sort]);

  const hasSearchQuery = isFullList && searchQuery.trim().length > 0;
  const headerTextColor = isFullList ? 'text-primary-action' : 'text-text-muted';

  const toggleSort = (key: SortKey) => {
    if (!isFullList) return;

    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'ascending' ? 'descending' : 'ascending',
    }));
  };

  const renderBadge = (job: Job) => {
    const badge = STATUS_BADGE[job.status];
    return (
      <Badge variant={badge.variant} soft={isFullList} className={badge.className}>
        {statusLabels[job.status]}
      </Badge>
    );
  };

  const renderViewButton = (job: Job) => (
    <button
      type="button"
      onClick={() => onViewJob?.(job.id)}
      className="jobs-table-view text-text-primary text-base font-bold hover:underline group-hover:underline"
    >
      {copy.view}
    </button>
  );

  const renderSkeletonRows = () => (
    <>
      {Array.from({ length: 3 }, (_, index) => (
        <tr key={index} data-testid="jobs-table-skeleton-row" className="border-b border-border-default last:border-b-0">
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
        <div className="flex flex-col items-center gap-4">
          <span>{hasSearchQuery ? copy.emptySearch : isFullList ? copy.emptyFullList : copy.emptyDashboard}</span>
          {isFullList && !hasSearchQuery && (
            <Button variant="primary" size="md" onClick={onNewApplication} data-testid="jobs-table-empty-new-application">
              {copy.newApplication}
            </Button>
          )}
        </div>
      </td>
    </tr>
  );

  const renderErrorState = () => (
    <tr>
      <td colSpan={columns.length} className="px-4 py-10 text-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-base text-state-error">{error || copy.errorFallback}</p>
          <Button variant="secondary" size="md" onClick={onRetry}>
            {copy.retry}
          </Button>
        </div>
      </td>
    </tr>
  );

  return (
    <section className="bg-card border border-border-default rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div className="flex items-center gap-3">
          <h2 className="font-bold text-text-primary text-2xl">
            {isFullList ? copy.headingFullList : copy.headingDashboard}
          </h2>
          {!isFullList && (
            <button type="button" className="text-primary-action text-base font-normal hover:underline">
              {copy.viewAll}
            </button>
          )}
        </div>
        <Button variant="primary" size="md" onClick={onNewApplication}>
          {copy.newApplication}
        </Button>
      </div>

      {isFullList && (
        <div className="border-b border-border-default px-6 py-4">
          <label className="sr-only" htmlFor="jobs-table-search">
            {copy.search}
          </label>
          <input
            id="jobs-table-search"
            data-testid="jobs-table-search"
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder={copy.search}
            className="w-full max-w-sm rounded-md border border-border-default bg-card px-3 py-2 text-base text-text-primary placeholder:text-text-muted focus:border-primary-action focus:outline-none focus:ring-1 focus:ring-primary-action"
          />
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse" data-testid="jobs-table">
          <thead className="hidden bg-surface-subtle border-b border-border-default md:table-header-group">
            <tr>
              {columns.map((column) => {
                const isActiveSort = isFullList && sort.key === column.key;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={isActiveSort ? sort.direction : undefined}
                    className={`px-4 py-3 text-left text-base font-medium ${headerTextColor}`}
                  >
                    {isFullList ? (
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
                    ) : (
                      column.label
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {isLoading && renderSkeletonRows()}
            {!isLoading && error && renderErrorState()}
            {!isLoading && !error && visibleJobs.length === 0 && renderEmptyState()}
            {!isLoading && !error && visibleJobs.map((job, index) => (
              <tr
                key={job.id}
                data-testid={`job-row-${job.id}`}
                className={`group block border-b border-border-default p-4 last:border-b-0 hover:bg-surface-selected md:table-row md:p-0 ${
                  index % 2 === 0 ? 'bg-white' : 'bg-surface-subtle'
                }`}
              >
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.jobTitle}</span>
                  <span>{job.title}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.company}</span>
                  <span>{job.company}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.status}</span>
                  <span>{renderBadge(job)}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 text-text-primary text-base font-medium md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.updated}</span>
                  <span>{job.updatedAt}</span>
                </td>
                <td className="grid grid-cols-[7rem_1fr] gap-3 px-0 py-2 md:table-cell md:px-4 md:py-4">
                  <span className="text-sm font-medium text-text-muted md:hidden">{copy.action}</span>
                  <span>{renderViewButton(job)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
