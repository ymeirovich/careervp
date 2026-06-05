'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useApplicationHub } from '../../../hooks/useApplicationHub';
import { useGenerateModule } from '../../../hooks/useGenerateModule';
import { ModuleCard } from '../../../components/ModuleCard/ModuleCard';
import { HubLayout } from '../../../components/layout/HubLayout';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../components/ui/Spinner';
import { ChooseBaseCVModal } from '../../../components/ChooseBaseCVModal/ChooseBaseCVModal';
import type { ChooseBaseCVItem } from '../../../components/ChooseBaseCVModal/ChooseBaseCVModal';
import { getArtifact } from '../../../lib/artifactStorage';
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

const GENERATABLE_MODULES = new Set<ModuleType>(['vpr', 'tailoredCV', 'coverLetter', 'interviewPrep']);

export default function ApplicationHubPage() {
  const params = useParams();
  const jobId = typeof params.id === 'string' ? params.id : '';
  const router = useRouter();

  const { hubState, isLoading, gapResponseIds, vprId, companyResearchId, cvId, cvName, refetch } = useApplicationHub(jobId);
  const [showChangeCVModal, setShowChangeCVModal] = useState(false);
  const [selectedCvItem, setSelectedCvItem] = useState<ChooseBaseCVItem | null>(null);
  const [regenConfirmModule, setRegenConfirmModule] = useState<ModuleType | null>(null);

  // Per-module generation errors (set on cancel, cleared on new generate)
  const [generationErrors, setGenerationErrors] = useState<Partial<Record<ModuleType, string>>>({});

  // Active CV: locally-selected override takes precedence over the user's default CV
  const activeCvId = (selectedCvItem?.cv_id ?? selectedCvItem?.id) ?? cvId ?? undefined;
  const activeCvName = selectedCvItem
    ? (selectedCvItem.file_name ?? selectedCvItem.full_name ?? selectedCvItem.name ?? 'Selected CV')
    : cvName ?? undefined;

  // All generators instantiated unconditionally (Rules of Hooks)
  const vprGen = useGenerateModule('vpr', jobId);
  const coverLetterGen = useGenerateModule('coverLetter', jobId);
  const interviewPrepGen = useGenerateModule('interviewPrep', jobId);
  const tailoredCVGen = useGenerateModule('tailoredCV', jobId);

  const genMap = {
    vpr: vprGen,
    coverLetter: coverLetterGen,
    interviewPrep: interviewPrepGen,
    tailoredCV: tailoredCVGen,
  } as const;

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading hub…" />
      </div>
    );
  }

  if (!hubState) return null;

  function clearError(moduleType: ModuleType) {
    setGenerationErrors((prev) => {
      const next = { ...prev };
      delete next[moduleType];
      return next;
    });
  }

  async function handleGenerate(moduleType: ModuleType) {
    clearError(moduleType);
    const cvId = activeCvId;

    const gen = genMap[moduleType as keyof typeof genMap];
    if (gen) {
      await gen.generate({
        cvId,
        vprId: vprId ?? undefined,
        gapResponseIds,
        companyResearchId: companyResearchId ?? undefined,
      });
      // Trigger refetch so hub status updates after generation completes
      refetch();
    }
  }

  async function handleCancel(moduleType: ModuleType) {
    const gen = genMap[moduleType as keyof typeof genMap];
    if (!gen) return;
    const cancelTaskId = gen.taskId ?? getArtifact(jobId, moduleType);
    if (!cancelTaskId) return;
    await gen.cancel(cancelTaskId);
    setGenerationErrors((prev) => ({
      ...prev,
      [moduleType]: 'Generation was cancelled.',
    }));
    refetch();
  }

  function buildPrimaryAction(moduleType: ModuleType): ModuleAction | undefined {
    const moduleState = hubState!.modules[moduleType];
    const { status, primaryAction, resultUrl } = moduleState;

    if (!primaryAction) return undefined;

    let onClick: () => void;

    if (moduleType === 'baseCV') {
      onClick = () => router.push('/cv-center');
      // When a CV exists, relabel the primary action from "Start" to "View"
      if (activeCvId) {
        return { ...primaryAction, label: 'View', variant: 'secondary' as const, onClick };
      }
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
      // stale/edited regenerates an existing artifact → require confirmation
      // notStarted/failed have no existing artifact → generate directly
      const needsConfirmation = status === 'stale' || status === 'edited';
      onClick = needsConfirmation
        ? () => setRegenConfirmModule(moduleType)
        : () => void handleGenerate(moduleType);
    }

    return { ...primaryAction, onClick };
  }

  const ARTIFACT_ROUTES: Partial<Record<ModuleType, (resultUrl?: string) => string>> = {
    vpr: (r) => `/applications/${jobId}/vpr${r ? `?id=${r}` : ''}`,
    coverLetter: (r) => `/applications/${jobId}/cover-letter${r ? `?id=${r}` : ''}`,
    interviewPrep: (r) => `/applications/${jobId}/interview-prep${r ? `?id=${r}` : ''}`,
    tailoredCV: (r) => `/applications/${jobId}/cv-tailored${r ? `?id=${r}` : ''}`,
  };

  function buildSecondaryActions(moduleType: ModuleType): ModuleAction[] | undefined {
    if (moduleType === 'baseCV') {
      return activeCvId
        ? [{ label: 'Change', onClick: () => setShowChangeCVModal(true), variant: 'secondary' as const }]
        : undefined;
    }

    const moduleState = hubState!.modules[moduleType];
    const routeFn = ARTIFACT_ROUTES[moduleType];

    return (moduleState.secondaryActions ?? []).map((action) => {
      if (action.label === 'Regenerate') {
        return { ...action, onClick: () => setRegenConfirmModule(moduleType) };
      }
      if ((action.label === 'View' || action.label === 'Edit') && routeFn) {
        const base = routeFn(moduleState.resultUrl);
        const dest = action.label === 'Edit' ? `${base}&mode=edit` : base;
        return { ...action, onClick: () => router.push(dest) };
      }
      return action;
    });
  }

  const MODULE_DISPLAY_NAMES: Partial<Record<ModuleType, string>> = {
    vpr: 'Value Proposition Report',
    tailoredCV: 'Tailored CV',
    coverLetter: 'Cover Letter',
    interviewPrep: 'Interview Prep',
  };

  const hasNoCV = !activeCvId;
  // Tailored CV requires a completed VPR to provide the vpr_id
  const tailoredCVBlocked = !vprId && hubState.modules.tailoredCV.status === 'notStarted';

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

      <ChooseBaseCVModal
        isOpen={showChangeCVModal}
        onClose={() => setShowChangeCVModal(false)}
        showChoices
        onSelectCV={(item) => {
          setSelectedCvItem(item);
          setShowChangeCVModal(false);
        }}
      />

      {regenConfirmModule && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6"
          onClick={(e) => { if (e.target === e.currentTarget) setRegenConfirmModule(null); }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="regen-confirm-title"
            className="w-full max-w-md rounded-xl border border-border-default bg-card p-6 shadow-lg"
          >
            <h2 id="regen-confirm-title" className="text-lg font-bold text-text-primary">
              Regenerate {MODULE_DISPLAY_NAMES[regenConfirmModule]}?
            </h2>
            <p className="mt-2 text-sm text-text-muted">
              This action will regenerate and overwrite the existing{' '}
              {MODULE_DISPLAY_NAMES[regenConfirmModule]}. Do you want to proceed?
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setRegenConfirmModule(null)}
                className="rounded-lg border border-border-default px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-subtle"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  const mod = regenConfirmModule;
                  setRegenConfirmModule(null);
                  void handleGenerate(mod);
                }}
                className="rounded-lg bg-primary-action px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}

      <HubLayout hubStatus={hubState.hubStatus} staleModules={hubState.staleModules}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MODULE_ORDER.map((moduleType) => {
            const moduleState = hubState.modules[moduleType];
            const gen = GENERATABLE_MODULES.has(moduleType)
              ? genMap[moduleType as keyof typeof genMap]
              : null;

            // Show processing UI optimistically while API call is in-flight
            const isOptimisticallyProcessing = gen?.isGenerating ?? false;
            const effectiveState =
              isOptimisticallyProcessing ? 'processing' : moduleState.status;

            const isActivelyProcessing =
              isOptimisticallyProcessing || moduleState.status === 'processing';

            // Only show cancel when actively processing and a taskId is known
            const cancelTaskId = gen?.taskId ?? getArtifact(jobId, moduleType);
            const cancelAction: ModuleAction | undefined =
              isActivelyProcessing && cancelTaskId
                ? {
                    label: 'Cancel',
                    onClick: () => void handleCancel(moduleType),
                    variant: 'secondary' as const,
                  }
                : undefined;

            const primaryAction = isActivelyProcessing
              ? undefined
              : buildPrimaryAction(moduleType);

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
                  state={effectiveState}
                  title={moduleState.title}
                  subtitle={
                    moduleType === 'baseCV' && activeCvName
                      ? activeCvName
                      : moduleType === 'tailoredCV' && tailoredCVBlocked
                        ? 'Generate your VPR first'
                        : moduleState.subtitle
                  }
                  meta={moduleState.meta}
                  warningText={moduleState.warningText}
                  progressText={moduleState.progressText}
                  badgeLabel={moduleState.badgeLabel}
                  primaryAction={primaryAction}
                  secondaryActions={isActivelyProcessing ? undefined : buildSecondaryActions(moduleType)}
                  cancelAction={cancelAction}
                  errorMessage={generationErrors[moduleType]}
                  disabled={moduleType === 'tailoredCV' && tailoredCVBlocked}
                />
              </ErrorBoundary>
            );
          })}
        </div>
      </HubLayout>
    </ErrorBoundary>
  );
}
