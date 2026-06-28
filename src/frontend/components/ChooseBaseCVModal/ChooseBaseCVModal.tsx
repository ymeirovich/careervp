'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, Upload, X } from 'lucide-react';
import { apiClient } from '../../api/client';
import { Button } from '../ui/Button';

export type ChooseBaseCVKind = 'uploaded' | 'generated';

export interface ChooseBaseCVItem {
  cv_id?: string;
  id?: string;
  user_id?: string;
  full_name?: string;
  file_name?: string;
  name?: string;
  title?: string;
  language?: 'en' | 'he' | string;
  created_at?: string;
  updated_at?: string;
  generated_at?: string;
  uploaded_at?: string;
  source?: string;
  type?: string;
  cv_type?: string;
  is_generated?: boolean;
}

interface ChooseBaseCVModalProps {
  isOpen: boolean;
  onClose: () => void;
  showChoices?: boolean;
  onSelectCV?: (cv: ChooseBaseCVItem, kind: ChooseBaseCVKind) => void;
  onUpload?: (file: File) => void | Promise<void>;
}

type Copy = {
  chooseTitle: string;
  uploadTitle: string;
  choiceSubtitle: string;
  uploadSubtitle: string;
  selectUploaded: string;
  selectGenerated: string;
  or: string;
  uploadNew: string;
  cvFile: string;
  chooseFile: string;
  noFile: string;
  upload: string;
  close: string;
  cancel: string;
  noCvs: string;
  loading: string;
  error: string;
  name: string;
  type: string;
  updated: string;
  uploaded: string;
  generated: string;
  select: string;
};

const TEXT: Record<'en' | 'he', Copy> = {
  en: {
    cancel: 'Cancel',
    chooseFile: 'Choose File',
    chooseTitle: 'Choose Base CV',
    choiceSubtitle: 'Select an existing CV or upload a new base CV.',
    close: 'Close',
    cvFile: 'CV File',
    error: 'Failed to load CVs.',
    generated: 'Generated',
    loading: 'Loading CVs...',
    name: 'Name',
    noCvs: 'No CVs available',
    noFile: 'No file chosen',
    or: 'OR',
    select: 'Select',
    selectGenerated: 'Select generated CV',
    selectUploaded: 'Select uploaded CV',
    type: 'Type',
    updated: 'Updated',
    upload: 'Upload',
    uploadNew: 'Upload New CV',
    uploadSubtitle: 'Upload your CV in PDF, DOC, or DOCX format.',
    uploadTitle: 'Upload Base CV',
    uploaded: 'Uploaded',
  },
  he: {
    cancel: 'ביטול',
    chooseFile: 'בחר קובץ',
    chooseTitle: 'בחר קורות חיים בסיסיים',
    choiceSubtitle: 'בחר קורות חיים קיימים או העלה קורות חיים בסיסיים חדשים.',
    close: 'סגור',
    cvFile: 'קובץ קורות חיים',
    error: 'טעינת קורות החיים נכשלה.',
    generated: 'נוצרו',
    loading: 'טוען קורות חיים...',
    name: 'שם',
    noCvs: 'אין קורות חיים זמינים',
    noFile: 'לא נבחר קובץ',
    or: 'או',
    select: 'בחר',
    selectGenerated: 'בחר קורות חיים שנוצרו',
    selectUploaded: 'בחר קורות חיים שהועלו',
    type: 'סוג',
    updated: 'עודכן',
    upload: 'העלה',
    uploadNew: 'העלה קורות חיים חדשים',
    uploadSubtitle: 'העלה את קורות החיים בפורמט PDF, DOC או DOCX.',
    uploadTitle: 'העלה קורות חיים בסיסיים',
    uploaded: 'הועלו',
  },
};

const focusableSelector = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function isHebrewLocale() {
  return typeof document !== 'undefined' && document.documentElement.lang.toLowerCase().startsWith('he');
}

function getCopy() {
  return isHebrewLocale() ? TEXT.he : TEXT.en;
}

function getCvId(cv: ChooseBaseCVItem) {
  return cv.cv_id ?? cv.id ?? cv.file_name ?? cv.name ?? cv.title ?? 'cv';
}

function getCvName(cv: ChooseBaseCVItem) {
  return cv.file_name ?? cv.full_name ?? cv.name ?? cv.title ?? getCvId(cv);
}

function getCvKind(cv: ChooseBaseCVItem): ChooseBaseCVKind {
  const rawType = `${cv.cv_type ?? cv.type ?? cv.source ?? ''}`.toLowerCase();
  if (cv.is_generated || rawType.includes('generated') || rawType.includes('tailored') || rawType.includes('vpr')) {
    return 'generated';
  }
  return 'uploaded';
}

