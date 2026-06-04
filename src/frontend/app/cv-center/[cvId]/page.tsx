'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '../../../api/methods';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../components/ui/Spinner';
import type { UserCV, WorkExperience, Education, Certification } from '../../../lib/types';

const CARD = 'rounded-xl border border-border-default bg-card p-6 flex flex-col gap-4';
const SECTION_TITLE = 'text-sm font-semibold uppercase tracking-wide text-text-muted';
const BODY = 'text-sm text-text-primary leading-relaxed';
const MUTED = 'text-sm text-text-muted';

function ContactRow({ label, value }: { label: string; value: string | undefined }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-muted w-20 shrink-0 pt-0.5">{label}</span>
      <span className={BODY}>{value}</span>
    </div>
  );
}

function ExperienceCard({ job }: { job: WorkExperience }) {
  return (
    <div className="flex flex-col gap-2 pb-4 border-b border-border-default last:border-0 last:pb-0">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">{job.role}</p>
          <p className={MUTED}>{job.company}</p>
        </div>
        <span className="text-xs text-text-muted whitespace-nowrap shrink-0">{job.dates}</span>
      </div>
      {job.achievements.length > 0 && (
        <ul className="flex flex-col gap-1 pl-4">
          {job.achievements.map((a, i) => (
            <li key={i} className="text-sm text-text-primary list-disc">{a}</li>
          ))}
        </ul>
      )}
      {job.technologies.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {job.technologies.map((t) => (
            <span key={t} className="px-2 py-0.5 rounded-full bg-surface-subtle text-xs text-text-muted">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function EducationCard({ edu }: { edu: Education }) {
  return (
    <div className="flex flex-col gap-1 pb-4 border-b border-border-default last:border-0 last:pb-0">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">{edu.degree}{edu.field_of_study ? ` · ${edu.field_of_study}` : ''}</p>
          <p className={MUTED}>{edu.institution}</p>
        </div>
        <span className="text-xs text-text-muted whitespace-nowrap shrink-0">{edu.graduation_date}</span>
      </div>
      {edu.honors.length > 0 && (
        <p className="text-xs text-text-muted">{edu.honors.join(', ')}</p>
      )}
    </div>
  );
}

function CertificationRow({ cert }: { cert: Certification }) {
  return (
    <div className="flex flex-col gap-0.5 pb-3 border-b border-border-default last:border-0 last:pb-0">
      <p className="text-sm font-medium text-text-primary">{cert.name}</p>
      {(cert.issuer ?? cert.date) && (
        <p className={MUTED}>{[cert.issuer, cert.date].filter(Boolean).join(' · ')}</p>
      )}
    </div>
  );
}

function CVDetailContent({ cvId }: { cvId: string }) {
  const router = useRouter();
  const [cv, setCv] = useState<UserCV | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    api
      .getCVById(cvId)
      .then((data) => {
        if (!cancelled) {
          if (data) {
            setCv(data);
          } else {
            setError('CV not found.');
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load CV. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [cvId]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading CV…" />
      </div>
    );
  }

  if (error || !cv) {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <p className="text-text-muted">{error ?? 'CV not found.'}</p>
        <button
          type="button"
          onClick={() => router.push('/cv-center')}
          className="text-sm font-medium text-primary-action underline hover:opacity-75"
        >
          Back to CV Center
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-text-primary">{cv.full_name}</h1>
          {cv.contact_info.location && (
            <p className={MUTED}>{cv.contact_info.location}</p>
          )}
          {cv.language !== 'en' && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-surface-subtle text-text-muted w-fit">{cv.language.toUpperCase()}</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => router.push('/cv-center')}
          className="shrink-0 text-sm font-medium text-text-muted hover:text-text-primary transition-colors"
        >
          ← Back
        </button>
      </div>

      {/* Contact */}
      <div className={CARD}>
        <h2 className={SECTION_TITLE}>Contact</h2>
        <div className="flex flex-col gap-2">
          <ContactRow label="Email" value={cv.contact_info.email} />
          <ContactRow label="Phone" value={cv.contact_info.phone} />
          <ContactRow label="Location" value={cv.contact_info.location} />
          <ContactRow label="LinkedIn" value={cv.contact_info.linkedin} />
        </div>
      </div>

      {/* Professional Summary */}
      {cv.professional_summary && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Professional Summary</h2>
          <p className={BODY}>{cv.professional_summary}</p>
        </div>
      )}

      {/* Top Achievements */}
      {cv.top_achievements.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Top Achievements</h2>
          <ul className="flex flex-col gap-2 pl-4">
            {cv.top_achievements.map((a, i) => (
              <li key={i} className={`${BODY} list-disc`}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Experience */}
      {cv.experience.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Experience</h2>
          <div className="flex flex-col gap-4">
            {cv.experience.map((job, i) => (
              <ExperienceCard key={i} job={job} />
            ))}
          </div>
        </div>
      )}

      {/* Education */}
      {cv.education.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Education</h2>
          <div className="flex flex-col gap-4">
            {cv.education.map((edu, i) => (
              <EducationCard key={i} edu={edu} />
            ))}
          </div>
        </div>
      )}

      {/* Skills */}
      {cv.skills.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Skills</h2>
          <div className="flex flex-wrap gap-2">
            {cv.skills.map((skill) => (
              <span key={skill} className="px-3 py-1 rounded-full border border-border-default bg-surface-subtle text-sm text-text-primary">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Certifications */}
      {cv.certifications.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Certifications</h2>
          <div className="flex flex-col gap-3">
            {cv.certifications.map((cert, i) => (
              <CertificationRow key={i} cert={cert} />
            ))}
          </div>
        </div>
      )}

      {/* Languages */}
      {cv.languages.length > 0 && (
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Languages</h2>
          <div className="flex flex-wrap gap-2">
            {cv.languages.map((lang) => (
              <span key={lang} className="px-3 py-1 rounded-full border border-border-default bg-surface-subtle text-sm text-text-primary">
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CVDetailPage() {
  const params = useParams();
  const cvId = typeof params.cvId === 'string' ? params.cvId : '';

  if (!cvId) return null;

  return (
    <ErrorBoundary cloudwatchKey="cv-detail-page">
      <CVDetailContent cvId={cvId} />
    </ErrorBoundary>
  );
}
