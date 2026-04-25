'use client';

import React, { useState, useEffect, use, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { Spinner } from '../../../../components/ui/Spinner';
import type { JobDetail } from '../../../../lib/types';

function CoverLetterContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');

  const [fullText, setFullText] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, jobResult] = await Promise.allSettled([
        api.getApplication(jobId),
        api.getJob(jobId),
      ]);

      const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;
      const jobData = jobResult.status === 'fulfilled' ? jobResult.value : null;
      setJob(jobData);

      const resolvedArtifactId = hub?.artifacts.cover_letter?.artifact_id ?? queryId;
      const artifactStatus = hub?.artifacts.cover_letter?.status;

      if (!resolvedArtifactId || (artifactStatus && artifactStatus !== 'completed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      setArtifactId(resolvedArtifactId);

      try {
        const data = await api.getCoverLetter(resolvedArtifactId);
        const text = data.result?.cover_letter ?? null;
        setFullText(text);
        if (!text) router.replace(`/applications/${jobId}`);
      } catch (err) {
        setError('Failed to load cover letter.');
        console.error(err);
        throw err;
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId, queryId, router]);

  const handleCopy = async () => {
    if (!fullText) return;
    try {
      await navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Cover Letter…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6" data-testid="cover-letter-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold text-text-primary">Cover Letter</h1>
          {job && (
            <p className="text-sm text-text-muted">{job.title} · {job.company_name}</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => void handleCopy()}
            className="rounded-md bg-brand-primary px-3 py-2 text-sm font-bold text-white hover:opacity-90"
            data-testid="copy-to-clipboard"
          >
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </button>
          {artifactId && (
            <ExportDropdown jobId={jobId} moduleType="cover_letter" artifactId={artifactId} />
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-bg-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {copied && (
        <div className="rounded-md bg-state-success/10 border border-state-success px-4 py-3 text-sm font-medium text-state-success">
          Copied to clipboard
        </div>
      )}

      {fullText && (
        <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
          <h2 className="text-base font-bold text-text-primary">Cover Letter</h2>
          <p
            className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap"
            data-testid="cover-letter-text"
          >
            {fullText}
          </p>
        </div>
      )}
    </div>
  );
}

export default function CoverLetterPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  return (
    <ErrorBoundary cloudwatchKey="cover-letter-page">
      <Suspense fallback={<div className="flex justify-center py-12"><Spinner size="lg" aria-label="Loading…" /></div>}>
        <CoverLetterContent jobId={jobId} />
      </Suspense>
    </ErrorBoundary>
  );
}
