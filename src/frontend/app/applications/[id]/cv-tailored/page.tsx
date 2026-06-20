'use client';

import React, { useState, useEffect, use, Suspense, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ArtifactAutosaveField } from '../../../../components/ArtifactAutosaveField';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { RichTextEditor } from '../../../../components/RichTextEditor/RichTextEditor';
import { Spinner } from '../../../../components/ui/Spinner';
import type { ArtifactAutosaveResult, ArtifactBaseVersion } from '../../../../hooks/useArtifactAutosave';
import type { CVSections, CVTailoredStatusResponse, JobDetail } from '../../../../lib/types';

function formatDateRange(start: string, end?: string | null, isCurrent?: boolean): string {
  const endLabel = isCurrent || !end || end === 'Present' ? 'Present' : end;
  return start ? `${start} – ${endLabel}` : endLabel ?? '';
}

function cloneSections(sections: CVSections): CVSections {
  return JSON.parse(JSON.stringify(sections)) as CVSections;
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
      for (const bullet of exp.bullets) lines.push(`  • ${bullet.text}`);
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

const inputClassName =
  'w-full rounded border border-border-default bg-surface-subtle px-2 py-1 text-sm text-text-primary leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary-action/50';

interface PersistedSectionsResult {
  response: CVTailoredStatusResponse;
  sections: CVSections;
  updatedAt: string | null;
  baseVersion: ArtifactBaseVersion;
}

interface CVFieldPersistence {
  save: (value: string, context: { baseVersion: ArtifactBaseVersion }) => Promise<ArtifactAutosaveResult>;
  onSaved: (result: ArtifactAutosaveResult) => void;
  fetchLatest: () => Promise<ArtifactAutosaveResult>;
  onReloaded: (result: ArtifactAutosaveResult) => void;
}

interface CVFieldProps {
  artifactId: string | null;
  baseVersion: ArtifactBaseVersion;
  baseline: string;
  fieldKey: string;
  onRequestEdit: () => void;
  onValueChange: (value: string) => void;
  persistence: CVFieldPersistence;
  serverUpdatedAt: string | null;
  value: string;
}

function CVRichTextField({
  artifactId,
  baseVersion,
  baseline,
  fieldKey,
  onRequestEdit,
  onValueChange,
  persistence,
  serverUpdatedAt,
  value,
  placeholder,
}: CVFieldProps & { placeholder: string }) {
  return (
    <ArtifactAutosaveField
      artifactType="cv_tailored"
      artifactId={artifactId}
      fieldKey={fieldKey}
      value={value}
      baseline={baseline}
      onValueChange={onValueChange}
      serverUpdatedAt={serverUpdatedAt}
      baseVersion={baseVersion}
      save={persistence.save}
      onSaved={persistence.onSaved}
      fetchLatest={persistence.fetchLatest}
      onReloaded={persistence.onReloaded}
      onRequestEdit={onRequestEdit}
      renderField={({ isSaving, onBlur }) => (
        <RichTextEditor
          content={value}
          onChange={onValueChange}
          onBlur={onBlur}
          readOnly={isSaving}
          placeholder={placeholder}
          ariaLabelledBy={fieldKey}
        />
      )}
    />
  );
}

function CVPlainTextField({
  artifactId,
  baseVersion,
  baseline,
  fieldKey,
  multiline = false,
  onRequestEdit,
  onValueChange,
  persistence,
  placeholder,
  rows = 2,
  serverUpdatedAt,
  value,
}: CVFieldProps & { multiline?: boolean; placeholder?: string; rows?: number }) {
  return (
    <ArtifactAutosaveField
      artifactType="cv_tailored"
      artifactId={artifactId}
      fieldKey={fieldKey}
      value={value}
      baseline={baseline}
      onValueChange={onValueChange}
      serverUpdatedAt={serverUpdatedAt}
      baseVersion={baseVersion}
      save={persistence.save}
      onSaved={persistence.onSaved}
      fetchLatest={persistence.fetchLatest}
      onReloaded={persistence.onReloaded}
      onRequestEdit={onRequestEdit}
      renderField={({ isSaving, onBlur }) =>
        multiline ? (
          <textarea
            value={value}
            onChange={(event) => onValueChange(event.target.value)}
            onBlur={onBlur}
            rows={rows}
            disabled={isSaving}
            placeholder={placeholder}
            className={`${inputClassName} resize-none disabled:opacity-60`}
          />
        ) : (
          <input
            type="text"
            value={value}
            onChange={(event) => onValueChange(event.target.value)}
            onBlur={onBlur}
            disabled={isSaving}
            placeholder={placeholder}
            className={`${inputClassName} disabled:opacity-60`}
          />
        )
      }
    />
  );
}

interface CVDocumentProps {
  artifactId: string | null;
  baseVersion: ArtifactBaseVersion;
  baselineSections: CVSections;
  onRequestEdit: () => void;
  onSectionsChange: (nextSections: CVSections) => void;
  persistenceFor: (_fieldKey: string, getValue: (sections: CVSections) => string, applyValue: (sections: CVSections, value: string) => void) => CVFieldPersistence;
  sections: CVSections;
  serverUpdatedAt: string | null;
}

function CVDocumentEdit({
  artifactId,
  baseVersion,
  baselineSections,
  onRequestEdit,
  onSectionsChange,
  persistenceFor,
  sections,
  serverUpdatedAt,
}: CVDocumentProps) {
  const updateSections = (applyValue: (nextSections: CVSections) => void) => {
    const nextSections = cloneSections(sections);
    applyValue(nextSections);
    onSectionsChange(nextSections);
  };

  return (
    <div className="flex flex-col gap-6 font-sans">
      <div className="border-b border-border-default pb-4 flex flex-col gap-2">
        <CVPlainTextField
          artifactId={artifactId}
          baseVersion={baseVersion}
          baseline={baselineSections.contact.name}
          fieldKey="contact.name"
          onRequestEdit={onRequestEdit}
          onValueChange={(value) => {
            updateSections((nextSections) => {
              nextSections.contact.name = value;
            });
          }}
          persistence={persistenceFor(
            'contact.name',
            (cv) => cv.contact.name,
            (cv, value) => {
              cv.contact.name = value;
            },
          )}
          placeholder="Full Name"
          serverUpdatedAt={serverUpdatedAt}
          value={sections.contact.name}
        />
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {(['email', 'phone', 'linkedin', 'location'] as const).map((field) => (
            <CVPlainTextField
              key={field}
              artifactId={artifactId}
              baseVersion={baseVersion}
              baseline={baselineSections.contact[field] ?? ''}
              fieldKey={`contact.${field}`}
              onRequestEdit={onRequestEdit}
              onValueChange={(value) => {
                updateSections((nextSections) => {
                  nextSections.contact[field] = value;
                });
              }}
              persistence={persistenceFor(
                `contact.${field}`,
                (cv) => cv.contact[field] ?? '',
                (cv, value) => {
                  cv.contact[field] = value;
                },
              )}
              placeholder={field.charAt(0).toUpperCase() + field.slice(1)}
              serverUpdatedAt={serverUpdatedAt}
              value={sections.contact[field] ?? ''}
            />
          ))}
        </div>
      </div>

      <section>
        <h2 id="summary" className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">
          Professional Summary
        </h2>
        <CVRichTextField
          artifactId={artifactId}
          baseVersion={baseVersion}
          baseline={baselineSections.summary}
          fieldKey="summary"
          onRequestEdit={onRequestEdit}
          onValueChange={(value) => {
            updateSections((nextSections) => {
              nextSections.summary = value;
            });
          }}
          persistence={persistenceFor(
            'summary',
            (cv) => cv.summary,
            (cv, value) => {
              cv.summary = value;
            },
          )}
          placeholder="Write your tailored summary…"
          serverUpdatedAt={serverUpdatedAt}
          value={sections.summary}
        />
      </section>

      <section>
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">
          Core Competencies
        </h2>
        <CVPlainTextField
          artifactId={artifactId}
          baseVersion={baseVersion}
          baseline={baselineSections.skills.technical.join(', ')}
          fieldKey="skills.technical"
          multiline
          onRequestEdit={onRequestEdit}
          onValueChange={(value) => {
            updateSections((nextSections) => {
              nextSections.skills.technical = value.split(',').map((entry) => entry.trim()).filter(Boolean);
            });
          }}
          persistence={persistenceFor(
            'skills.technical',
            (cv) => cv.skills.technical.join(', '),
            (cv, value) => {
              cv.skills.technical = value.split(',').map((entry) => entry.trim()).filter(Boolean);
            },
          )}
          placeholder="Comma-separated skills"
          rows={2}
          serverUpdatedAt={serverUpdatedAt}
          value={sections.skills.technical.join(', ')}
        />
        <p className="mt-1 text-xs text-text-muted">Separate skills with commas</p>
      </section>

      {sections.experience.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-3">
            Professional Experience
          </h2>
          <div className="flex flex-col gap-4">
            {sections.experience.map((experience, experienceIndex) => (
              <div key={`${experience.company}-${experience.title}-${experienceIndex}`}>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-sm font-semibold text-text-primary">{experience.title} | {experience.company}</span>
                  <span className="text-xs text-text-muted shrink-0">{formatDateRange(experience.start_date, experience.end_date, experience.is_current)}</span>
                </div>
                <div className="flex flex-col gap-3">
                  {experience.bullets.map((bullet, bulletIndex) => (
                    <div key={`${experience.company}-bullet-${bulletIndex}`} className="flex gap-2">
                      <span className="mt-2 text-sm text-text-secondary">•</span>
                      <div className="flex-1">
                        <CVRichTextField
                          artifactId={artifactId}
                          baseVersion={baseVersion}
                          baseline={baselineSections.experience[experienceIndex]?.bullets[bulletIndex]?.text ?? ''}
                          fieldKey={`experience.${experienceIndex}.bullet.${bulletIndex}`}
                          onRequestEdit={onRequestEdit}
                          onValueChange={(value) => {
                            updateSections((nextSections) => {
                              const currentBullet = nextSections.experience[experienceIndex]?.bullets[bulletIndex];
                              if (currentBullet) {
                                currentBullet.text = value;
                              }
                            });
                          }}
                          persistence={persistenceFor(
                            `experience.${experienceIndex}.bullet.${bulletIndex}`,
                            (cv) => cv.experience[experienceIndex]?.bullets[bulletIndex]?.text ?? '',
                            (cv, value) => {
                              const currentBullet = cv.experience[experienceIndex]?.bullets[bulletIndex];
                              if (currentBullet) {
                                currentBullet.text = value;
                              }
                            },
                          )}
                          placeholder="Edit this bullet…"
                          serverUpdatedAt={serverUpdatedAt}
                          value={bullet.text}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {sections.education.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">
            Education
          </h2>
          <div className="flex flex-col gap-4">
            {sections.education.map((education, educationIndex) => (
              <div key={`${education.institution}-${education.degree}-${educationIndex}`} className="grid gap-2 md:grid-cols-2">
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.education[educationIndex]?.degree ?? ''}
                  fieldKey={`education.${educationIndex}.degree`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.education[educationIndex];
                      if (current) {
                        current.degree = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `education.${educationIndex}.degree`,
                    (cv) => cv.education[educationIndex]?.degree ?? '',
                    (cv, value) => {
                      const current = cv.education[educationIndex];
                      if (current) {
                        current.degree = value;
                      }
                    },
                  )}
                  placeholder="Degree"
                  serverUpdatedAt={serverUpdatedAt}
                  value={education.degree}
                />
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.education[educationIndex]?.field ?? ''}
                  fieldKey={`education.${educationIndex}.field`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.education[educationIndex];
                      if (current) {
                        current.field = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `education.${educationIndex}.field`,
                    (cv) => cv.education[educationIndex]?.field ?? '',
                    (cv, value) => {
                      const current = cv.education[educationIndex];
                      if (current) {
                        current.field = value;
                      }
                    },
                  )}
                  placeholder="Field of study"
                  serverUpdatedAt={serverUpdatedAt}
                  value={education.field}
                />
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.education[educationIndex]?.institution ?? ''}
                  fieldKey={`education.${educationIndex}.institution`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.education[educationIndex];
                      if (current) {
                        current.institution = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `education.${educationIndex}.institution`,
                    (cv) => cv.education[educationIndex]?.institution ?? '',
                    (cv, value) => {
                      const current = cv.education[educationIndex];
                      if (current) {
                        current.institution = value;
                      }
                    },
                  )}
                  placeholder="Institution"
                  serverUpdatedAt={serverUpdatedAt}
                  value={education.institution}
                />
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.education[educationIndex]?.graduation_date ?? ''}
                  fieldKey={`education.${educationIndex}.graduation_date`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.education[educationIndex];
                      if (current) {
                        current.graduation_date = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `education.${educationIndex}.graduation_date`,
                    (cv) => cv.education[educationIndex]?.graduation_date ?? '',
                    (cv, value) => {
                      const current = cv.education[educationIndex];
                      if (current) {
                        current.graduation_date = value;
                      }
                    },
                  )}
                  placeholder="Graduation date"
                  serverUpdatedAt={serverUpdatedAt}
                  value={education.graduation_date}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {sections.certifications.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">
            Certifications
          </h2>
          <div className="flex flex-col gap-4">
            {sections.certifications.map((certification, certificationIndex) => (
              <div key={`${certification.name}-${certificationIndex}`} className="grid gap-2 md:grid-cols-3">
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.certifications[certificationIndex]?.name ?? ''}
                  fieldKey={`certifications.${certificationIndex}.name`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.certifications[certificationIndex];
                      if (current) {
                        current.name = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `certifications.${certificationIndex}.name`,
                    (cv) => cv.certifications[certificationIndex]?.name ?? '',
                    (cv, value) => {
                      const current = cv.certifications[certificationIndex];
                      if (current) {
                        current.name = value;
                      }
                    },
                  )}
                  placeholder="Certification"
                  serverUpdatedAt={serverUpdatedAt}
                  value={certification.name}
                />
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.certifications[certificationIndex]?.issuer ?? ''}
                  fieldKey={`certifications.${certificationIndex}.issuer`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.certifications[certificationIndex];
                      if (current) {
                        current.issuer = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `certifications.${certificationIndex}.issuer`,
                    (cv) => cv.certifications[certificationIndex]?.issuer ?? '',
                    (cv, value) => {
                      const current = cv.certifications[certificationIndex];
                      if (current) {
                        current.issuer = value;
                      }
                    },
                  )}
                  placeholder="Issuer"
                  serverUpdatedAt={serverUpdatedAt}
                  value={certification.issuer}
                />
                <CVPlainTextField
                  artifactId={artifactId}
                  baseVersion={baseVersion}
                  baseline={baselineSections.certifications[certificationIndex]?.date ?? ''}
                  fieldKey={`certifications.${certificationIndex}.date`}
                  onRequestEdit={onRequestEdit}
                  onValueChange={(value) => {
                    updateSections((nextSections) => {
                      const current = nextSections.certifications[certificationIndex];
                      if (current) {
                        current.date = value;
                      }
                    });
                  }}
                  persistence={persistenceFor(
                    `certifications.${certificationIndex}.date`,
                    (cv) => cv.certifications[certificationIndex]?.date ?? '',
                    (cv, value) => {
                      const current = cv.certifications[certificationIndex];
                      if (current) {
                        current.date = value;
                      }
                    },
                  )}
                  placeholder="Date"
                  serverUpdatedAt={serverUpdatedAt}
                  value={certification.date}
                />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function CVDocument({ cv }: { cv: CVSections }) {
  const contactParts = [cv.contact.email, cv.contact.phone, cv.contact.linkedin, cv.contact.location].filter(Boolean);

  return (
    <div className="flex flex-col gap-6 font-sans">
      <div className="text-center border-b border-border-default pb-4">
        <h1 className="text-xl font-bold text-text-primary tracking-wide uppercase">{cv.contact.name}</h1>
        {contactParts.length > 0 && (
          <p className="text-sm text-text-muted mt-1">{contactParts.join(' | ')}</p>
        )}
      </div>

      <section>
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Professional Summary</h2>
        <RichTextEditor content={cv.summary} onChange={() => undefined} readOnly />
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
            {cv.experience.map((experience, experienceIndex) => (
              <div key={`${experience.company}-${experience.title}-${experienceIndex}`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold text-text-primary">{experience.title} | {experience.company}</span>
                  <span className="text-xs text-text-muted shrink-0">{formatDateRange(experience.start_date, experience.end_date, experience.is_current)}</span>
                </div>
                <div className="mt-2 flex flex-col gap-3">
                  {experience.bullets.map((bullet, bulletIndex) => (
                    <div key={`${experience.company}-readonly-bullet-${bulletIndex}`} className="flex gap-2">
                      <span className="mt-2 text-sm text-text-secondary">•</span>
                      <div className="flex-1">
                        <RichTextEditor content={bullet.text} onChange={() => undefined} readOnly />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {cv.education.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Education</h2>
          <div className="flex flex-col gap-2">
            {cv.education.map((education, educationIndex) => (
              <div key={`${education.institution}-${education.degree}-${educationIndex}`} className="flex items-start justify-between gap-2">
                <span className="text-sm text-text-secondary">
                  <span className="font-medium">{education.degree}</span> in {education.field} | {education.institution}
                </span>
                {education.graduation_date && <span className="text-xs text-text-muted shrink-0">{education.graduation_date}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      {cv.certifications.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-text-primary pb-1 mb-2">Certifications</h2>
          <ul className="flex flex-col gap-1">
            {cv.certifications.map((certification, certificationIndex) => (
              <li key={`${certification.name}-${certificationIndex}`} className="flex gap-2 text-sm text-text-secondary">
                <span className="shrink-0 mt-0.5">•</span>
                <span>{certification.name}{certification.issuer && <span className="text-text-muted"> | {certification.issuer}</span>}{certification.date && <span className="text-text-muted"> | {certification.date}</span>}</span>
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
  const isEditMode = searchParams.get('mode') === 'edit';

  const [data, setData] = useState<CVTailoredStatusResponse | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [editSections, setEditSections] = useState<CVSections | null>(null);
  const [originalSections, setOriginalSections] = useState<CVSections | null>(null);
  const [serverUpdatedAt, setServerUpdatedAt] = useState<string | null>(null);
  const [baseVersion, setBaseVersion] = useState<ArtifactBaseVersion>(null);
  const [pageSaving, setPageSaving] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const editSectionsRef = useRef<CVSections | null>(null);
  editSectionsRef.current = editSections;

  const isDirty = isEditMode && editSections !== null && originalSections !== null
    && JSON.stringify(editSections) !== JSON.stringify(originalSections);

  const enterEditMode = useCallback(() => {
    const base = `/applications/${jobId}/cv-tailored${queryId ? `?id=${queryId}` : ''}`;
    router.replace(`${base}${queryId ? '&' : '?'}mode=edit`);
  }, [jobId, queryId, router]);

  const exitEditMode = useCallback(() => {
    const base = `/applications/${jobId}/cv-tailored${queryId ? `?id=${queryId}` : ''}`;
    router.replace(base);
  }, [jobId, queryId, router]);

  const applySectionsFromResponse = useCallback((response: CVTailoredStatusResponse, fallbackSections?: CVSections) => {
    const responseSections = response.result?.cv_sections ?? fallbackSections;
    if (!responseSections) return;

    const nextSections = cloneSections(responseSections);
    setData(response);
    setEditSections(nextSections);
    setOriginalSections(cloneSections(responseSections));
    setServerUpdatedAt(response.updated_at ?? null);
    setBaseVersion(response.version ?? response.updated_at ?? null);
  }, []);

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

      const resolvedArtifactId = hub?.artifacts.cv_tailored?.artifact_id ?? queryId;
      const hubArtifactStatus = hub?.artifacts.cv_tailored?.status;

      if (!resolvedArtifactId || (hubArtifactStatus && hubArtifactStatus === 'failed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      const cvData = await api.getCVTailored(resolvedArtifactId);
      const hasSections = Boolean(cvData.result?.cv_sections);
      const hasRawFallback = Boolean(cvData.result?.tailored_cv);
      const isTerminalFailure = cvData.status === 'failed' || cvData.status === 'cancelled';

      if ((!hasSections && !hasRawFallback) || (isTerminalFailure && !hasSections && !hasRawFallback)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      setArtifactId(resolvedArtifactId);
      setData(cvData);
      setServerUpdatedAt(cvData.updated_at ?? null);
      setBaseVersion(cvData.version ?? cvData.updated_at ?? null);

      if (cvData.result?.cv_sections) {
        const cloned = cloneSections(cvData.result.cv_sections);
        setEditSections(cloned);
        setOriginalSections(cloneSections(cvData.result.cv_sections));
      }

      setLoading(false);
    };

    void init();
  }, [jobId, queryId, router]);

  const buildUpdatedSections = useCallback((applyValue: (sections: CVSections) => void): CVSections | null => {
    const current = editSectionsRef.current ?? originalSections;
    if (!current) return null;

    const nextSections = cloneSections(current);
    applyValue(nextSections);
    return nextSections;
  }, [originalSections]);

  const persistSections = useCallback(async (nextSections: CVSections, versionToSend: ArtifactBaseVersion): Promise<PersistedSectionsResult> => {
    if (!artifactId) {
      return {
        response: data as CVTailoredStatusResponse,
        sections: nextSections,
        updatedAt: serverUpdatedAt,
        baseVersion: versionToSend,
      };
    }

    const response = await api.patchCVTailored(artifactId, {
      cv_sections: nextSections,
      base_version: versionToSend,
    });

    return {
      response,
      sections: response.result?.cv_sections ?? nextSections,
      updatedAt: response.updated_at ?? new Date().toISOString(),
      baseVersion: response.version ?? response.updated_at ?? versionToSend ?? null,
    };
  }, [artifactId, data, serverUpdatedAt]);

  const fetchLatestSections = useCallback(async (): Promise<PersistedSectionsResult> => {
    if (!artifactId) {
      const current = editSectionsRef.current ?? originalSections;
      if (!current) {
        throw new Error('Missing tailored CV sections');
      }
      return {
        response: data as CVTailoredStatusResponse,
        sections: current,
        updatedAt: serverUpdatedAt,
        baseVersion,
      };
    }

    const latest = await api.getCVTailored(artifactId);
    const sections = latest.result?.cv_sections ?? editSectionsRef.current ?? originalSections;
    if (!sections) {
      throw new Error('Missing tailored CV sections');
    }

    return {
      response: latest,
      sections,
      updatedAt: latest.updated_at ?? null,
      baseVersion: latest.version ?? latest.updated_at ?? null,
    };
  }, [artifactId, baseVersion, data, originalSections, serverUpdatedAt]);

  const persistenceFor = useCallback((
    _fieldKey: string,
    getValue: (sections: CVSections) => string,
    applyValue: (sections: CVSections, value: string) => void,
  ): CVFieldPersistence => ({
    save: async (value, context) => {
      const nextSections = buildUpdatedSections((sections) => applyValue(sections, value));
      if (!nextSections) {
        return { value, baseVersion: context.baseVersion, updatedAt: serverUpdatedAt };
      }

      const persisted = await persistSections(nextSections, context.baseVersion);
      return {
        value: getValue(persisted.sections),
        updatedAt: persisted.updatedAt,
        baseVersion: persisted.baseVersion,
        metadata: persisted,
      };
    },
    onSaved: (result) => {
      const persisted = result.metadata as PersistedSectionsResult | undefined;
      if (!persisted) return;
      applySectionsFromResponse(persisted.response, persisted.sections);
    },
    fetchLatest: async () => {
      const latest = await fetchLatestSections();
      return {
        value: getValue(latest.sections),
        updatedAt: latest.updatedAt,
        baseVersion: latest.baseVersion,
        metadata: latest,
      };
    },
    onReloaded: (result) => {
      const latest = result.metadata as PersistedSectionsResult | undefined;
      if (!latest) return;
      applySectionsFromResponse(latest.response, latest.sections);
    },
  }), [applySectionsFromResponse, buildUpdatedSections, fetchLatestSections, persistSections, serverUpdatedAt]);

  const handleSave = async () => {
    if (!editSections) return;
    setPageSaving(true);
    setPageError(null);

    try {
      const persisted = await persistSections(cloneSections(editSections), baseVersion);
      applySectionsFromResponse(persisted.response, persisted.sections);
      exitEditMode();
    } catch {
      setPageError('Failed to save. Please try again.');
    } finally {
      setPageSaving(false);
    }
  };

  const handleCancel = () => {
    if (originalSections) {
      setEditSections(cloneSections(originalSections));
    }
    setPageError(null);
    exitEditMode();
  };

  const handleCopy = async () => {
    if (!editSections) return;
    await navigator.clipboard.writeText(buildCopyText(editSections));
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

  const result = data?.result;
  const cvSections = editSections;
  const atsScore = result?.ats_score;
  const atsGrade = result?.ats_grade;
  const keywordsMatched = result?.keywords_matched ?? result?.keyword_matches?.matched ?? [];
  const keywordsMissing = result?.keywords_missing ?? result?.keyword_matches?.missing ?? [];
  const atsColorClass = atsGrade === 'green' ? 'bg-state-active' : atsGrade === 'yellow' ? 'bg-state-warning' : 'bg-state-error';

  return (
    <div className="flex flex-col gap-6 max-w-4xl" data-testid="cv-tailored-page">
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
                disabled={pageSaving}
                className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-60 flex items-center gap-2"
              >
                {pageSaving && <Spinner size="sm" aria-label="" />}
                {pageSaving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={handleCancel}
                disabled={pageSaving}
                className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle disabled:opacity-60"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              {artifactId && cvSections && (
                <button
                  onClick={enterEditMode}
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

      {pageError && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {pageError}
        </div>
      )}

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

      {cvSections && originalSections ? (
        <div className="rounded-md border border-border-default bg-card p-8 flex flex-col gap-4">
          <div className="flex items-center justify-between">
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
          {isEditMode ? (
            <CVDocumentEdit
              artifactId={artifactId}
              baseVersion={baseVersion}
              baselineSections={originalSections}
              onRequestEdit={enterEditMode}
              onSectionsChange={setEditSections}
              persistenceFor={persistenceFor}
              sections={cvSections}
              serverUpdatedAt={serverUpdatedAt}
            />
          ) : (
            <CVDocument cv={cvSections} />
          )}
        </div>
      ) : result?.tailored_cv ? (
        <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
          <h2 className="text-base font-bold text-text-primary">Tailored CV</h2>
          <RichTextEditor content={result.tailored_cv} onChange={() => undefined} readOnly />
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
