import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TailoredCVsListTable } from '../../../components/TailoredCVsListTable/TailoredCVsListTable';

const tailoredCvs = [
  {
    id: 'tc-1',
    applicationId: 'app-1',
    title: 'base_cv_v2_tailored.pdf',
    language: 'English',
    status: 'ready' as const,
    updated_at: '2026-05-20T10:00:00Z',
  },
  {
    id: 'tc-2',
    applicationId: 'app-2',
    title: 'senior_backend_tailored.pdf',
    language: 'Hebrew',
    status: 'processing' as const,
    updated_at: '2026-05-15T09:00:00Z',
  },
  {
    id: 'tc-3',
    applicationId: 'app-3',
    title: 'data_analyst_tailored.pdf',
    language: 'English',
    status: 'failed' as const,
    updated_at: '2026-05-10T08:00:00Z',
  },
  {
    id: 'tc-4',
    applicationId: 'app-4',
    title: 'product_manager_tailored.pdf',
    language: 'English',
    status: 'edited' as const,
    updated_at: '2026-05-12T08:00:00Z',
  },
];

afterEach(() => {
  document.documentElement.lang = 'en';
  vi.unstubAllGlobals();
});

function table() {
  return screen.getByTestId('tailored-cvs-list-table');
}

describe('TailoredCVsListTable', () => {
  it('renders semantic table markup with scoped column headers', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    expect(table().tagName).toBe('TABLE');
    const headers = within(table()).getAllByRole('columnheader');
    expect(headers).toHaveLength(5);
    headers.forEach((header) => expect(header).toHaveAttribute('scope', 'col'));
  });

  it('renders zebra striping, hover highlight, and a bold View link action', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    expect(screen.getByTestId('tailored-cv-row-tc-1').className).toContain('bg-white');
    expect(screen.getByTestId('tailored-cv-row-tc-2').className).toContain('bg-surface-subtle');
    expect(screen.getByTestId('tailored-cv-row-tc-1').className).toContain('hover:bg-surface-selected');

    const viewLink = within(screen.getByTestId('tailored-cv-row-tc-1')).getByRole('link', { name: 'View' });
    expect(viewLink.className).toContain('font-bold');
    expect(viewLink.className).toContain('hover:underline');
    expect(viewLink).toHaveAttribute('href', '/applications/app-1/cv-tailored?id=tc-1');
  });

  it('maps status to soft badges for ready/processing/edited and destructive for failed', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    const readyBadge = within(screen.getByTestId('tailored-cv-row-tc-1')).getByText('Ready');
    const processingBadge = within(screen.getByTestId('tailored-cv-row-tc-2')).getByText('Processing');
    const failedBadge = within(screen.getByTestId('tailored-cv-row-tc-3')).getByText('Failed');
    const editedBadge = within(screen.getByTestId('tailored-cv-row-tc-4')).getByText('Edited');

    expect(readyBadge.className).toContain('bg-green-50');
    expect(processingBadge.className).toContain('bg-blue-50');
    expect(editedBadge.className).toContain('bg-blue-50');
    expect(failedBadge.className).toContain('bg-state-error');
  });

  it('formats Last Updated using Intl.DateTimeFormat', () => {
    render(<TailoredCVsListTable tailoredCvs={[tailoredCvs[0]]} />);

    const expected = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(
      new Date(tailoredCvs[0].updated_at),
    );
    expect(within(screen.getByTestId('tailored-cv-row-tc-1')).getByText(expected)).toBeInTheDocument();
  });

  it('defaults to Last Updated descending sort (most recent first)', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    const rows = screen.getAllByTestId(/^tailored-cv-row-/);
    expect(rows[0]).toHaveAttribute('data-testid', 'tailored-cv-row-tc-1');
    expect(rows[1]).toHaveAttribute('data-testid', 'tailored-cv-row-tc-2');
  });

  it('sorts rows by column click and keyboard activation with aria-sort updates', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    const titleHeader = within(table()).getByRole('columnheader', { name: /Title/ });
    const titleButton = within(titleHeader).getByRole('button', { name: /Title/ });

    fireEvent.click(titleButton);
    expect(titleHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(screen.getAllByTestId(/^tailored-cv-row-/)[0]).toHaveAttribute('data-testid', 'tailored-cv-row-tc-1');

    fireEvent.keyDown(titleButton, { key: ' ' });
    expect(titleHeader).toHaveAttribute('aria-sort', 'descending');
    expect(screen.getAllByTestId(/^tailored-cv-row-/)[0]).toHaveAttribute('data-testid', 'tailored-cv-row-tc-2');

    const statusHeader = within(table()).getByRole('columnheader', { name: /Status/ });
    fireEvent.click(within(statusHeader).getByRole('button', { name: /Status/ }));
    expect(statusHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(titleHeader).not.toHaveAttribute('aria-sort');
  });

  it('filters rows by search across title and language and shows empty-search state', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    fireEvent.change(screen.getByTestId('tailored-cvs-list-table-search'), { target: { value: 'hebrew' } });
    expect(screen.getByTestId('tailored-cv-row-tc-2')).toBeInTheDocument();
    expect(screen.queryByTestId('tailored-cv-row-tc-1')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('tailored-cvs-list-table-search'), { target: { value: 'zzznomatch' } });
    expect(within(table()).getByText('No matching tailored CVs')).toBeInTheDocument();
  });

  it('renders loading, error (+ retry), and empty states inside the table card', () => {
    const onRetry = vi.fn();
    const { rerender } = render(<TailoredCVsListTable tailoredCvs={tailoredCvs} isLoading />);

    expect(screen.getAllByTestId('tailored-cvs-list-table-skeleton-row')).toHaveLength(3);
    expect(screen.queryByTestId('tailored-cv-row-tc-1')).not.toBeInTheDocument();

    rerender(<TailoredCVsListTable tailoredCvs={[]} error="Could not load tailored CVs" onRetry={onRetry} />);
    expect(within(table()).getByText('Could not load tailored CVs')).toBeInTheDocument();
    fireEvent.click(within(table()).getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<TailoredCVsListTable tailoredCvs={[]} />);
    expect(within(table()).getByRole('link', { name: 'application' })).toHaveAttribute('href', '/applications');
  });

  it('renders responsive card-style row markup with all five field labels', () => {
    render(<TailoredCVsListTable tailoredCvs={[tailoredCvs[0]]} />);

    const row = screen.getByTestId('tailored-cv-row-tc-1');
    expect(row.className).toContain('block');
    expect(row.className).toContain('md:table-row');
    expect(within(row).getByText('Title')).toBeInTheDocument();
    expect(within(row).getByText('Language')).toBeInTheDocument();
    expect(within(row).getByText('Last Updated')).toBeInTheDocument();
    expect(within(row).getByText('Status')).toBeInTheDocument();
    expect(within(row).getByText('Action')).toBeInTheDocument();
  });

  it('renders Hebrew labels from the document locale', () => {
    document.documentElement.lang = 'he';

    const { rerender } = render(<TailoredCVsListTable tailoredCvs={[tailoredCvs[0]]} />);

    expect(within(table()).getByRole('columnheader', { name: 'כותרת' })).toBeInTheDocument();
    expect(screen.getByTestId('tailored-cvs-list-table-search')).toHaveAttribute('placeholder', 'חיפוש לפי כותרת או שפה');
    expect(within(screen.getByTestId('tailored-cv-row-tc-1')).getByRole('link', { name: 'צפייה' })).toBeInTheDocument();
    expect(within(screen.getByTestId('tailored-cv-row-tc-1')).getByText('מוכן')).toBeInTheDocument();

    rerender(<TailoredCVsListTable tailoredCvs={[]} />);
    expect(within(table()).getByRole('link', { name: 'הגשה' })).toHaveAttribute('href', '/applications');
  });

  it('includes the cv artifact id as ?id= in the View link href (regression: id was absent)', () => {
    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    for (const cv of tailoredCvs) {
      const link = within(screen.getByTestId(`tailored-cv-row-${cv.id}`)).getByRole('link', { name: /View|צפייה/ });
      expect(link).toHaveAttribute('href', `/applications/${cv.applicationId}/cv-tailored?id=${cv.id}`);
    }
  });

  it('does not call GET /cv-tailorings directly from the table component', () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response('[]', { status: 200 })));
    vi.stubGlobal('fetch', fetchMock);

    render(<TailoredCVsListTable tailoredCvs={tailoredCvs} />);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
