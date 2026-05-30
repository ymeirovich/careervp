import React from 'react';
import type { HubStatus } from '../../types/enums';
import type { ModuleType } from '../../types/enums';
import { WarningBanner } from '../ui/WarningBanner';

export interface HubLayoutProps {
  hubStatus: HubStatus;
  staleModules?: ModuleType[];
  jobDetailHeaderSlot?: React.ReactNode;
  children: React.ReactNode;
}

export function HubLayout({ hubStatus, staleModules, jobDetailHeaderSlot, children }: HubLayoutProps) {
  const showStaleBanner = hubStatus === 'STALE_DEPENDENCIES';
  const showErrorBanner = hubStatus === 'ERROR_RECOVERABLE';
  const showBlockedBanner = hubStatus === 'PROCESSING_BLOCKED';

  return (
    <div className="flex flex-col gap-4">
      {jobDetailHeaderSlot}

      {showBlockedBanner && (
        <div
          data-testid="hub-blocked-banner"
          className="bg-state-info/10 border border-state-info text-state-info rounded-xl px-4 py-3 text-sm font-medium"
        >
          Complete Gap Analysis to unlock remaining modules.
        </div>
      )}

      {showStaleBanner && (
        <WarningBanner
          message="Some modules are outdated because your CV was updated."
          staleModules={staleModules}
        />
      )}

      {showErrorBanner && (
        <WarningBanner message="One or more modules failed. Retry to continue." />
      )}

      {children}
    </div>
  );
}
