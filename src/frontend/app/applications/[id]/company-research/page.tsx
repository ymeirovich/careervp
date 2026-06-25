'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../../components/ui/Spinner';
import type { CompanyResearchResult } from '../../../../lib/types';

function CompanyResearchContent({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [research, setResearch] = useState<CompanyResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [pollMessage, setPollMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string>('');

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const [data, appData] = await Promise.all([
          api.getCompanyResearch(jobId),
          api.getApplication(jobId),
        ]);
        setResearch(data);
        setCompanyName(appData?.job?.company_name ?? '');
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId]);

  const handleTrigger = async () => {
    setTriggering(true);
    setError(null);
    setPollMessage(null);
    try {
      await api.fetchCompanyResearch({ job_id: jobId, company_name: companyName });

      const POLL_INTERVAL_MS = 10_000;
      const MAX_ATTEMPTS = 30; // 30 × 10 s = 5 minutes

      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        setPollMessage(`Researching… checking for results (attempt ${attempt} of ${MAX_ATTEMPTS})`);
        await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

        const { status, data } = await api.getCompanyResearchStatus(jobId);

        if (status === 'completed' && data) {
          setResearch(data);
          return;
        }

        if (status === 'failed' || status === 'not_generated') {
          setError('Company research failed on the server. Please try again.');
          return;
        }
      }

      setError('Research is taking longer than expected. Please refresh the page in a few minutes.');
    } catch (err) {
      setError('Failed to research company. Please try again.');
      console.error(err);
    } finally {
      setTriggering(false);
      setPollMessage(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Company Research…" />
      </div>
    );
  }

  const CARD = 'rounded-md border border-border-default bg-card p-6 flex flex-col gap-4';
  const TITLE = 'text-base font-bold text-text-primary';
  const LABEL = 'text-xs font-semibold uppercase tracking-wide text-text-muted';
  const BODY = 'text-sm text-text-primary leading-relaxed';

  // Backend response shape varies across canonical/legacy stores; these arrays
  // may be missing or null. Normalize so rendering never crashes on `.length`.
  const values = research?.values ?? [];
  const products = research?.products ?? [];
  const recentNews = (research?.recent_news ?? []).map((item) =>
    typeof item === 'string' ? { title: item } : item,
  );

  return (
    <div className="flex flex-col gap-6" data-testid="company-research-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-text-primary">Company Research</h1>
          <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-state-info/10 text-state-info">Beta</span>
        </div>
        <button
          onClick={() => router.push(`/applications/${jobId}`)}
          className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
        >
          ← Back to Hub
        </button>
      </div>

      <p className="text-xs text-text-muted">Content is AI-researched and may be incomplete or outdated.</p>

      {error && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {error}
        </div>
      )}

      {!research ? (
        <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center flex flex-col items-center gap-4">
          <p className="text-sm text-text-muted">No company research available yet.</p>
          <button
            onClick={() => void handleTrigger()}
            disabled={triggering}
            className="rounded-md bg-primary-action px-4 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
            data-testid="research-company-btn"
          >
            {triggering ? 'Researching…' : 'Research this company'}
          </button>
          {pollMessage && (
            <p className="text-xs text-text-muted" data-testid="poll-message">{pollMessage}</p>
          )}
        </div>
      ) : (
        <>
          <div className={CARD}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className={TITLE}>{research.company_name ?? 'Company'}</h2>
                <div className="flex gap-2 mt-1 flex-wrap">
                  {research.industry && <span className="text-xs text-text-muted">{research.industry}</span>}
                  {research.size_range && <span className="text-xs text-text-muted">· {research.size_range}</span>}
                  {research.funding_status && <span className="text-xs text-text-muted">· {research.funding_status}</span>}
                </div>
              </div>
            </div>
            {research.mission && (
              <div>
                <p className={LABEL}>Mission</p>
                <p className={BODY}>{research.mission}</p>
              </div>
            )}
          </div>

          {values.length > 0 && (
            <div className={CARD}>
              <h2 className={TITLE}>Values</h2>
              <ul className="flex flex-col gap-1">
                {values.map((v, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-primary">
                    <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-primary-action" />
                    {v}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {research.culture && (
            <div className={CARD}>
              <h2 className={TITLE}>Culture & Environment</h2>
              <p className={BODY}>{research.culture}</p>
            </div>
          )}

          {products.length > 0 && (
            <div className={CARD}>
              <h2 className={TITLE}>Products & Services</h2>
              <ul className="flex flex-col gap-1">
                {products.map((p, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-primary">
                    <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-primary-action" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recentNews.length > 0 && (
            <div className={CARD}>
              <h2 className={TITLE}>Recent News</h2>
              <div className="flex flex-col gap-3">
                {recentNews.map((item, i) => (
                  <div key={i} className="flex items-start justify-between gap-3">
                    <p className="text-sm text-text-primary">{item.title}</p>
                    {item.date && <span className="text-xs text-text-muted shrink-0">{item.date}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function CompanyResearchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  return (
    <ErrorBoundary cloudwatchKey="company-research-page">
      <CompanyResearchContent jobId={jobId} />
    </ErrorBoundary>
  );
}
