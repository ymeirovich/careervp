import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { BaseCVsTable, type BaseCVListItem } from '../../../components/BaseCVsTable';

const apiResponse: { cvs: BaseCVListItem[] } = {
  cvs: [
    {
      cv_id: 'cv-1',
      full_name: 'Zoe Backend CV',
      language: 'English',
      created_at: '2026-05-01T08:00:00Z',
      updated_at: '2026-05-20T10:00:00Z',
      status: 'ready',
      used_in: ['SysAid Backend Engineer'],
    },
    {
      cv_id: 'cv-2',
      full_name: 'Ari Product CV',
      language: 'Hebrew',
      created_at: '2026-04-20T08:00:00Z',
      updated_at: '2026-05-25T09:00:00Z',
      status: 'processing',
      used_in_count: 2,
    },
    {
      cv_id: 'cv-3',
      full_name: 'Maya Data CV',
      language: 'English',
      created_at: '2026-04-25T08:00:00Z',
      updated_at: '2026-05-10T08:00:00Z',
      status: 'failed',
      applications_count: 0,
    },
    {
      cv_id: 'cv-4',
      full_name: 'No Status CV',
      language: 'English',
      created_at: '2026-04-28T08:00:00Z',
      updated_at: '2026-05-12T08:00:00Z',
    },
  ],
};

afterEach(() => {
  document.documentElement.lang = 'en';
  vi.unstubAllGlobals();
});

function table() {
  return screen.getByTestId('base-cvs-table');
}

