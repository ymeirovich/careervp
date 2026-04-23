'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useJobs } from '../../hooks/useJobs';
import { Button } from '../ui/Button';

interface NewApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NewApplicationModal({ isOpen, onClose }: NewApplicationModalProps) {
  const router = useRouter();
  const { createJob, isCreating } = useJobs();

  const [title, setTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [description, setDescription] = useState('');
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const job = await createJob({
        title,
        company_name: companyName,
        description,
        url: url || undefined,
      });
      router.push(`/applications/${job.job_id}`);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create application');
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="New Application"
      data-testid="new-application-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div className="bg-card border border-border-default rounded-xl p-6 w-full max-w-lg shadow-lg">
        <h2 className="text-text-primary font-bold text-xl mb-5">New Application</h2>
        <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="new-app-title" className="text-text-primary text-sm font-medium">
              Job Title <span aria-hidden="true">*</span>
            </label>
            <input
              id="new-app-title"
              data-testid="new-app-title-input"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-text-primary bg-surface-subtle text-sm"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="new-app-company" className="text-text-primary text-sm font-medium">
              Company Name <span aria-hidden="true">*</span>
            </label>
            <input
              id="new-app-company"
              data-testid="new-app-company-input"
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-text-primary bg-surface-subtle text-sm"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="new-app-description" className="text-text-primary text-sm font-medium">
              Job Description <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="new-app-description"
              data-testid="new-app-description-input"
              required
              rows={5}
              placeholder="Paste the full job posting here"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-text-primary bg-surface-subtle text-sm resize-none"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="new-app-url" className="text-text-primary text-sm font-medium">
              Job URL
            </label>
            <input
              id="new-app-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-text-primary bg-surface-subtle text-sm"
            />
          </div>

          {error && <p className="text-state-error text-sm">{error}</p>}

          <div className="flex justify-end gap-3 mt-2">
            <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={isCreating}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" isLoading={isCreating}>
              Create Application
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
