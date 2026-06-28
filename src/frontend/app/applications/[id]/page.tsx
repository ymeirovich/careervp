'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useApplicationHub } from '../../../hooks/useApplicationHub';
import { useGenerateModule } from '../../../hooks/useGenerateModule';
import { ModuleCard } from '../../../components/ModuleCard/ModuleCard';
import { HubLayout } from '../../../components/layout/HubLayout';
import { ErrorBoundary } from '../../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../../components/ui/Spinner';
import { WarningBanner } from '../../../components/ui/WarningBanner';
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

const GENERATABLE_MODULES = new Set<ModuleType>(['vpr', 'tailoredCV', 'coverLetter', 'interviewPrep', 'companyResearch']);
const CHAIN_MODULES: ModuleType[] = ['vpr', 'tailoredCV', 'coverLetter', 'interviewPrep'];

function isReadyLikeStatus(status: string): boolean {
  return ['ready', 'complete', 'edited', 'stale', 'final'].includes(status);
}

function ChainProgressBar({
  companyResearchStatus,
  vprStatus,
  tailoredCvStatus,
}: {
  companyResearchStatus: string;
  vprStatus: string;
  tailoredCvStatus: string;
}) {
  const steps = [
    { key: 'cr', label: 'CR', status: companyResearchStatus },
    { key: 'vpr', label: 'VPR', status: vprStatus },
    { key: 'cv', label: 'Tailored CV', status: tailoredCvStatus },
  ];

  return (
    <div
      data-testid="chain-progress-bar"
      className="rounded-2xl border border-border-default bg-card/90 px-4 py-4"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        {steps.map((step, index) => {
          const isDone = isReadyLikeStatus(step.status);
          const isProcessing = step.status === 'processing';
          const badgeClass = isDone
            ? 'border-state-active bg-state-active text-white'
            : isProcessing
              ? 'border-state-warning bg-state-warning/10 text-state-warning'
              : 'border-border-default bg-surface-subtle text-text-muted';

          return (
            <React.Fragment key={step.key}>
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold ${badgeClass}`}
                >
                  {isDone ? '✓' : isProcessing ? '...' : `${index + 1}`}
                </span>
                <div className="flex flex-col">
                  <span className="text-sm font-semibold text-text-primary">{step.label}</span>
                  <span className="text-xs text-text-muted">
                    {isDone ? 'Done' : isProcessing ? 'Processing' : 'Waiting'}
                  </span>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className="hidden h-px flex-1 bg-border-default md:block" aria-hidden="true" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

export default function ApplicationHubPage() {
  const params = useParams();
  const jobId = typeof params.id === 'string' ? params.id : '';
  const router = useRouter();

  const {
    hubState,
    isLoading,
    gapResponseIds,
    vprId,
    companyResearchId,
    cvId,
    cvName,
    refetch,
    companyResearchError,
    applicationState,
    companyName,
    jobUrl,
  } = useApplicationHub(jobId);
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
  const companyResearchGen = useGenerateModule('companyResearch', jobId);

  const genMap = {
    vpr: vprGen,
    coverLetter: coverLetterGen,
    interviewPrep: interviewPrepGen,
    tailoredCV: tailoredCVGen,
    companyResearch: companyResearchGen,
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
      try {
        // An explicit (re)generate from the hub must bypass the backend idempotency
        // short-circuit, otherwise a previously completed VPR (including one whose S3
        // result expired) is returned unchanged and the worker is never re-invoked.
        await gen.generate({
          cvId,
          vprId: vprId ?? undefined,
          gapResponseIds,
          companyResearchId: companyResearchId ?? undefined,
          force: true,
          companyName: companyName ?? undefined,
          jobUrl: jobUrl ?? undefined,
        });
        // Trigger refetch so hub status updates after generation completes
        refetch();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Generation failed';
        setGenerationErrors((prev) => ({ ...prev, [moduleType]: message }));
      }
    }
  }

  async function handleCancel(moduleType: ModuleType) {
    const gen = genMap[moduleType as keyof typeof genMap];
    if (!gen) return;
    const cancelTaskId = gen.taskId ?? getArtifact(jobId, moduleType);
    // Pass empty string when taskId not yet known — AbortController in hook handles abort
    await gen.cancel(cancelTaskId ?? '');
    setGenerationErrors((prev) => ({
      ...prev,
      [moduleType]: 'Generation was cancelled.',
    }));
    refetch();
  }

  function getGenerationBlockReason(moduleType: ModuleType, actionLabel: string): string | undefined {
    if (!CHAIN_MODULES.includes(moduleType)) {
      return undefined;
    }

    const isGenerationAction = ['Generate', 'Regenerate', 'Retry'].includes(actionLabel);
    if (!isGenerationAction) {
      return undefined;
    }

    if (companyResearchError) {
      return 'Requires company research';
    }

    if (applicationState === 'cr_pending') {
      return 'Company research is in progress';
    }

    return undefined;
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
      if (companyResearchError) {
        return {
          ...primaryAction,
          label: 'Retry',
          variant: 'primary' as const,
          onClick: () => void handleGenerate('companyResearch'),
        };
      }
      onClick = () => router.push(`/applications/${jobId}/company-research`);
      if (companyResearchId) {
        return { ...primaryAction, label: 'View', variant: 'secondary' as const, onClick };
      }
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

    const disabledReason = getGenerationBlockReason(moduleType, primaryAction.label);
    return { ...primaryAction, onClick, disabled: Boolean(disabledReason), disabledReason };
  }

  const ARTIFACT_ROUTES: Partial<Record<ModuleType, (resultUrl?: string) => string>> = {
    vpr: (r) => `/applications/${jobId}/vpr${r ? `?id=${r}` : ''}`,
    coverLetter: (r) => `/applications/${jobId}/cover-letter${r ? `?id=${r}` : ''}`,
    interviewPrep: (r) => `/applications/${jobId}/interview-prep${r ? `?id=${r}` : ''}`,
    tailoredCV: (r) => `/applications/${jobId}/cv-tailored${r ? `?id=${r}` : ''}`,
    gapAnalysis: () => `/applications/${jobId}/gap-analysis`,
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
        const disabledReason = getGenerationBlockReason(moduleType, action.label);
        return {
          ...action,
          onClick: () => setRegenConfirmModule(moduleType),
          disabled: Boolean(disabledReason),
          disabledReason,
        };
      }
      if ((action.label === 'View' || action.label === 'Edit') && routeFn) {
        const base = routeFn(moduleState.resultUrl);
        const dest = action.label === 'Edit' ? `${base}${base.includes('?') ? '&' : '?'}mode=edit` : base;
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
  const companyResearchStatus = companyResearchError ? 'failed' : hubState.modules.companyResearch.status;
  const showChainProgress =
    !companyResearchError &&
    (applicationState === 'cr_pending' ||
      (applicationState === 'artifacts_generating' &&
        companyResearchStatus !== 'notStarted'));

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
              {regenConfirmModule === 'tailoredCV'
                ? 'Generate New Tailored CV?'
                : `Regenerate ${MODULE_DISPLAY_NAMES[regenConfirmModule]}?`}
            </h2>
            <p className="mt-2 text-sm text-text-muted">
              {regenConfirmModule === 'tailoredCV'
                ? 'A new tailored CV will be generated. Your previous CV stays available in the Tailored CVs list.'
                : (
                  <>
                    This action will regenerate and overwrite the existing{' '}
                    {MODULE_DISPLAY_NAMES[regenConfirmModule]}. Do you want to proceed?
                  </>
                )}
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
                  if (mod) {
                    void handleGenerate(mod);
                  }
                }}
                className="rounded-lg bg-primary-action px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                {regenConfirmModule === 'tailoredCV' ? 'Generate New Version' : 'OK'}
              </button>
            </div>
          </div>
        </div>
      )}

      <HubLayout hubStatus={hubState.hubStatus} staleModules={hubState.staleModules}>
        {companyResearchError && (
          <WarningBanner
            message="Company research failed. Retry to unlock your documents."
          />
        )}

        {showChainProgress && (
          <ChainProgressBar
            companyResearchStatus={applicationState === 'cr_pending' ? 'processing' : companyResearchStatus}
            vprStatus={hubState.modules.vpr.status}
            tailoredCvStatus={hubState.modules.tailoredCV.status}
          />
        )}

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

            const cancelTaskId = gen?.taskId ?? getArtifact(jobId, moduleType);
            // Cancel renders while actively processing when either:
            //   (a) gen.isGenerating — optimistic window; AbortController handles abort before taskId
            //   (b) a taskId is known — we can call the backend cancel endpoint
            const cancelAction: ModuleAction | undefined =
              isActivelyProcessing && (gen?.isGenerating || cancelTaskId)
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