describe('BaseCVsTable', () => {
  it('renders semantic table markup with seven scoped column headers in order', () => {
    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    expect(table().tagName).toBe('TABLE');
    const headers = within(table()).getAllByRole('columnheader');

    expect(headers).toHaveLength(7);
    expect(headers.map((header) => header.textContent?.replace(/[▲▼]/g, '').trim())).toEqual([
      'File Name',
      'Upload Date',
      'Language',
      'Last Updated',
      'Status',
      'Used In',
      'Actions',
    ]);
    headers.forEach((header) => expect(header).toHaveAttribute('scope', 'col'));
  });

  it('maps API fields to cells, formats both date columns, and renders Used In fallbacks', () => {
    render(<BaseCVsTable cvs={[apiResponse.cvs[0], apiResponse.cvs[3]]} />);

    const firstRow = screen.getByTestId('base-cv-row-cv-1');
    const expectedCreated = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(
      new Date(apiResponse.cvs[0].created_at ?? ''),
    );
    const expectedUpdated = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(
      new Date(apiResponse.cvs[0].updated_at ?? ''),
    );

    expect(within(firstRow).getByText('Zoe Backend CV')).toBeInTheDocument();
    expect(within(firstRow).getByText('English')).toBeInTheDocument();
    expect(within(firstRow).getByText(expectedCreated)).toBeInTheDocument();
    expect(within(firstRow).getByText(expectedUpdated)).toBeInTheDocument();
    expect(within(firstRow).getByText('SysAid Backend Engineer')).toBeInTheDocument();
    expect(within(screen.getByTestId('base-cv-row-cv-4')).getByText('—')).toBeInTheDocument();
  });

  it('renders zebra striping, hover highlight, and a bold underlined-on-hover View link', () => {
    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    expect(screen.getByTestId('base-cv-row-cv-2').className).toContain('bg-white');
    expect(screen.getByTestId('base-cv-row-cv-1').className).toContain('bg-surface-subtle');
    expect(screen.getByTestId('base-cv-row-cv-2').className).toContain('hover:bg-surface-selected');

    const viewLink = within(screen.getByTestId('base-cv-row-cv-2')).getByRole('link', { name: 'View' });
    expect(viewLink.className).toContain('font-bold');
    expect(viewLink.className).toContain('hover:underline');
    expect(viewLink.className).toContain('group-hover:underline');
    expect(viewLink).toHaveAttribute('href', '/cv-center/cv-2');
  });

  it('maps ready, missing, processing, and failed statuses to soft status badges', () => {
    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    const readyBadge = within(screen.getByTestId('base-cv-row-cv-1')).getByText('Ready');
    const missingStatusBadge = within(screen.getByTestId('base-cv-row-cv-4')).getByText('Ready');
    const processingBadge = within(screen.getByTestId('base-cv-row-cv-2')).getByText('Processing');
    const failedBadge = within(screen.getByTestId('base-cv-row-cv-3')).getByText('Failed');

    expect(readyBadge.className).toContain('bg-green-50');
    expect(missingStatusBadge.className).toContain('bg-green-50');
    expect(processingBadge.className).toContain('bg-blue-50');
    expect(failedBadge.className).toContain('bg-state-error');
  });

  it('renders Set as Default, Delete, and View actions and calls action callbacks with the CV id', () => {
    const onSetDefault = vi.fn();
    const onDelete = vi.fn();

    render(<BaseCVsTable cvs={[apiResponse.cvs[0]]} onSetDefault={onSetDefault} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: 'Set as Default' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(onSetDefault).toHaveBeenCalledWith('cv-1');
    expect(onDelete).toHaveBeenCalledWith('cv-1');
    expect(screen.getByRole('link', { name: 'View' })).toHaveAttribute('href', '/cv-center/cv-1');
  });

  it('defaults to Last Updated descending sort and toggles sorting by click and keyboard', () => {
    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    const initialRows = screen.getAllByTestId(/^base-cv-row-/);
    expect(initialRows[0]).toHaveAttribute('data-testid', 'base-cv-row-cv-2');
    expect(initialRows[1]).toHaveAttribute('data-testid', 'base-cv-row-cv-1');

    const fileNameHeader = within(table()).getByRole('columnheader', { name: /File Name/ });
    const fileNameButton = within(fileNameHeader).getByRole('button', { name: /File Name/ });

    fireEvent.click(fileNameButton);
    expect(fileNameHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(screen.getAllByTestId(/^base-cv-row-/)[0]).toHaveAttribute('data-testid', 'base-cv-row-cv-2');

    fireEvent.keyDown(fileNameButton, { key: 'Enter' });
    expect(fileNameHeader).toHaveAttribute('aria-sort', 'descending');
    expect(screen.getAllByTestId(/^base-cv-row-/)[0]).toHaveAttribute('data-testid', 'base-cv-row-cv-1');

    const usedInHeader = within(table()).getByRole('columnheader', { name: /Used In/ });
    fireEvent.click(within(usedInHeader).getByRole('button', { name: /Used In/ }));
    expect(usedInHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(fileNameHeader).not.toHaveAttribute('aria-sort');
  });

  it('makes every column header sortable by exposing a focusable sort button', () => {
    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    const headers = within(table()).getAllByRole('columnheader');
    headers.forEach((header) => {
      expect(within(header).getByRole('button')).toBeInTheDocument();
    });
  });

  it('renders loading, error with retry, and empty states inside the table card', () => {
    const onRetry = vi.fn();
    const onUploadNew = vi.fn();
    const { rerender } = render(<BaseCVsTable cvs={apiResponse.cvs} isLoading />);

    expect(screen.getAllByTestId('base-cvs-table-skeleton-row')).toHaveLength(3);
    expect(screen.queryByTestId('base-cv-row-cv-1')).not.toBeInTheDocument();

    rerender(<BaseCVsTable cvs={[]} error="Could not load base CVs" onRetry={onRetry} />);
    expect(within(table()).getByText('Could not load base CVs')).toBeInTheDocument();
    fireEvent.click(within(table()).getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<BaseCVsTable cvs={[]} onUploadNew={onUploadNew} />);
    expect(within(table()).getByText('No primary CVs uploaded yet')).toBeInTheDocument();
    fireEvent.click(within(table()).getByRole('button', { name: '+ Upload New CV' }));
    expect(onUploadNew).toHaveBeenCalledTimes(1);
  });

  it('renders responsive card-style row markup with all seven field labels', () => {
    render(<BaseCVsTable cvs={[apiResponse.cvs[0]]} />);

    const row = screen.getByTestId('base-cv-row-cv-1');
    expect(row.className).toContain('block');
    expect(row.className).toContain('md:table-row');
    expect(within(row).getByText('File Name')).toBeInTheDocument();
    expect(within(row).getByText('Upload Date')).toBeInTheDocument();
    expect(within(row).getByText('Language')).toBeInTheDocument();
    expect(within(row).getByText('Last Updated')).toBeInTheDocument();
    expect(within(row).getByText('Status')).toBeInTheDocument();
    expect(within(row).getByText('Used In')).toBeInTheDocument();
    expect(within(row).getByText('Actions')).toBeInTheDocument();
  });

  it('renders Hebrew labels from the document locale', () => {
    document.documentElement.lang = 'he';

    const { rerender } = render(<BaseCVsTable cvs={[apiResponse.cvs[0]]} />);

    expect(within(table()).getByRole('columnheader', { name: /שם הקובץ/ })).toBeInTheDocument();
    expect(within(screen.getByTestId('base-cv-row-cv-1')).getByRole('link', { name: 'צפייה' })).toBeInTheDocument();
    expect(within(screen.getByTestId('base-cv-row-cv-1')).getByText('מוכן')).toBeInTheDocument();
    expect(within(screen.getByTestId('base-cv-row-cv-1')).getByRole('button', { name: 'הגדר כברירת מחדל' })).toBeInTheDocument();
    expect(within(screen.getByTestId('base-cv-row-cv-1')).getByRole('button', { name: 'מחיקה' })).toBeInTheDocument();

    rerender(<BaseCVsTable cvs={[]} />);
    expect(within(table()).getByText('לא הועלו עדיין קורות חיים ראשיים')).toBeInTheDocument();
    expect(within(table()).getByRole('button', { name: '+ העלאת קורות חיים חדשים' })).toBeInTheDocument();

    rerender(<BaseCVsTable cvs={[]} error="טעינת קורות החיים הבסיסיים נכשלה." />);
    expect(within(table()).getByRole('button', { name: 'נסה שוב' })).toBeInTheDocument();
  });

  it('does not call GET /users/me/cv directly from the table component', () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(apiResponse), { status: 200 })));
    vi.stubGlobal('fetch', fetchMock);

    render(<BaseCVsTable cvs={apiResponse.cvs} />);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
