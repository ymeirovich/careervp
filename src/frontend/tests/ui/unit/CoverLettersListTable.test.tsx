import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CoverLettersListTable } from '../../../components/CoverLettersListTable/CoverLettersListTable';

const coverLetters = [
  {
    applicationId: 'app-1',
    company_name: 'Gamma Inc',
    job_title: 'Senior Engineer',
    status: 'ready' as const,
    created_at: '2026-05-20T10:00:00Z',
  },
  {
    applicationId: 'app-2',
    company_name: 'Acme Corp',
    job_title: 'Product Manager',
    status: 'processing' as const,
    created_at: '2026-05-15T09:00:00Z',
  },
  {
    applicationId: 'app-3',
    company_name: 'Beta Ltd',
    job_title: 'Data Analyst',
    status: 'failed' as const,
    created_at: '2026-05-10T08:00:00Z',
  },
];

afterEach(() => {
  document.documentElement.lang = 'en';
});

function table() {
  return screen.getByTestId('cover-letters-list-table');
}

describe('CoverLettersListTable', () => {
  it('renders semantic table markup with scoped column headers', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    expect(table().tagName).toBe('TABLE');
    const headers = within(table()).getAllByRole('columnheader');
    expect(headers).toHaveLength(5);
    headers.forEach((header) => expect(header).toHaveAttribute('scope', 'col'));
  });

  it('renders zebra striping, hover highlight, and a bold View link action', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    expect(screen.getByTestId('cover-letter-row-app-1').className).toContain('bg-white');
    expect(screen.getByTestId('cover-letter-row-app-2').className).toContain('bg-surface-subtle');
    expect(screen.getByTestId('cover-letter-row-app-1').className).toContain('hover:bg-surface-selected');

    const viewLink = within(screen.getByTestId('cover-letter-row-app-1')).getByRole('link', { name: 'View' });
    expect(viewLink.className).toContain('font-bold');
    expect(viewLink.className).toContain('hover:underline');
    expect(viewLink).toHaveAttribute('href', '/applications/app-1/cover-letter');
  });

  it('maps status to soft badges for ready/processing and destructive for failed', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    const readyBadge = within(screen.getByTestId('cover-letter-row-app-1')).getByText('Ready');
    const processingBadge = within(screen.getByTestId('cover-letter-row-app-2')).getByText('Processing');
    const failedBadge = within(screen.getByTestId('cover-letter-row-app-3')).getByText('Failed');

    expect(readyBadge.className).toContain('bg-green-50');
    expect(processingBadge.className).toContain('bg-blue-50');
    expect(failedBadge.className).toContain('bg-state-error');
  });

  it('defaults to date descending sort (most recent first)', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    const rows = screen.getAllByTestId(/^cover-letter-row-/);
    expect(rows[0]).toHaveAttribute('data-testid', 'cover-letter-row-app-1');
    expect(rows[1]).toHaveAttribute('data-testid', 'cover-letter-row-app-2');
    expect(rows[2]).toHaveAttribute('data-testid', 'cover-letter-row-app-3');
  });

  it('sorts rows by column click and keyboard activation with aria-sort updates', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    const companyHeader = within(table()).getByRole('columnheader', { name: /Company/ });
    const companyButton = within(companyHeader).getByRole('button', { name: /Company/ });

    fireEvent.click(companyButton);
    expect(companyHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(screen.getAllByTestId(/^cover-letter-row-/)[0]).toHaveAttribute('data-testid', 'cover-letter-row-app-2');

    fireEvent.keyDown(companyButton, { key: 'Enter' });
    expect(companyHeader).toHaveAttribute('aria-sort', 'descending');
    expect(screen.getAllByTestId(/^cover-letter-row-/)[0]).toHaveAttribute('data-testid', 'cover-letter-row-app-1');

    const statusHeader = within(table()).getByRole('columnheader', { name: /Status/ });
    fireEvent.click(within(statusHeader).getByRole('button', { name: /Status/ }));
    expect(statusHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(companyHeader).not.toHaveAttribute('aria-sort');
  });

  it('filters rows by search across company and job title and shows empty-search state', () => {
    render(<CoverLettersListTable coverLetters={coverLetters} />);

    fireEvent.change(screen.getByTestId('cover-letters-list-table-search'), { target: { value: 'acme' } });
    expect(screen.getByTestId('cover-letter-row-app-2')).toBeInTheDocument();
    expect(screen.queryByTestId('cover-letter-row-app-1')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('cover-letters-list-table-search'), { target: { value: 'zzznomatch' } });
    expect(within(table()).getByText('No matching cover letters')).toBeInTheDocument();
    expect(within(table()).queryByText('No cover letters yet')).not.toBeInTheDocument();
  });

  it('renders loading, error (+ retry), and empty states inside the table card', () => {
    const onRetry = vi.fn();
    const { rerender } = render(<CoverLettersListTable coverLetters={coverLetters} isLoading />);

    expect(screen.getAllByTestId('cover-letters-list-table-skeleton-row')).toHaveLength(3);
    expect(screen.queryByTestId('cover-letter-row-app-1')).not.toBeInTheDocument();

    rerender(<CoverLettersListTable coverLetters={[]} error="Could not load cover letters" onRetry={onRetry} />);
    expect(within(table()).getByText('Could not load cover letters')).toBeInTheDocument();
    fireEvent.click(within(table()).getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<CoverLettersListTable coverLetters={[]} />);
    expect(within(table()).getByText('No cover letters yet')).toBeInTheDocument();
  });

  it('renders responsive card-style row markup with all five field labels', () => {
    render(<CoverLettersListTable coverLetters={[coverLetters[0]]} />);

    const row = screen.getByTestId('cover-letter-row-app-1');
    expect(row.className).toContain('block');
    expect(row.className).toContain('md:table-row');
    expect(within(row).getByText('Company')).toBeInTheDocument();
    expect(within(row).getByText('Job Title')).toBeInTheDocument();
    expect(within(row).getByText('Date')).toBeInTheDocument();
    expect(within(row).getByText('Status')).toBeInTheDocument();
    expect(within(row).getByText('Action')).toBeInTheDocument();
  });

  it('renders Hebrew labels from the document locale', () => {
    document.documentElement.lang = 'he';
    render(<CoverLettersListTable coverLetters={[coverLetters[0]]} />);

    expect(within(table()).getByRole('columnheader', { name: 'חברה' })).toBeInTheDocument();
    expect(screen.getByTestId('cover-letters-list-table-search')).toHaveAttribute('placeholder', 'חיפוש לפי חברה או שם משרה');
    expect(within(screen.getByTestId('cover-letter-row-app-1')).getByRole('link', { name: 'צפייה' })).toBeInTheDocument();
    expect(within(screen.getByTestId('cover-letter-row-app-1')).getByText('מוכן')).toBeInTheDocument();
  });
});

