'use client';

import React, { useState, type KeyboardEvent } from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../components/ui/Spinner';
import { useCV } from '../../hooks/useCV';
import type { UserCV } from '../../lib/types';

type ViewMode = 'view' | 'edit' | 'create';

// ── TagInput ──────────────────────────────────────────────────────────────────

function TagInput({
  tags,
  onChange,
  placeholder,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState('');

  const addTag = () => {
    const trimmed = input.trim();
    if (!trimmed || tags.includes(trimmed)) return;
    onChange([...tags, trimmed]);
    setInput('');
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(); }
    if (e.key === 'Backspace' && !input && tags.length > 0) onChange(tags.slice(0, -1));
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-surface-subtle text-text-muted">
            {t}
            <button type="button" onClick={() => onChange(tags.filter((x) => x !== t))} className="hover:text-state-error leading-none">×</button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKey}
        onBlur={addTag}
        placeholder={placeholder ?? 'Type and press Enter'}
        className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action"
      />
    </div>
  );
}

// ── CVForm ────────────────────────────────────────────────────────────────────

const INPUT = 'rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action';
const CARD = 'rounded-md border border-border-default bg-card p-6 flex flex-col gap-4';
const LABEL = 'text-xs font-semibold text-text-muted uppercase tracking-wide';

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
    top_achievements: initial.top_achievements ?? ['', '', ''],
    languages: initial.languages ?? [],
  });

  const set = (patch: Partial<UserCV>) => setForm((f) => ({ ...f, ...patch }));

  const patchAchievement = (i: number, value: string) => {
    const top_achievements = [...(form.top_achievements ?? ['', '', ''])];
    while (top_achievements.length < 3) top_achievements.push('');
    top_achievements[i] = value;
    set({ top_achievements });
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); void onSave(form); }} className="flex flex-col gap-6">

      {/* Basic Info */}
      <div className={CARD}>
        <h2 className="text-base font-bold text-text-primary">Basic Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className={LABEL}>Full Name</label>
            <input type="text" value={form.full_name ?? ''} onChange={(e) => set({ full_name: e.target.value })} className={INPUT} required />
          </div>
          <div className="flex flex-col gap-1">
            <label className={LABEL}>Language</label>
            <select value={form.language ?? 'en'} onChange={(e) => set({ language: e.target.value as 'en' | 'he' })} className={INPUT}>
              <option value="en">English</option>
              <option value="he">Hebrew</option>
            </select>
          </div>
        </div>
      </div>

      {/* Contact Info */}
      <div className={CARD}>
        <h2 className="text-base font-bold text-text-primary">Contact Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(['email', 'phone', 'location', 'linkedin'] as const).map((field) => (
            <div key={field} className="flex flex-col gap-1">
              <label className={LABEL}>{field}</label>
              <input
                type="text"
                value={(form.contact_info?.[field] as string) ?? ''}
                onChange={(e) => set({ contact_info: { ...form.contact_info, [field]: e.target.value } as UserCV['contact_info'] })}
                className={INPUT}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Professional Summary */}
      <div className={CARD}>
        <h2 className="text-base font-bold text-text-primary">Professional Summary</h2>
        <textarea
          rows={5}
          value={form.professional_summary ?? ''}
          onChange={(e) => set({ professional_summary: e.target.value })}
          placeholder="Write a compelling professional summary…"
          className={INPUT + ' resize-none'}
        />
      </div>

      {/* Skills */}
      <div className={CARD}>
        <h2 className="text-base font-bold text-text-primary">Skills</h2>
        <TagInput
          tags={form.skills ?? []}
          onChange={(tags) => set({ skills: tags })}
          placeholder="Add skill and press Enter"
        />
      </div>

      {/* Top Achievements */}
      <div className={CARD}>
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-bold text-text-primary">Top Achievements</h2>
          <span className="text-xs text-text-muted">Max 3 — must be verifiable</span>
        </div>
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col gap-1">
              <label className={LABEL}>Achievement {i + 1}</label>
              <textarea
                rows={2}
                value={(form.top_achievements ?? [])[i] ?? ''}
                onChange={(e) => patchAchievement(i, e.target.value)}
                placeholder={`Describe achievement ${i + 1} with measurable impact…`}
                className={INPUT + ' resize-none'}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Languages */}
      <div className={CARD}>
        <h2 className="text-base font-bold text-text-primary">Languages</h2>
        <TagInput
          tags={form.languages ?? []}
          onChange={(tags) => set({ languages: tags })}
          placeholder="Add language and press Enter"
        />
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        <button type="button" onClick={onCancel} disabled={isSaving} className="rounded-md border border-border-default px-4 py-2 text-sm text-text-primary hover:bg-surface-subtle disabled:opacity-50">
          Cancel
        </button>
        <button type="submit" disabled={isSaving} className="rounded-md bg-primary-action px-4 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50">
          {isSaving ? 'Saving…' : 'Save CV'}
        </button>
      </div>
    </form>
  );
}

// ── CVPreview ─────────────────────────────────────────────────────────────────

function CVPreview({ cv }: { cv: UserCV }) {
  const contact = cv.contact_info;
  const achievements = (cv.top_achievements ?? []).filter((a) => a.trim());
  const languages = cv.languages ?? [];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className={CARD}>
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
            <p className={LABEL + ' mb-1'}>Summary</p>
            <p className="text-sm text-text-primary leading-relaxed">{cv.professional_summary}</p>
          </div>
        )}
      </div>

      {/* Experience */}
      {cv.experience.length > 0 && (
        <div className={CARD}>
          <p className={LABEL}>Experience</p>
          <div className="flex flex-col gap-3">
            {cv.experience.map((exp, i) => (
              <div key={i} className="border-l-2 border-primary-action pl-3">
                <p className="text-sm font-semibold text-text-primary">{exp.role} at {exp.company}</p>
                <p className="text-xs text-text-muted">{exp.dates}{exp.current ? ' · Present' : ''}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skills */}
      {cv.skills.length > 0 && (
        <div className={CARD}>
          <p className={LABEL}>Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {cv.skills.map((s, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-surface-subtle text-text-muted">{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Top Achievements */}
      {achievements.length > 0 && (
        <div className={CARD}>
          <p className={LABEL}>Top Achievements</p>
          <ol className="list-decimal list-inside flex flex-col gap-2">
            {achievements.map((a, i) => (
              <li key={i} className="text-sm text-text-primary leading-relaxed">{a}</li>
            ))}
          </ol>
        </div>
      )}

      {/* Languages */}
      {languages.length > 0 && (
        <div className={CARD}>
          <p className={LABEL}>Languages</p>
          <div className="flex flex-wrap gap-1.5">
            {languages.map((l, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-surface-subtle text-text-muted">{l}</span>
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

// ── Page ──────────────────────────────────────────────────────────────────────

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
          <button onClick={() => setMode('edit')} className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90">
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
          <button onClick={() => setMode('create')} className="rounded-md bg-primary-action px-4 py-2 text-sm font-bold text-white hover:opacity-90">
            Create CV
          </button>
        </div>
      ) : mode === 'edit' || mode === 'create' ? (
        <CVForm initial={cv ?? {}} onSave={handleSave} onCancel={() => setMode('view')} isSaving={isSaving} />
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
