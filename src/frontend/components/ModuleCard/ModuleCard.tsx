import React, { useRef, useEffect } from 'react';
import type { ModuleType, ModuleStatus } from '../../types/enums';
import type { ButtonVariant } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Spinner } from '../ui/Spinner';
import { Tooltip } from '../ui/Tooltip';

export interface ModuleAction {
  label: string;
  onClick: () => void;
  variant?: ButtonVariant;
  isLoading?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

export interface ModuleCardProps {
  module: ModuleType;
  state: ModuleStatus;
  title: string;
  subtitle?: string;
  description?: string;
  meta?: string;
  warningText?: string;
  progressText?: string;
  badgeLabel?: string;
  primaryAction?: ModuleAction;
  secondaryActions?: ModuleAction[];
  cancelAction?: ModuleAction;
  errorMessage?: string;
  disabled?: boolean;
  // Convenience props for simple callers
  onPrimaryAction?: () => void;
  onSecondaryAction?: () => void;
}

const MODULE_LABELS: Record<ModuleType, string> = {
  vpr:             'Value Proposition Report',
  tailoredCV:      'Tailored CV',
  coverLetter:     'Cover Letter',
  interviewPrep:   'Interview Prep',
  gapAnalysis:     'Gap Analysis',
  companyResearch: 'Company Research',
  baseCV:          'Base CV',
};

// CTA rules — EXACT labels enforced by cta-label-consistency.test.ts
function getPrimaryLabel(module: ModuleType, state: ModuleStatus): string | null {
  switch (state) {
    case 'notStarted': return module === 'baseCV' ? 'Start' : 'Generate';
    case 'processing':  return null;
    case 'ready':       return 'View';
    case 'complete':    return 'View';
    case 'edited':      return 'Regenerate';
    case 'stale':       return 'Regenerate';
    case 'failed':      return 'Retry';
    case 'timeout':     return 'Refresh';
    case 'final':       return 'Export';
  }
}

function getDefaultSecondary(state: ModuleStatus): string[] {
  switch (state) {
    case 'ready':    return ['Edit', 'Regenerate'];
    case 'complete': return ['Edit', 'History'];
    case 'edited':   return ['History'];
    case 'stale':    return ['View'];
    case 'final':    return ['History'];
    default:         return [];
  }
}

function getBadgeLabel(state: ModuleStatus, override?: string): string | null {
  if (override) return override;
  switch (state) {
    case 'edited': return 'Edited';
    case 'stale':  return 'Outdated';
    case 'final':  return 'Final';
    default:       return null;
  }
}

export function ModuleCard({
  module,
  state,
  title,
  subtitle,
  description,
  meta,
  warningText,
  progressText,
  badgeLabel,
  primaryAction,
  secondaryActions,
  cancelAction,
  errorMessage,
  disabled = false,
  onPrimaryAction,
  onSecondaryAction,
}: ModuleCardProps) {
  const isProcessing = state === 'processing';
  const primaryLabel = primaryAction?.label ?? getPrimaryLabel(module, state);
  const displayedBadge = getBadgeLabel(state, badgeLabel);
  const defaultSecondary = getDefaultSecondary(state);

  // Focus management: announce state transitions to assistive tech
  const liveRef = useRef<HTMLSpanElement>(null);
  const prevState = useRef(state);
  useEffect(() => {
    if (prevState.current !== state && liveRef.current) {
      liveRef.current.textContent = `${title || MODULE_LABELS[module]} is now ${state}`;
    }
    prevState.current = state;
  }, [state, module, title]);

  const badgeVariantMap = {
    Edited: 'edited',
    Outdated: 'stale',
    Final: 'final',
  } as const;

  function renderActionButton(
    action: ModuleAction,
    key: string,
    isPrimary = false,
  ): React.ReactNode {
    const button = (
      <Button
        key={key}
        data-testid={isPrimary ? 'primary-cta' : undefined}
        variant={action.variant ?? (isPrimary ? 'primary' : 'secondary')}
        size="sm"
        isLoading={action.isLoading}
        onClick={action.onClick}
        disabled={disabled || action.disabled}
      >
        {action.label}
      </Button>
    );

    if (!action.disabledReason) {
      return button;
    }

    return (
      <Tooltip key={key} content={action.disabledReason}>
        <span className="inline-flex cursor-not-allowed">{button}</span>
      </Tooltip>
    );
  }

  return (
    <div
      data-testid={`module-card-${module}`}
      aria-label={`${title || MODULE_LABELS[module]}, ${state}`}
      aria-busy={isProcessing || undefined}
      className={`
        bg-card border border-border-default rounded-xl p-4 flex flex-col gap-3
        ${disabled ? 'opacity-50' : ''}
      `.trim()}
    >
      {/* Screen-reader live region for state transitions */}
      <span ref={liveRef} className="sr-only" aria-live="polite" aria-atomic="true" />

      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-text-primary text-base leading-snug">
            {title || MODULE_LABELS[module]}
          </h3>
          {subtitle && <p className="text-text-muted text-sm mt-0.5">{subtitle}</p>}
        </div>
        {displayedBadge && (
          <Badge
            variant={badgeVariantMap[displayedBadge as keyof typeof badgeVariantMap] ?? 'neutral'}
            label={displayedBadge}
            data-testid="status-badge"
          />
        )}
      </div>

      {description && <p className="text-text-muted text-sm">{description}</p>}
      {meta && <p className="text-text-subtle text-xs font-medium">{meta}</p>}

      {isProcessing && !cancelAction && (
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Spinner size="sm" aria-label={`Generating ${title || MODULE_LABELS[module]}…`} />
          <span>{progressText ?? 'Generating…'}</span>
        </div>
      )}

      {state === 'failed' && (
        <p className="text-state-error text-sm">Generation failed. Please retry.</p>
      )}
      {state === 'timeout' && (
        <p className="text-text-muted text-sm">Still processing — check back shortly.</p>
      )}
      {state === 'stale' && warningText && (
        <p className="text-state-warning text-sm">{warningText}</p>
      )}

      {errorMessage && (
        <p className="text-state-error text-sm">{errorMessage}</p>
      )}

      {/* Processing state with cancel: disabled "Processing..." button + Cancel */}
      {isProcessing && cancelAction && (
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <button
            type="button"
            disabled
            className="inline-flex items-center gap-1 rounded-lg bg-primary-action px-3 py-1.5 text-sm font-medium text-white opacity-60 cursor-not-allowed"
          >
            Processing<span aria-hidden="true" className="animate-pulse">...</span>
          </button>
          <Button
            variant={cancelAction.variant ?? 'secondary'}
            size="sm"
            onClick={cancelAction.onClick}
          >
            {cancelAction.label}
          </Button>
        </div>
      )}

      {/* Normal (non-processing) action buttons */}
      {!isProcessing && (primaryLabel || defaultSecondary.length > 0 || secondaryActions) && (
        <div className="flex flex-wrap items-center gap-2 mt-1">
          {primaryLabel &&
            renderActionButton(
              {
                label: primaryLabel,
                onClick: primaryAction?.onClick ?? onPrimaryAction ?? (() => {}),
                variant: primaryAction?.variant ?? 'primary',
                isLoading: primaryAction?.isLoading,
                disabled: primaryAction?.disabled,
                disabledReason: primaryAction?.disabledReason,
              },
              'primary',
              true,
            )}

          {(secondaryActions ?? defaultSecondary.map((label): ModuleAction => ({ label, onClick: onSecondaryAction ?? (() => {}), variant: 'secondary' }))).map((action) =>
            renderActionButton(action, action.label),
          )}
        </div>
      )}
    </div>
  );
}
