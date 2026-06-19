'use client';

import React, { useState, useEffect, use, Suspense, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { RichTextEditor } from '../../../../components/RichTextEditor/RichTextEditor';
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

// ── Read-only document ──────────────────────────────────────────────────────

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

// ── Edit-mode document ──────────────────────────────────────────────────────

const editFieldClass =
  'w-full rounded border border-border-default bg-surface-subtle px-2 py-1 text-sm text-text-primary leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary-action/50 resize-none';

interface CVDocumentEditProps {
  cv: CVSections;
  onChange: (updated: CVSections) => void;
}

function CVDocumentEdit({ cv, onChange }: CVDocumentEditProps) {
  const c = cv.contact;

  const setContact = (field: keyof typeof c, value: string) =>
    onChange({ ...cv, contact: { ...c, [field]: value } });

  const setSummary = (value: string) => onChange({ ...cv, summary: value });

  const setSkillsTechnical = (value: string) =>
    onChange({ ...cv, skills: { ...cv.skills, technical: value.split(',').map((s) => s.trim()).filter(Boolean) } });

  const setBullet = (expIdx: number, bulletIdx: number, value: string) => {
    const experience = cv.experience.map((exp, i) => {
      if (i !== expIdx) return exp;
      return {
        ...exp,
        bullets: exp.bullets.map((b, j) =>
          j === bulletIdx ? { ...b, text: value } : b
        ),
      };
    });
    onChange({ ...cv, experience });
  };

  return (
    <div className="flex flex-col gap-6 font-sans">
      {/* Contact header */}
      <div className="border-b border-border-default pb-4 flex flex-col gap-2">
        <input
          type="text"
          value={c.name}
          onChange={(e) => setContact('name', e.target.value)}
          className={`${editFieldClass} text-center text-xl font-bold uppercase tracking-wide`}
          placeholder="Full Name"
        />
        <div className="grid grid-cols-2 gap-2">
          {(['email', 'phone', 'linkedin', 'location'] as const).map((field) => (
            <input
              key={field}
              type="text"
              value={c[field] ?? ''}
              onChange={(e) => setContact(field, e.target.value)}
              placeholder={field.charAt(0).toUpperCase() + field.slice(1)}
              className={editFieldClass}
            />
          ))}
        </div>
      </div>

      {/* Summary */}
      <section>
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Professional Summary</h2>
        <textarea
          value={cv.summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={4}
          className={editFieldClass}
        />
      </section>

      {/* Skills */}
      {cv.skills.technical.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Core Competencies</h2>
          <textarea
            value={cv.skills.technical.join(', ')}
            onChange={(e) => setSkillsTechnical(e.target.value)}
            rows={2}
            placeholder="Comma-separated skills"
            className={editFieldClass}
          />
          <p className="mt-1 text-xs text-text-muted">Separate skills with commas</p>
        </section>
      )}

      {/* Experience */}
      {cv.experience.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-3">Professional Experience</h2>
          <div className="flex flex-col gap-4">
            {cv.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="text-sm font-semibold text-text-primary">{exp.title} | {exp.company}</span>
                  <span className="text-xs text-text-muted shrink-0">{formatDateRange(exp.start_date, exp.end_date, exp.is_current)}</span>
                </div>
                <ul className="flex flex-col gap-1">
                  {exp.bullets.map((b, j) => (
                    <li key={j} className="flex gap-2">
                      <span className="shrink-0 mt-2 text-sm text-text-secondary">•</span>
                      <textarea
                        value={b.text}
                        onChange={(e) => setBullet(i, j, e.target.value)}
                        rows={2}
                        className={`${editFieldClass} flex-1`}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Education (read-only in edit mode per spec) */}
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

      {/* Certifications (read-only per spec) */}
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

// ── Page ────────────────────────────────────────────────────────────────────

function CVTailoredContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');
  const isEditMode = searchParams.get('mode') === 'edit';

  const [data, setData] = useState<CVTailoredStatusResponse | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  // Edit state
  const [editSections, setEditSections] = useState<CVSections | null>(null);
  const [originalSections, setOriginalSections] = useState<CVSections | null>(null);
  const [editRawText, setEditRawText] = useState('');
  const [originalRawText, setOriginalRawText] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const isDirty = isEditMode && (
    editSections !== null
      ? JSON.stringify(editSections) !== JSON.stringify(originalSections)
      : editRawText !== originalRawText
  );

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

      // Prefer the hub's authoritative artifact_id; fall back to ?id= query param
      const resolvedArtifactId = hub?.artifacts.cv_tailored?.artifact_id ?? queryId;
      const hubArtifactStatus = hub?.artifacts.cv_tailored?.status;

      if (!resolvedArtifactId || (hubArtifactStatus && hubArtifactStatus === 'failed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      const [cvResult] = await Promise.allSettled([
        api.getCVTailored(resolvedArtifactId),
      ]);

      const cvData = cvResult.status === 'fulfilled' ? cvResult.value : null;

      // Redirect only when there's clearly no usable content
      const hasContent = !!(cvData?.result?.cv_sections || cvData?.result?.tailored_cv);
      const isTerminalFailure = cvData?.status === 'failed' || cvData?.status === 'cancelled';
      if (!cvData || (isTerminalFailure && !hasContent) || (!hasContent && cvData.status === 'processing')) {
        router.replace(`/applications/${jobId}`);
        return;
      }
      setArtifactId(resolvedArtifactId);
      setData(cvData);

      const sections = cvData.result?.cv_sections ?? null;
      if (sections) {
        setEditSections(JSON.parse(JSON.stringify(sections)) as CVSections);
        setOriginalSections(JSON.parse(JSON.stringify(sections)) as CVSections);
      } else {
        const raw = cvData.result?.tailored_cv ?? '';
        setEditRawText(raw);
        setOriginalRawText(raw);
      }

      setLoading(false);
    };
    void init();
  }, [jobId, queryId, router]);

  const exitEditMode = useCallback(() => {
    const base = `/applications/${jobId}/cv-tailored${queryId ? `?id=${queryId}` : ''}`;
    router.replace(base);
  }, [jobId, queryId, router]);

  const handleSave = async () => {
    if (!artifactId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const body = editSections
        ? { cv_sections: editSections }
        : { tailored_cv: editRawText };
      const updated = await api.patchCVTailored(artifactId, body);
      setData(updated);
      const sections = updated.result?.cv_sections ?? null;
      if (sections) {
        setEditSections(JSON.parse(JSON.stringify(sections)) as CVSections);
        setOriginalSections(JSON.parse(JSON.stringify(sections)) as CVSections);
      } else {
        const raw = updated.result?.tailored_cv ?? editRawText;
        setEditRawText(raw);
        setOriginalRawText(raw);
      }
      exitEditMode();
    } catch {
      setSaveError('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (originalSections) {
      setEditSections(JSON.parse(JSON.stringify(originalSections)) as CVSections);
    } else {
      setEditRawText(originalRawText);
    }
    setSaveError(null);
    exitEditMode();
  };

  const result = data?.result;
  const cvSections = result?.cv_sections;
  const atsScore = result?.ats_score;
  const atsGrade = result?.ats_grade;
  const keywordsMatched = result?.keywords_matched ?? result?.keyword_matches?.matched ?? [];
  const keywordsMissing = result?.keywords_missing ?? result?.keyword_matches?.missing ?? [];

  const atsColorClass = atsGrade === 'green' ? 'bg-state-active' : atsGrade === 'yellow' ? 'bg-state-warning' : 'bg-state-error';

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
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-text-primary">Tailored CV</h1>
            {isDirty && (
              <span className="rounded-full bg-state-warning/15 px-2.5 py-0.5 text-xs font-medium text-state-warning">
                Unsaved changes
              </span>
            )}
          </div>
          {job && <p className="text-sm text-text-muted">{job.title} · {job.company_name}</p>}
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {isEditMode ? (
            <>
              <button
                onClick={() => void handleSave()}
                disabled={saving}
                className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-60 flex items-center gap-2"
              >
                {saving && <Spinner size="sm" aria-label="" />}
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={handleCancel}
                disabled={saving}
                className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle disabled:opacity-60"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              {artifactId && (
                <button
                  onClick={() => {
                    const base = `/applications/${jobId}/cv-tailored${queryId ? `?id=${queryId}` : ''}`;
                    router.replace(`${base}${queryId ? '&' : '?'}mode=edit`);
                  }}
                  className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
                  data-testid="cv-tailored-edit-button"
                >
                  Edit
                </button>
              )}
              {artifactId && (
                <ExportDropdown jobId={jobId} moduleType="cv_tailored" artifactId={artifactId} companyName={job?.company_name ?? ''} jobTitle={job?.title ?? ''} />
              )}
            </>
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {saveError && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {saveError}
        </div>
      )}

      {/* ATS score — always read-only, even in edit mode */}
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
                <span className="text-xs font-semibold text-state-active">Matched: </span>
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

      {/* CV content */}
      {cvSections ? (
        <div className="rounded-md border border-border-default bg-card p-8 flex flex-col gap-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-bold text-text-primary">Tailored CV</h2>
            {!isEditMode && (
              <button
                onClick={() => void handleCopy()}
                className="text-xs font-medium text-text-muted hover:text-text-primary transition-colors"
              >
                {copied ? 'Copied ✓' : 'Copy to clipboard'}
              </button>
            )}
          </div>
          {isEditMode && editSections ? (
            <CVDocumentEdit cv={editSections} onChange={setEditSections} />
          ) : (
            <CVDocument cv={cvSections} />
          )}
        </div>
      ) : result?.tailored_cv ? (
        <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-text-primary">Tailored CV</h2>
            {!isEditMode && (
              <button onClick={() => void handleCopy()} className="text-xs font-medium text-text-muted hover:text-text-primary transition-colors">
                {copied ? 'Copied ✓' : 'Copy to clipboard'}
              </button>
            )}
          </div>
          {isEditMode ? (
            <RichTextEditor
              content={editRawText}
              onChange={setEditRawText}
              readOnly={saving}
              placeholder="Edit your tailored CV…"
            />
          ) : (
            <pre className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap font-sans">{result.tailored_cv}</pre>
          )}
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
