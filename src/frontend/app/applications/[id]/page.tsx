'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useApplicationHub } from '../../../hooks/useApplicationHub';
import { useGenerateModule } from '../../../hooks/useGenerateModule';
import { useCV } from '../../../hooks/useCV';
import { ModuleCard } from '../../../components/ModuleCard/ModuleCard';
import { HubLayout } from '../../../components/layout/HubLayout';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../components/ui/Spinner';
import type { ModuleType } from '../../../types/enums';
import type { ModuleAction } from '../../../types/hub-state';

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
  const params = useParams();
  const jobId = typeof params.id === 'string' ? params.id : '';
  const router = useRouter();

  const { hubState, isLoading, gapResponseIds } = useApplicationHub(jobId);
  const { cv } = useCV();

  // All generators instantiated unconditionally (Rules of Hooks)
  const vprGen = useGenerateModule('vpr', jobId);
  const coverLetterGen = useGenerateModule('coverLetter', jobId);
  const interviewPrepGen = useGenerateModule('interviewPrep', jobId);
  const tailoredCVGen = useGenerateModule('tailoredCV', jobId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading hub…" />
      </div>
    );
  }

  if (!hubState) return null;

  async function handleGenerate(moduleType: ModuleType) {
    const cvId = cv?.cv_id;
    const vprArtifactId = hubState?.modules.vpr.resultUrl ?? undefined;

    const genMap = {
      vpr: vprGen,
      coverLetter: coverLetterGen,
      interviewPrep: interviewPrepGen,
      tailoredCV: tailoredCVGen,
    } as const;

    const gen = genMap[moduleType as keyof typeof genMap];
    if (gen) {
      await gen.generate({ cvId, vprId: vprArtifactId, gapResponseIds });
    }
  }

  function buildPrimaryAction(moduleType: ModuleType): ModuleAction | undefined {
    const moduleState = hubState!.modules[moduleType];
    const { status, primaryAction, resultUrl } = moduleState;

    if (!primaryAction) return undefined;

    let onClick: () => void;

    if (moduleType === 'baseCV') {
      onClick = () => router.push('/cv-center');
    } else if (moduleType === 'gapAnalysis') {
      onClick = () => router.push(`/applications/${jobId}/gap-analysis`);
    } else if (moduleType === 'companyResearch') {
      onClick = () => router.push(`/applications/${jobId}/company-research`);
    } else if (status === 'ready' || status === 'complete' || status === 'final') {
      const moduleRoutes: Partial<Record<ModuleType, string>> = {
        vpr: `/applications/${jobId}/vpr${resultUrl ? `?id=${resultUrl}` : ''}`,
        coverLetter: `/applications/${jobId}/cover-letter${resultUrl ? `?id=${resultUrl}` : ''}`,
        interviewPrep: `/applications/${jobId}/interview-prep${resultUrl ? `?id=${resultUrl}` : ''}`,
        tailoredCV: `/applications/${jobId}/cv-tailored${resultUrl ? `?id=${resultUrl}` : ''}`,
      };
      const dest = moduleRoutes[moduleType] ?? '/dashboard';
      onClick = () => router.push(dest);
    } else {
      // notStarted, failed, stale, edited → generate
      onClick = () => void handleGenerate(moduleType);
    }

    return { ...primaryAction, onClick };
  }

  const hasNoCV = !cv?.cv_id;

  return (
    <ErrorBoundary cloudwatchKey="application-hub">
      {hasNoCV && (
        <div
          data-testid="hub-blocked-banner"
          className="bg-state-info/10 border border-state-info text-state-info rounded-xl px-4 py-3 text-sm font-medium mb-4"
        >
          Upload your CV to unlock all CareerVP features.{' '}
          <button
            onClick={() => router.push('/cv-center')}
            className="underline font-semibold hover:opacity-75"
          >
            Upload CV
          </button>
        </div>
      )}

      <HubLayout hubStatus={hubState.hubStatus} staleModules={hubState.staleModules}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MODULE_ORDER.map((moduleType) => {
            const moduleState = hubState.modules[moduleType];
            const primaryAction = buildPrimaryAction(moduleType);

            return (
              <ErrorBoundary
                key={moduleType}
                cloudwatchKey={`module-card-${moduleType}`}
                fallback={
                  <div className="bg-card border border-border-default rounded-xl p-4 text-text-muted text-sm">
                    This module failed to load.
                  </div>
                }
              >
                <ModuleCard
                  module={moduleType}
                  state={moduleState.status}
                  title={moduleState.title}
                  subtitle={moduleState.subtitle}
                  meta={moduleState.meta}
                  warningText={moduleState.warningText}
                  progressText={moduleState.progressText}
                  badgeLabel={moduleState.badgeLabel}
                  primaryAction={primaryAction}
                  secondaryActions={moduleState.secondaryActions}
                />
              </ErrorBoundary>
            );
          })}
        </div>
      </HubLayout>
    </ErrorBoundary>
  );
}
