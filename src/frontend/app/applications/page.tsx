'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { JobsTable } from '../../components/dashboard/JobsTable';
import { useJobs } from '../../hooks/useJobs';

export default function ApplicationsPage() {
  const router = useRouter();
  const { jobs, isLoading, error, refetch } = useJobs();

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
    <JobsTable
      mode="full-list"
      jobs={mappedJobs}
      isLoading={isLoading}
      error={error}
      onRetry={refetch}
      onViewJob={(id) => router.push(`/applications/${id}`)}
      onNewApplication={() => router.push('/applications/new')}
    />
  );
}
