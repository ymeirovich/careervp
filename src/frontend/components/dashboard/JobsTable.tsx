import React from 'react';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

type JobStatus = 'active' | 'draft' | 'archived';

interface Job {
  id: string;
  title: string;
  company: string;
  status: JobStatus;
  updatedAt: string;
}

interface JobsTableProps {
  jobs: Job[];
  onViewJob?: (jobId: string) => void;
  onNewApplication?: () => void;
}

const STATUS_BADGE_VARIANT: Record<JobStatus, 'success' | 'neutral'> = {
  active: 'success',
  draft: 'neutral',
  archived: 'neutral',
};

const STATUS_LABEL: Record<JobStatus, string> = {
  active: 'Active',
  draft: 'Draft',
  archived: 'Archived',
};

export function JobsTable({ jobs, onViewJob, onNewApplication }: JobsTableProps) {
  return (
    <div className="bg-card border border-border-default rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div className="flex items-center gap-3">
          <h2 className="font-bold text-text-primary text-2xl">Most Recent Jobs</h2>
          <button className="text-primary-action text-base font-normal hover:underline">
            View All
          </button>
        </div>
        <Button variant="primary" size="md" onClick={onNewApplication}>
          + New Application
        </Button>
      </div>

      <div>
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] bg-surface-subtle border-b border-border-default px-4 py-3">
          {['Job Title', 'Company', 'Status', 'Updated', 'Action'].map((col) => (
            <span key={col} className="text-text-muted text-base font-medium">{col}</span>
          ))}
        </div>

        {jobs.length === 0 ? (
          <div className="px-4 py-10 text-center text-text-muted text-base">
            No applications yet. Click <strong>+ New Application</strong> to get started.
          </div>
        ) : (
          jobs.map((job, i) => (
            <div
              key={job.id}
              data-testid={`job-card-${job.id}`}
              className={`grid grid-cols-[2fr_1fr_1fr_1fr_1fr] items-center px-4 py-4 ${
                i < jobs.length - 1 ? 'border-b border-border-default' : ''
              }`}
            >
              <span className="text-text-primary text-base font-medium">{job.title}</span>
              <span className="text-text-primary text-base font-medium">{job.company}</span>
              <div>
                <Badge variant={STATUS_BADGE_VARIANT[job.status]}>
                  {STATUS_LABEL[job.status]}
                </Badge>
              </div>
              <span className="text-text-primary text-base font-medium">{job.updatedAt}</span>
              <div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onViewJob?.(job.id)}
                >
                  View
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
