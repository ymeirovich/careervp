'use client';

import React from 'react';
import { ModuleCard } from '../../../components/ModuleCard/ModuleCard';
import type { ModuleType } from '../../../types/enums';

// TODO: Wire to useApplicationHub hook (spec-03)
// TODO: Fetch module statuses with adaptive polling (spec-03)

const MODULE_ORDER: ModuleType[] = [
  'baseCV',
  'gapAnalysis',
  'vpr',
  'tailoredCV',
  'coverLetter',
  'interviewPrep',
  'companyResearch',
];

export default function ApplicationHubPage() {
  return (
    <div className="flex flex-col gap-6">
      <div
        data-testid="hub-blocked-banner"
        className="hidden bg-state-warning/10 border border-state-warning text-state-warning rounded-lg px-4 py-3 text-sm font-medium"
      >
        Complete Gap Analysis to unlock remaining modules.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {MODULE_ORDER.map((module) => (
          <ModuleCard
            key={module}
            module={module}
            state="notStarted"
            title=""
            onPrimaryAction={() => {
              // TODO: Wire to useGenerateModule mutation (spec-03)
              console.log('Generate', module);
            }}
          />
        ))}
      </div>
    </div>
  );
}
