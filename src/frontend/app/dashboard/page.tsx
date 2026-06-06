'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useJobs } from '../../hooks/useJobs';
import { useDashboard } from '../../contexts/DashboardContext';
import { StatsRow } from '../../components/dashboard/StatsRow';
import { JobsTable } from '../../components/dashboard/JobsTable';

export default function DashboardPage() {
  const router = useRouter();
  const { jobs, isLoading, error, refetch } = useJobs();
  const { usage, subscription, hasActiveAccess, isLoading: isDashboardLoading } = useDashboard();

  const planLabel =
    subscription?.subscription?.plan_type === 'monthly'
      ? 'Monthly Plan'
      : subscription?.subscription?.plan_type === 'annual'
      ? 'Annual Plan'
      : usage?.trial?.active
      ? 'Free Trial'
      : 'Free Tier';

  const creditsUsed = usage?.applications.used ?? 0;
  const creditsTotal = creditsUsed + (usage?.applications.remaining ?? 0);

  const mappedJobs = jobs.map((job) => ({
    id: job.job_id,
    title: job.title,
    company: job.company_name,
    status: (job.status as 'active' | 'draft' | 'archived') ?? 'draft',
    updatedAt: new Date(job.created_at).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
  }));

  return (
    <div className="flex flex-col gap-6">
      <StatsRow
        plan={planLabel}
        creditsUsed={creditsUsed}
        creditsTotal={creditsTotal || 3}
        isActive={hasActiveAccess}
        isLoading={Boolean(isDashboardLoading)}
      />

      <div data-testid="jobs-table">
        <JobsTable
          mode="dashboard"
          jobs={mappedJobs}
          isLoading={isLoading}
          error={error}
          onRetry={refetch}
          onViewJob={(id) => router.push(`/applications/${id}`)}
          onNewApplication={() => router.push('/applications/new')}
        />
      </div>
    </div>
  );
}
