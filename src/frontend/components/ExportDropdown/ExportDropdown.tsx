'use client';

import React, { useState, useRef, useEffect } from 'react';
import { api } from '../../api/methods';
import { ApiError } from '../../api/client';

interface ExportDropdownProps {
  jobId: string;
  moduleType: 'vpr' | 'cover_letter' | 'interview_prep' | 'cv_tailored';
  artifactId: string;
  companyName?: string;
  jobTitle?: string;
}

const ARTIFACT_TYPE_LABELS: Record<ExportDropdownProps['moduleType'], string> = {
  vpr: 'VPR',
  cover_letter: 'Cover_Letter',
  interview_prep: 'Interview_Prep',
  cv_tailored: 'Tailored_CV',
};

const FORMATS = [
  { label: 'Download as Word (.docx)', format: 'docx' as const },
  { label: 'Download as PDF', format: 'pdf' as const },
];

export function ExportDropdown({ jobId, moduleType, artifactId, companyName, jobTitle }: ExportDropdownProps) {
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  async function handleExport(format: 'docx' | 'pdf') {
    setOpen(false);
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.exportArtifact(jobId, moduleType, format);
      const sanitize = (s: string) => s.trim().replace(/\s+/g, '_').replace(/[^\w-]/g, '');
      const company = sanitize(companyName ?? '');
      const title = sanitize(jobTitle ?? '');
      const artifactLabel = ARTIFACT_TYPE_LABELS[moduleType];
      const filename = company && title
        ? `${company}-${title}-${artifactLabel}.${format}`
        : `${moduleType}-${jobId}.${format}`;
      const a = document.createElement('a');
      a.href = response.download_url;
      a.download = filename;
      a.click();
    } catch (err) {
      if (err instanceof ApiError && err.status === 501) {
        setError('Export is coming soon!');
      } else {
        setError('Download failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="relative" ref={ref} data-testid="export-dropdown">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={isLoading}
        className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle disabled:opacity-50 flex items-center gap-1.5"
      >
        {isLoading ? 'Exporting…' : 'Export'}
        <span className="text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-52 rounded-md border border-border-default bg-card shadow-md z-20">
          {FORMATS.map(({ label, format }) => (
            <button
              key={format}
              onClick={() => void handleExport(format)}
              className="w-full text-left px-4 py-2.5 text-sm text-text-primary hover:bg-surface-subtle first:rounded-t-md last:rounded-b-md"
              title="Export coming soon"
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="absolute right-0 mt-1 text-xs text-state-error bg-card border border-state-error rounded-md px-3 py-2 whitespace-nowrap z-20">
          {error}
        </p>
      )}
    </div>
  );
}
