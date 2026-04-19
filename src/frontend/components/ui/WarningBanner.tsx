import React from 'react';
import type { ModuleType } from '../../types/enums';

const MODULE_LABELS: Record<ModuleType, string> = {
  vpr: 'VPR',
  tailoredCV: 'Tailored CV',
  coverLetter: 'Cover Letter',
  interviewPrep: 'Interview Prep',
  gapAnalysis: 'Gap Analysis',
  companyResearch: 'Company Research',
  baseCV: 'Base CV',
};

export interface WarningBannerProps {
  message: string;
  staleModules?: ModuleType[];
  onDismiss?: () => void;
}

export function WarningBanner({ message, staleModules, onDismiss }: WarningBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 bg-state-warning/10 border border-state-warning text-state-warning rounded-xl px-4 py-3"
    >
      <span className="text-lg leading-none mt-0.5" aria-hidden="true">⚠</span>
      <div className="flex-1 text-sm font-medium">
        <p>{message}</p>
        {staleModules && staleModules.length > 0 && (
          <p className="mt-1 text-text-muted text-sm">
            Affected: {staleModules.map((m) => MODULE_LABELS[m]).join(', ')}
          </p>
        )}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-state-warning hover:opacity-70 text-lg leading-none"
          aria-label="Dismiss warning"
        >
          ×
        </button>
      )}
    </div>
  );
}
