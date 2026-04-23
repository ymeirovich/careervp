'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useJobs } from '../../hooks/useJobs';
import { useDashboard } from '../../contexts/DashboardContext';
import { StatsRow } from '../../components/dashboard/StatsRow';
import { JobsTable } from '../../components/dashboard/JobsTable';
import { UsageGate } from '../../components/UsageGate/UsageGate';
import { NewApplicationModal } from '../../components/NewApplicationModal/NewApplicationModal';
import { EmptyState } from '../../components/ui/EmptyState';
import { Button } from '../../components/ui/Button';

export default function DashboardPage() {
  const router = useRouter();
  const { jobs, isLoading } = useJobs();
  const { usage, subscription, hasActiveAccess } = useDashboard();
  const [isModalOpen, setIsModalOpen] = useState(false);

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
      />

      <div className="flex justify-end">
        <UsageGate action="new_application">
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsModalOpen(true)}
            data-testid="new-application-btn"
          >
            + New Application
          </Button>
        </UsageGate>
      </div>

      {jobs.length === 0 && !isLoading ? (
        <EmptyState
          title="No applications yet"
          description="Create your first application to get started with CareerVP."
        />
      ) : (
        <div data-testid="jobs-table">
          <JobsTable
            jobs={mappedJobs}
            onViewJob={(id) => router.push(`/applications/${id}`)}
            onNewApplication={() => setIsModalOpen(true)}
          />
        </div>
      )}

      <NewApplicationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
