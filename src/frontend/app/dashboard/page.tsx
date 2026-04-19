'use client';

import React from 'react';
import { StatsRow } from '../../components/dashboard/StatsRow';
import { JobsTable } from '../../components/dashboard/JobsTable';

// TODO: Wire to useApplicationHub hook (spec-03)
// TODO: Fetch user subscription data via TanStack Query

export default function DashboardPage() {
  // TODO: Replace with real data from hooks
  const mockJobs = [
    { id: 'job-001', title: 'Learning Experience Specialist', company: 'SysAid', status: 'active' as const, updatedAt: 'Mar 7, 2026' },
    { id: 'job-002', title: 'Senior Product Designer', company: 'TechCorp', status: 'draft' as const, updatedAt: 'Mar 5, 2026' },
    { id: 'job-003', title: 'UX Researcher', company: 'DesignLab', status: 'archived' as const, updatedAt: 'Feb 28, 2026' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <StatsRow
        plan="Free Tier"
        creditsUsed={1}
        creditsTotal={3}
        isActive={true}
      />
      <JobsTable
        jobs={mockJobs}
        onViewJob={(id) => {
          // TODO: Navigate to application hub
          console.log('View job', id);
        }}
        onNewApplication={() => {
          // TODO: Navigate to /applications/new
          console.log('New application');
        }}
      />
    </div>
  );
}
