import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { JobsTable } from '../../../components/dashboard/JobsTable';

const jobs = [
  {
    id: 'job-1',
    title: 'Frontend Engineer',
    company: 'Acme',
    status: 'active' as const,
    updatedAt: 'May 1, 2026',
  },
  {
    id: 'job-2',
    title: 'Backend Engineer',
    company: 'Beta',
    status: 'draft' as const,
    updatedAt: 'May 3, 2026',
  },
  {
    id: 'job-3',
    title: 'Product Manager',
    company: 'Core',
    status: 'archived' as const,
    updatedAt: 'Apr 28, 2026',
  },
];

afterEach(() => {
  document.documentElement.lang = 'en';
});

function table() {
  return screen.getByTestId('jobs-table');
}

describe('JobsTable', () => {
  it('renders semantic table markup with scoped column headers', () => {
    render(<JobsTable jobs={jobs} mode="dashboard" />);

    expect(table().tagName).toBe('TABLE');
    const headers = within(table()).getAllByRole('columnheader');
    expect(headers).toHaveLength(5);
    headers.forEach((header) => expect(header).toHaveAttribute('scope', 'col'));
  });

  it('renders status badges with the required active, draft, and archived styles', () => {
    render(<JobsTable jobs={jobs} mode="dashboard" />);

    const activeBadge = within(screen.getByTestId('job-row-job-1')).getByText('Active');
    const draftBadge = within(screen.getByTestId('job-row-job-2')).getByText('Draft');
    const archivedBadge = within(screen.getByTestId('job-row-job-3')).getByText('Archived');

    expect(activeBadge.className).toContain('bg-state-active');
    expect(activeBadge.className).toContain('text-white');
    expect(draftBadge.className).toContain('bg-[#FED7AA]');
    expect(draftBadge.className).toContain('text-[#9A3412]');
    expect(archivedBadge.className).toContain('bg-[#D1D5DB]');
    expect(archivedBadge.className).toContain('text-[#374151]');
  });

  it('normalizes backend job status values before rendering badges', () => {
    render(
      <JobsTable
        jobs={[
          {
            id: 'job-completed',
            title: 'Learning Experience Specialist',
            company: 'SysAid2',
            status: 'COMPLETED',
            updatedAt: 'May 30, 2026',
          },
        ]}
        mode="full-list"
      />,
    );

    const row = screen.getByTestId('job-row-job-completed');
    expect(within(row).getByText('Active')).toBeInTheDocument();
    expect(within(row).getByText('Active').className).toContain('bg-green-50');
  });

  it('uses alternating row backgrounds and bold text-link View actions', () => {
    const onViewJob = vi.fn();
    render(<JobsTable jobs={jobs} mode="dashboard" onViewJob={onViewJob} />);

    expect(screen.getByTestId('job-row-job-1').className).toContain('bg-white');
    expect(screen.getByTestId('job-row-job-2').className).toContain('bg-surface-subtle');
    expect(screen.getByTestId('job-row-job-1').className).toContain('hover:bg-surface-selected');

    const viewButton = within(screen.getByTestId('job-row-job-1')).getByRole('button', { name: 'View' });
    expect(viewButton.className).toContain('font-bold');
    expect(viewButton.className).toContain('hover:underline');

    fireEvent.click(viewButton);
    expect(onViewJob).toHaveBeenCalledWith('job-1');
  });

  it('keeps dashboard mode compact with muted headers, View All, and no sorting/search', () => {
    render(<JobsTable jobs={jobs} mode="dashboard" />);

    expect(screen.getByRole('heading', { name: 'Most Recent Jobs' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View All' })).toBeInTheDocument();
    expect(screen.queryByTestId('jobs-table-search')).not.toBeInTheDocument();

    const titleHeader = within(table()).getByRole('columnheader', { name: 'Job Title' });
    expect(titleHeader.className).toContain('text-text-muted');
    expect(within(titleHeader).queryByRole('button')).not.toBeInTheDocument();
    expect(titleHeader).not.toHaveAttribute('aria-sort');
  });

  it('renders full-list mode with orange sortable headers, search, and no View All', () => {
    render(<JobsTable jobs={jobs} mode="full-list" />);

    expect(screen.getByRole('heading', { name: 'My Jobs' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View All' })).not.toBeInTheDocument();
    expect(screen.getByTestId('jobs-table-search')).toHaveAttribute('placeholder', 'Search by job title');

    const titleHeader = within(table()).getByRole('columnheader', { name: /Job Title/ });
    expect(titleHeader.className).toContain('text-primary-action');
    expect(within(titleHeader).getByRole('button', { name: /Job Title/ })).toBeInTheDocument();
  });

  it('fires the new application callback from the full-list header and empty CTA', () => {
    const onNewApplication = vi.fn();
    const { rerender } = render(<JobsTable jobs={jobs} mode="full-list" onNewApplication={onNewApplication} />);

    fireEvent.click(screen.getByRole('button', { name: '+ New Application' }));
    expect(onNewApplication).toHaveBeenCalledTimes(1);

    rerender(<JobsTable jobs={[]} mode="full-list" onNewApplication={onNewApplication} />);
    fireEvent.click(screen.getByTestId('jobs-table-empty-new-application'));
    expect(onNewApplication).toHaveBeenCalledTimes(2);
  });

  it('sorts full-list rows by column click and keyboard activation', () => {
    render(<JobsTable jobs={jobs} mode="full-list" />);

    const titleHeader = within(table()).getByRole('columnheader', { name: /Job Title/ });
    const titleButton = within(titleHeader).getByRole('button', { name: /Job Title/ });

    fireEvent.click(titleButton);
    expect(titleHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(screen.getAllByTestId(/^job-row-/)[0]).toHaveAttribute('data-testid', 'job-row-job-2');

    fireEvent.keyDown(titleButton, { key: 'Enter' });
    expect(titleHeader).toHaveAttribute('aria-sort', 'descending');
    expect(screen.getAllByTestId(/^job-row-/)[0]).toHaveAttribute('data-testid', 'job-row-job-3');

    const companyHeader = within(table()).getByRole('columnheader', { name: /Company/ });
    fireEvent.click(within(companyHeader).getByRole('button', { name: /Company/ }));
    expect(companyHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(titleHeader).not.toHaveAttribute('aria-sort');
  });

  it('filters full-list rows by job title and shows the empty-search state', () => {
    render(<JobsTable jobs={jobs} mode="full-list" />);

    fireEvent.change(screen.getByTestId('jobs-table-search'), { target: { value: 'front' } });
    expect(screen.getByTestId('job-row-job-1')).toBeInTheDocument();
    expect(screen.queryByTestId('job-row-job-2')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('jobs-table-search'), { target: { value: 'legal' } });
    expect(within(table()).getByText('No matching jobs')).toBeInTheDocument();
    expect(within(table()).queryByText('No applications yet')).not.toBeInTheDocument();
  });

  it('renders loading, error, and dashboard empty states inside the table card', () => {
    const onRetry = vi.fn();
    const { rerender } = render(<JobsTable jobs={jobs} isLoading />);

    expect(screen.getAllByTestId('jobs-table-skeleton-row')).toHaveLength(3);
    expect(screen.queryByTestId('job-row-job-1')).not.toBeInTheDocument();

    rerender(<JobsTable jobs={[]} error="Could not load jobs" onRetry={onRetry} />);
    expect(within(table()).getByText('Could not load jobs')).toBeInTheDocument();
    fireEvent.click(within(table()).getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<JobsTable jobs={[]} mode="dashboard" />);
    expect(within(table()).getByText('No applications yet. Click + New Application to get started.')).toBeInTheDocument();
  });

  it('renders responsive card-style row markup with all five field labels', () => {
    render(<JobsTable jobs={[jobs[0]]} mode="dashboard" />);

    const row = screen.getByTestId('job-row-job-1');
    expect(row.className).toContain('block');
    expect(row.className).toContain('md:table-row');
    expect(within(row).getByText('Job Title')).toBeInTheDocument();
    expect(within(row).getByText('Company')).toBeInTheDocument();
    expect(within(row).getByText('Status')).toBeInTheDocument();
    expect(within(row).getByText('Updated')).toBeInTheDocument();
    expect(within(row).getByText('Action')).toBeInTheDocument();
    expect(row.className).toContain('hover:bg-surface-selected');
  });

  it('renders Hebrew labels from the document locale in both modes', () => {
    document.documentElement.lang = 'he';
    const { rerender } = render(<JobsTable jobs={jobs} mode="dashboard" />);

    expect(screen.getByRole('heading', { name: 'המשרות האחרונות' })).toBeInTheDocument();
    expect(within(table()).getByRole('columnheader', { name: 'שם המשרה' })).toBeInTheDocument();
    expect(within(screen.getByTestId('job-row-job-1')).getByRole('button', { name: 'צפייה' })).toBeInTheDocument();

    rerender(<JobsTable jobs={jobs} mode="full-list" />);
    expect(screen.getByRole('heading', { name: 'המשרות שלי' })).toBeInTheDocument();
    expect(screen.getByTestId('jobs-table-search')).toHaveAttribute('placeholder', 'חיפוש לפי שם משרה');
  });
});
