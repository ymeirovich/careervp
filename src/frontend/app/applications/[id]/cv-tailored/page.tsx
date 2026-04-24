'use client';

import React, { useState, useEffect, use, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { Spinner } from '../../../../components/ui/Spinner';
import type { CVTailoredStatusResponse, CVSections, JobDetail } from '../../../../lib/types';

function formatDateRange(start: string, end?: string | null, isCurrent?: boolean): string {
  const endLabel = isCurrent || !end || end === 'Present' ? 'Present' : end;
  return start ? `${start} – ${endLabel}` : endLabel ?? '';
}

function buildCopyText(cv: CVSections): string {
  const c = cv.contact;
  const contactLine = [c.email, c.phone, c.linkedin, c.location].filter(Boolean).join(' | ');
  const lines: string[] = [c.name, contactLine, '', 'PROFESSIONAL SUMMARY', cv.summary, ''];
  if (cv.skills.technical.length > 0) {
    lines.push('CORE COMPETENCIES', cv.skills.technical.join(' | '), '');
  }
  if (cv.experience.length > 0) {
    lines.push('PROFESSIONAL EXPERIENCE');
    for (const exp of cv.experience) {
      lines.push(`${exp.title} | ${exp.company} | ${formatDateRange(exp.start_date, exp.end_date, exp.is_current)}`);
      for (const b of exp.bullets) lines.push(`  • ${b.text}`);
      lines.push('');
    }
  }
  if (cv.education.length > 0) {
    lines.push('EDUCATION');
    for (const edu of cv.education) {
      lines.push(`${edu.degree} in ${edu.field} | ${edu.institution}${edu.graduation_date ? ` | ${edu.graduation_date}` : ''}`);
    }
    lines.push('');
  }
  return lines.join('\n').trim();
}

function CVDocument({ cv }: { cv: CVSections }) {
  const c = cv.contact;
  const contactParts = [c.email, c.phone, c.linkedin, c.location].filter(Boolean);
  return (
    <div className="flex flex-col gap-6 font-sans">
      <div className="text-center border-b border-border-default pb-4">
        <h1 className="text-xl font-bold text-text-primary tracking-wide uppercase">{c.name}</h1>
        {contactParts.length > 0 && (
          <p className="text-sm text-text-muted mt-1">{contactParts.join(' | ')}</p>
        )}
      </div>
      <section>
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Professional Summary</h2>
        <p className="text-sm text-text-secondary leading-relaxed">{cv.summary}</p>
      </section>
      {cv.skills.technical.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Core Competencies</h2>
          <p className="text-sm text-text-secondary">{cv.skills.technical.join(' | ')}</p>
        </section>
      )}
      {cv.experience.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-3">Professional Experience</h2>
          <div className="flex flex-col gap-4">
            {cv.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold text-text-primary">{exp.title} | {exp.company}</span>
                  <span className="text-xs text-text-muted shrink-0">{formatDateRange(exp.start_date, exp.end_date, exp.is_current)}</span>
                </div>
                <ul className="mt-1 flex flex-col gap-1">
                  {exp.bullets.map((b, j) => (
                    <li key={j} className="flex gap-2 text-sm text-text-secondary">
                      <span className="shrink-0 mt-0.5">•</span>
                      <span className="leading-relaxed">{b.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}
      {cv.education.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Education</h2>
          <div className="flex flex-col gap-1">
            {cv.education.map((edu, i) => (
              <div key={i} className="flex items-start justify-between gap-2">
                <span className="text-sm text-text-secondary">
                  <span className="font-medium">{edu.degree}</span> in {edu.field} | {edu.institution}
                </span>
                {edu.graduation_date && <span className="text-xs text-text-muted shrink-0">{edu.graduation_date}</span>}
              </div>
            ))}
          </div>
        </section>
      )}
      {cv.certifications.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Certifications</h2>
          <ul className="flex flex-col gap-1">
            {cv.certifications.map((cert, i) => (
              <li key={i} className="flex gap-2 text-sm text-text-secondary">
                <span className="shrink-0 mt-0.5">•</span>
                <span>{cert.name}{cert.issuer && <span className="text-text-muted"> | {cert.issuer}</span>}{cert.date && <span className="text-text-muted"> | {cert.date}</span>}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function CVTailoredContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');

  const [data, setData] = useState<CVTailoredStatusResponse | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const init = async () => {
      const resolvedArtifactId = queryId;
      if (!resolvedArtifactId) {
        router.replace(`/applications/${jobId}`);
        return;
      }
      setLoading(true);
      const [cvResult, jobResult] = await Promise.allSettled([
        api.getCVTailored(resolvedArtifactId),
        api.getJob(jobId),
      ]);

      const cvData = cvResult.status === 'fulfilled' ? cvResult.value : null;
      const jobData = jobResult.status === 'fulfilled' ? jobResult.value : null;
      setJob(jobData);

      if (!cvData || cvData.status !== 'completed') {
        router.replace(`/applications/${jobId}`);
        return;
      }
      setArtifactId(resolvedArtifactId);
      setData(cvData);
      setLoading(false);
    };
    void init();
  }, [jobId, queryId, router]);

  const result = data?.result;
  const cvSections = result?.cv_sections;
  const atsScore = result?.ats_score;
  const atsGrade = result?.ats_grade;
  const keywordsMatched = result?.keywords_matched ?? result?.keyword_matches?.matched ?? [];
  const keywordsMissing = result?.keywords_missing ?? result?.keyword_matches?.missing ?? [];

  const atsColorClass = atsGrade === 'green' ? 'bg-state-success' : atsGrade === 'yellow' ? 'bg-state-warning' : 'bg-state-error';

  const handleCopy = async () => {
    const text = cvSections ? buildCopyText(cvSections) : (result?.tailored_cv ?? '');
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Tailored CV…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl" data-testid="cv-tailored-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold text-text-primary">Tailored CV</h1>
          {job && <p className="text-sm text-text-muted">{job.title} · {job.company_name}</p>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {artifactId && (
            <ExportDropdown jobId={jobId} moduleType="cv_tailored" artifactId={artifactId} />
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-bg-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {atsScore !== undefined && (
        <div className="rounded-md border border-border-default bg-card p-6 flex items-start gap-8" data-testid="ats-score">
          <div className="flex flex-col items-center gap-1 shrink-0">
            <span className={`inline-flex items-center justify-center w-14 h-14 rounded-full text-white font-bold text-xl ${atsColorClass}`}>
              {atsScore}
            </span>
            <span className="text-xs text-text-muted">ATS Score</span>
          </div>
          <div className="flex flex-col gap-2 flex-1 min-w-0">
            {keywordsMatched.length > 0 && (
              <div data-testid="keyword-matched-list">
                <span className="text-xs font-semibold text-state-success">Matched: </span>
                <span className="text-xs text-text-muted">{keywordsMatched.join(', ')}</span>
              </div>
            )}
            {keywordsMissing.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-state-error">Missing: </span>
                <span className="text-xs text-text-muted">{keywordsMissing.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {cvSections ? (
        <div className="rounded-md border border-border-default bg-card p-8 flex flex-col gap-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-bold text-text-primary">Tailored CV</h2>
            <button
              onClick={() => void handleCopy()}
              className="text-xs font-medium text-text-muted hover:text-text-primary transition-colors"
            >
              {copied ? 'Copied ✓' : 'Copy to clipboard'}
            </button>
          </div>
          <CVDocument cv={cvSections} />
        </div>
      ) : result?.tailored_cv ? (
        <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-text-primary">Tailored CV</h2>
            <button onClick={() => void handleCopy()} className="text-xs font-medium text-text-muted hover:text-text-primary transition-colors">
              {copied ? 'Copied ✓' : 'Copy to clipboard'}
            </button>
          </div>
          <pre className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap font-sans">{result.tailored_cv}</pre>
        </div>
      ) : null}
    </div>
  );
}

export default function CVTailoredPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  return (
    <ErrorBoundary cloudwatchKey="cv-tailored-page">
      <Suspense fallback={<div className="flex justify-center py-12"><Spinner size="lg" aria-label="Loading…" /></div>}>
        <CVTailoredContent jobId={jobId} />
      </Suspense>
    </ErrorBoundary>
  );
}