function getCvDate(cv: ChooseBaseCVItem) {
  const value = cv.updated_at ?? cv.uploaded_at ?? cv.generated_at ?? cv.created_at;
  if (!value) return '';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

function parseCVs(data: unknown): ChooseBaseCVItem[] {
  if (Array.isArray(data)) return data.filter((item): item is ChooseBaseCVItem => typeof item === 'object' && item !== null);
  if (typeof data !== 'object' || data === null) return [];

  const payload = data as {
    cvs?: unknown;
    uploaded_cvs?: unknown;
    generated_cvs?: unknown;
    tailored_cvs?: unknown;
  };

  const uploaded = Array.isArray(payload.uploaded_cvs)
    ? payload.uploaded_cvs
      .filter((cv): cv is ChooseBaseCVItem => typeof cv === 'object' && cv !== null)
      .map((cv) => ({ ...cv, cv_type: 'uploaded' }))
    : [];
  const generated = [
    ...(Array.isArray(payload.generated_cvs) ? payload.generated_cvs : []),
    ...(Array.isArray(payload.tailored_cvs) ? payload.tailored_cvs : []),
  ]
    .filter((cv): cv is ChooseBaseCVItem => typeof cv === 'object' && cv !== null)
    .map((cv) => ({ ...cv, cv_type: 'generated' }));
  const cvs = Array.isArray(payload.cvs) ? payload.cvs : [];

  return [...cvs, ...uploaded, ...generated].filter((item): item is ChooseBaseCVItem => typeof item === 'object' && item !== null);
}

export function ChooseBaseCVModal({
  isOpen,
  onClose,
  showChoices = true,
  onSelectCV,
  onUpload,
}: ChooseBaseCVModalProps) {
  const copy = getCopy();
  const titleId = 'choose-base-cv-modal-title';
  const descriptionId = 'choose-base-cv-modal-description';
  const dialogRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [cvs, setCvs] = useState<ChooseBaseCVItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeKind, setActiveKind] = useState<ChooseBaseCVKind>('uploaded');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(focusableSelector);
    firstFocusable?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !showChoices) return;

    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);

    apiClient
      .get<unknown>('/users/me/cv')
      .then((response) => {
        if (!cancelled) setCvs(parseCVs(response.data));
      })
      .catch(() => {
        if (!cancelled) {
          setCvs([]);
          setLoadError(copy.error);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [copy.error, isOpen, showChoices]);

  const uploadedCVs = useMemo(() => cvs.filter((cv) => getCvKind(cv) === 'uploaded'), [cvs]);
  const generatedCVs = useMemo(() => cvs.filter((cv) => getCvKind(cv) === 'generated'), [cvs]);
  const visibleCVs = activeKind === 'uploaded' ? uploadedCVs : generatedCVs;
  const hasAnyCVs = uploadedCVs.length > 0 || generatedCVs.length > 0;
  const uploadAreaHighlight = showChoices && !hasAnyCVs;

  if (!isOpen) return null;

  const selectFirst = (kind: ChooseBaseCVKind) => {
    setActiveKind(kind);
    const cv = kind === 'uploaded' ? uploadedCVs[0] : generatedCVs[0];
    if (cv) onSelectCV?.(cv, kind);
  };

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onClose();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }

    if (event.key !== 'Tab') return;

    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? []);
    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !onUpload) return;

    setIsUploading(true);
    try {
      await onUpload(selectedFile);
    } finally {
      setIsUploading(false);
    }
  };

  const renderCVRows = () => {
    if (isLoading) {
      return (
        <tr>
          <td colSpan={4} className="px-4 py-8 text-center text-sm text-text-muted">
            {copy.loading}
          </td>
        </tr>
      );
    }

    if (loadError) {
      return (
        <tr>
          <td colSpan={4} className="px-4 py-8 text-center text-sm text-state-error">
            {loadError}
          </td>
        </tr>
      );
    }

    if (visibleCVs.length === 0) {
      return (
        <tr>
          <td colSpan={4} className="px-4 py-8 text-center text-sm text-text-muted">
            {copy.noCvs}
          </td>
        </tr>
      );
    }

    return visibleCVs.map((cv, index) => {
      const kind = getCvKind(cv);
      return (
        <tr
          key={`${kind}-${getCvId(cv)}-${index}`}
          data-testid={`choose-base-cv-row-${kind}`}
          className={`border-b border-border-default last:border-b-0 ${index % 2 === 0 ? 'bg-white' : 'bg-surface-subtle'}`}
        >
          <td className="px-4 py-3 text-sm font-medium text-text-primary">{getCvName(cv)}</td>
          <td className="px-4 py-3 text-sm text-text-muted">{kind === 'generated' ? copy.generated : copy.uploaded}</td>
          <td className="px-4 py-3 text-sm text-text-muted">{getCvDate(cv)}</td>
          <td className="px-4 py-3 text-right">
            <Button type="button" variant="secondary" size="sm" onClick={() => onSelectCV?.(cv, kind)}>
              {copy.select}
            </Button>
          </td>
        </tr>
      );
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      data-testid="choose-base-cv-modal-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className={`
          relative w-full max-w-2xl rounded-xl border border-border-default bg-card p-6 shadow-lg outline-none
          max-h-[calc(100vh-3rem)] overflow-y-auto
        `.trim()}
      >
        <button
          type="button"
          aria-label={copy.close}
          onClick={onClose}
          className={`
            absolute right-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-md border border-border-default
            bg-surface-subtle text-text-primary hover:bg-surface-selected focus:outline-none focus:ring-2 focus:ring-primary-action
          `.trim()}
        >
          <X size={18} aria-hidden="true" />
        </button>

        <div className="pr-10">
          <h2 id={titleId} className="text-xl font-bold text-text-primary">
            {showChoices ? copy.chooseTitle : copy.uploadTitle}
          </h2>
          <p id={descriptionId} className="mt-2 text-sm text-text-muted">
            {showChoices ? copy.choiceSubtitle : copy.uploadSubtitle}
          </p>
        </div>

        {showChoices && (
          <div className="mt-6 flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Button
                type="button"
                variant={activeKind === 'uploaded' ? 'primary' : 'secondary'}
                size="md"
                disabled={uploadedCVs.length === 0}
                onClick={() => selectFirst('uploaded')}
                className="justify-start"
              >
                <FileText size={18} aria-hidden="true" />
                {copy.selectUploaded}
              </Button>
              <Button
                type="button"
                variant={activeKind === 'generated' ? 'primary' : 'secondary'}
                size="md"
                disabled={generatedCVs.length === 0}
                onClick={() => selectFirst('generated')}
                className="justify-start"
              >
                <FileText size={18} aria-hidden="true" />
                {copy.selectGenerated}
              </Button>
            </div>

            <div className="overflow-x-auto rounded-md border border-border-default">
              <table className="w-full border-collapse" data-testid="choose-base-cv-table">
                <thead className="bg-surface-subtle">
                  <tr className="border-b border-border-default">
                    <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-text-muted">{copy.name}</th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-text-muted">{copy.type}</th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-text-muted">{copy.updated}</th>
                    <th scope="col" className="px-4 py-3 text-right text-sm font-medium text-text-muted">{copy.select}</th>
                  </tr>
                </thead>
                <tbody>{renderCVRows()}</tbody>
              </table>
            </div>

            <div className="flex items-center gap-3 text-xs font-bold uppercase text-text-muted">
              <div className="h-px flex-1 bg-border-default" />
              <span>{copy.or}</span>
              <div className="h-px flex-1 bg-border-default" />
            </div>
          </div>
        )}

        <form
          className={`mt-6 rounded-md border p-4 ${
            uploadAreaHighlight ? 'border-primary-action bg-surface-selected' : 'border-border-default bg-card'
          }`}
          onSubmit={(event) => {
            event.preventDefault();
            void handleUpload();
          }}
        >
          {showChoices && <h3 className="text-base font-bold text-text-primary">{copy.uploadNew}</h3>}
          <div className="mt-4 flex flex-col gap-2">
            <label htmlFor="choose-base-cv-file" className="text-xs font-semibold uppercase text-text-muted">
              {copy.cvFile}
            </label>
            <input
              ref={fileInputRef}
              id="choose-base-cv-file"
              data-testid="choose-base-cv-file-input"
              type="file"
              accept=".pdf,.doc,.docx"
              className="sr-only"
              onChange={(event) => setSelectedFile(event.currentTarget.files?.[0] ?? null)}
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button
                type="button"
                variant="secondary"
                size="md"
                onClick={() => fileInputRef.current?.click()}
                data-testid="choose-base-cv-file-trigger"
              >
                <Upload size={18} aria-hidden="true" />
                {showChoices ? copy.uploadNew : copy.chooseFile}
              </Button>
              <span className="min-w-0 break-words text-sm text-text-muted">
                {selectedFile ? selectedFile.name : copy.noFile}
              </span>
            </div>
          </div>

          <div className="mt-5 flex justify-end gap-3">
            <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={isUploading}>
              {copy.cancel}
            </Button>
            <Button type="submit" variant="primary" size="md" disabled={!selectedFile || isUploading} isLoading={isUploading}>
              {copy.upload}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
