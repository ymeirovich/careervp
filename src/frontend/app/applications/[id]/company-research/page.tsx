'use client';

import { useState, useEffect, useRef, use } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../../components/ui/Spinner';
import type { CompanyResearchResult } from '../../../../lib/types';

export function CompanyResearchContent({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [research, setResearch] = useState<CompanyResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [pollMessage, setPollMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string>('');
  const [jobPostingUrl, setJobPostingUrl] = useState<string | undefined>(undefined);
  const pollAttemptRef = useRef(0);

  // Mount effect: status-aware initialization (R1)
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const [statusResult, appData] = await Promise.all([
          api.getCompanyResearchStatus(jobId),
          api.getApplication(jobId),
        ]);
        setCompanyName(appData?.job?.company_name ?? '');
        setJobPostingUrl(appData?.job?.url ?? undefined);

        if (statusResult.status === 'completed' && statusResult.data) {
          setResearch(statusResult.data);
          setStatus('completed');
        } else if (statusResult.status === 'failed') {
          setError('Company research failed on the server. Please try again.');
          setStatus('failed');
        } else if (statusResult.status === 'processing') {
          setStatus('processing');
        } else {
          // not_generated or unknown: idle state, no error (R3 BUG-3 fix)
          setStatus('not_generated');
        }
      } catch (err) {
        console.error(err);
        setStatus('not_generated');
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId]);

  // Poll effect: keyed on [status, jobId] so it auto-starts when processing (R2)
  useEffect(() => {
    if (status !== 'processing') return;

    const MAX_ATTEMPTS = 30;
    const POLL_INTERVAL_MS = 10_000;
    pollAttemptRef.current = 0;

    const id = setInterval(async () => {
      try {
        const { status: newStatus, data } = await api.getCompanyResearchStatus(jobId);

        if (newStatus === 'completed' && data) {
          setResearch(data);
          setStatus('completed');
          setPollMessage(null);
        } else if (newStatus === 'failed') {
          setError('Company research failed on the server. Please try again.');
          setStatus('failed');
          setPollMessage(null);
        } else {
          pollAttemptRef.current += 1;
          if (pollAttemptRef.current >= MAX_ATTEMPTS) {
            clearInterval(id);
            setStatus('timed_out');
            setPollMessage('Still running — refresh later');
          } else {
            setPollMessage(
              `Researching… checking for results (attempt ${pollAttemptRef.current} of ${MAX_ATTEMPTS})`,
            );
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(id);
  }, [status, jobId]);

  // handleTrigger: POST only; poll loop owned by effect above (R2 BUG-2 fix)
  const handleTrigger = async () => {
    setTriggering(true);
    setError(null);
    setPollMessage(null);
    try {
      await api.fetchCompanyResearch({ job_id: jobId, company_name: companyName, url: jobPostingUrl });
      setStatus('processing');
    } catch (err) {
      setError('Failed to research company. Please try again.');
      console.error(err);
    } finally {
      setTriggering(false);
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

  // Status-driven content (R3)
  const renderContent = () => {
    if (status === 'completed' && research) {
      return (
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
      );
    }

    if (status === 'failed') {
      return (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {error ?? 'Company research failed on the server. Please try again.'}
        </div>
      );
    }

    if (status === 'processing') {
      return (
        <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center flex flex-col items-center gap-4">
          <Spinner size="lg" aria-label="Researching company…" />
          {pollMessage && (
            <p className="text-xs text-text-muted" data-testid="poll-message">{pollMessage}</p>
          )}
        </div>
      );
    }

    // not_generated or timed_out: idle card with CTA (R3 BUG-3 fix, R4)
    return (
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
    );
  };

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

      {renderContent()}
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
