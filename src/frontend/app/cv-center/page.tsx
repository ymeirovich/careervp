'use client';

import React, { useState } from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../components/ui/Spinner';
import { useCV } from '../../hooks/useCV';
import type { UserCV } from '../../lib/types';

type ViewMode = 'view' | 'edit' | 'create';

function CVForm({
  initial,
  onSave,
  onCancel,
  isSaving,
}: {
  initial: Partial<UserCV>;
  onSave: (data: Partial<UserCV>) => Promise<void>;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const [form, setForm] = useState<Partial<UserCV>>({
    full_name: initial.full_name ?? '',
    language: initial.language ?? 'en',
    contact_info: initial.contact_info ?? { name: '', email: '', phone: '', location: '', linkedin: '' },
    professional_summary: initial.professional_summary ?? '',
    skills: initial.skills ?? [],
    experience: initial.experience ?? [],
    education: initial.education ?? [],
    certifications: initial.certifications ?? [],
  });

  const set = (patch: Partial<UserCV>) => setForm((f) => ({ ...f, ...patch }));

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); void onSave(form); }}
      className="flex flex-col gap-6"
    >
      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Basic Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Full Name</label>
            <input
              type="text"
              value={form.full_name ?? ''}
              onChange={(e) => set({ full_name: e.target.value })}
              className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Language</label>
            <select
              value={form.language ?? 'en'}
              onChange={(e) => set({ language: e.target.value as 'en' | 'he' })}
              className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary"
            >
              <option value="en">English</option>
              <option value="he">Hebrew</option>
            </select>
          </div>
        </div>
      </div>

      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Contact Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(['email', 'phone', 'location', 'linkedin'] as const).map((field) => (
            <div key={field} className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wide capitalize">{field}</label>
              <input
                type="text"
                value={(form.contact_info?.[field] as string) ?? ''}
                onChange={(e) => set({ contact_info: { ...form.contact_info, [field]: e.target.value } })}
                className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Professional Summary</h2>
        <textarea
          rows={5}
          value={form.professional_summary ?? ''}
          onChange={(e) => set({ professional_summary: e.target.value })}
          placeholder="Write a compelling professional summary…"
          className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary resize-none"
        />
      </div>

      <div className="flex gap-3 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className="rounded-md border border-border-default px-4 py-2 text-sm text-text-primary hover:bg-bg-subtle disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSaving}
          className="rounded-md bg-brand-primary px-4 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
        >
          {isSaving ? 'Saving…' : 'Save CV'}
        </button>
      </div>
    </form>
  );
}

function CVPreview({ cv }: { cv: UserCV }) {
  const contact = cv.contact_info;
  return (
    <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
      <div className="flex flex-col gap-1 border-b border-border-default pb-4">
        <h2 className="text-lg font-bold text-text-primary">{cv.full_name}</h2>
        <div className="flex flex-wrap gap-3 text-sm text-text-muted">
          {contact.email && <span>{contact.email}</span>}
          {contact.phone && <span>{contact.phone}</span>}
          {contact.location && <span>{contact.location}</span>}
          {contact.linkedin && <span>{contact.linkedin}</span>}
        </div>
      </div>
      {cv.professional_summary && (
        <div>
          <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">Summary</p>
          <p className="text-sm text-text-primary leading-relaxed">{cv.professional_summary}</p>
        </div>
      )}
      {cv.experience.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Experience</p>
          <div className="flex flex-col gap-3">
            {cv.experience.map((exp, i) => (
              <div key={i} className="border-l-2 border-brand-primary pl-3">
                <p className="text-sm font-semibold text-text-primary">{exp.role} at {exp.company}</p>
                <p className="text-xs text-text-muted">{exp.dates}{exp.current ? ' · Present' : ''}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {cv.skills.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {cv.skills.map((s, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-bg-subtle text-text-muted">{s}</span>
            ))}
          </div>
        </div>
      )}
      {cv.updated_at && (
        <p className="text-xs text-text-muted">Last updated: {new Date(cv.updated_at).toLocaleDateString()}</p>
      )}
    </div>
  );
}

function CVCenterContent() {
  const { cv, isLoading, isSaving, saveCV, error } = useCV();
  const [mode, setMode] = useState<ViewMode>('view');

  const handleSave = async (data: Partial<UserCV>) => {
    await saveCV(data);
    setMode('view');
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading CV…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-bold text-text-primary">CV Center</h1>
        {cv && mode === 'view' && (
          <button
            onClick={() => setMode('edit')}
            className="rounded-md bg-brand-primary px-3 py-2 text-sm font-bold text-white hover:opacity-90"
          >
            Edit CV
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {error}
        </div>
      )}

      {!cv && mode === 'view' ? (
        <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center flex flex-col items-center gap-4">
          <p className="text-sm text-text-muted">Upload your base CV to get started</p>
          <button
            onClick={() => setMode('create')}
            className="rounded-md bg-brand-primary px-4 py-2 text-sm font-bold text-white hover:opacity-90"
          >
            Create CV
          </button>
        </div>
      ) : mode === 'edit' || mode === 'create' ? (
        <CVForm
          initial={cv ?? {}}
          onSave={handleSave}
          onCancel={() => setMode('view')}
          isSaving={isSaving}
        />
      ) : cv ? (
        <CVPreview cv={cv} />
      ) : null}
    </div>
  );
}

export default function CVCenterPage() {
  return (
    <ErrorBoundary cloudwatchKey="cv-center-page">
      <CVCenterContent />
    </ErrorBoundary>
  );
}
