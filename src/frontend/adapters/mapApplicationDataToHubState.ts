import type { ModuleType, ModuleStatus, HubStatus } from '../types/enums';
import type {
  RawApplicationData,
  RawModuleData,
  RawCVData,
  RawGapAnalysisData,
  HubModuleState,
  HubState,
  ModuleAction,
} from '../types/hub-state';

const ALL_MODULE_TYPES: ModuleType[] = [
  'vpr',
  'tailoredCV',
  'coverLetter',
  'interviewPrep',
  'gapAnalysis',
  'companyResearch',
  'baseCV',
];

const CRITICAL_MODULES: ModuleType[] = ['vpr', 'gapAnalysis', 'baseCV'];

const MODULE_TITLES: Record<ModuleType, string> = {
  vpr: 'Value Proposition Report',
  tailoredCV: 'Tailored CV',
  coverLetter: 'Cover Letter',
  interviewPrep: 'Interview Prep',
  gapAnalysis: 'Gap Analysis',
  companyResearch: 'Company Research',
  baseCV: 'Base CV',
};

export function deriveModuleStatus(
  moduleType: ModuleType,
  rawStatus: RawModuleData['status'] | null,
  isStale: boolean,
  isFinalized: boolean
): ModuleStatus {
  if (rawStatus === null || rawStatus === undefined) return 'notStarted';
  if (rawStatus === 'cancelled') return 'notStarted';
  if (rawStatus === 'pending' || rawStatus === 'processing') return 'processing';
  if (rawStatus === 'failed') return 'failed';
  // completed
  if (isFinalized) return 'final';
  if (isStale) return 'stale';
  return 'ready';
}

export function detectStaleness(
  moduleData: Partial<Record<ModuleType, RawModuleData>>,
  gapAnalysis: RawGapAnalysisData | null
): Set<ModuleType> {
  const stale = new Set<ModuleType>();

  const vprModule = moduleData.vpr;
  if (gapAnalysis?.responses_submitted_at && vprModule) {
    if (gapAnalysis.responses_submitted_at > vprModule.created_at) {
      stale.add('vpr');
      stale.add('coverLetter');
      stale.add('interviewPrep');
    }
  }

  return stale;
}

const AVAILABLE_STATUSES: ModuleStatus[] = ['ready', 'complete', 'edited', 'stale', 'final'];

function isAvailable(status: ModuleStatus): boolean {
  return AVAILABLE_STATUSES.includes(status);
}

export function deriveHubStatus(
  moduleStatuses: Record<ModuleType, ModuleStatus>,
  staleModules: Set<ModuleType>,
  isFinalized: boolean
): HubStatus {
  if (isFinalized) return 'FINALIZED';

  const statuses = Object.values(moduleStatuses) as ModuleStatus[];

  if (statuses.every((s) => s === 'notStarted')) return 'INIT';

  if (statuses.some((s) => s === 'processing')) return 'LOADING';

  if (
    CRITICAL_MODULES.some((m) => moduleStatuses[m] === 'failed')
  ) return 'ERROR_RECOVERABLE';

  if (staleModules.size > 0) return 'STALE_DEPENDENCIES';

  // PROCESSING_BLOCKED: gap analysis not started but upstream prereqs are available
  if (
    moduleStatuses.gapAnalysis === 'notStarted' &&
    (isAvailable(moduleStatuses.companyResearch) || isAvailable(moduleStatuses.baseCV))
  ) return 'PROCESSING_BLOCKED';

  if (statuses.every((s) => s === 'complete' || s === 'final')) return 'READY_COMPLETE';

  const hasCompleted = statuses.some((s) => s === 'complete' || s === 'ready');
  const hasNotStarted = statuses.some((s) => s === 'notStarted');
  if (hasCompleted && hasNotStarted) return 'READY_PARTIAL';

  return 'LOADING';
}

function getPrimaryLabel(moduleType: ModuleType, status: ModuleStatus): string | null {
  switch (status) {
    case 'notStarted': return moduleType === 'baseCV' ? 'Start' : 'Generate';
    case 'processing': return null;
    case 'ready': return 'View';
    case 'complete': return 'View';
    case 'edited': return 'Regenerate';
    case 'stale': return 'Regenerate';
    case 'failed': return 'Retry';
    case 'timeout': return 'Refresh';
    case 'final': return 'Export';
    default: return null;
  }
}

function getSecondaryLabels(status: ModuleStatus): string[] {
  switch (status) {
    case 'ready': return ['Edit', 'Regenerate'];
    case 'complete': return ['Edit', 'History'];
    case 'edited': return ['Regenerate', 'History'];
    case 'stale': return ['View'];
    case 'final': return ['History'];
    default: return [];
  }
}

function getBadgeLabel(status: ModuleStatus): string | undefined {
  switch (status) {
    case 'edited': return 'Edited';
    case 'stale': return 'Outdated';
    case 'final': return 'Final';
    default: return undefined;
  }
}

function makeAction(label: string, variant: ModuleAction['variant'] = 'secondary'): ModuleAction {
  return { label, onClick: () => {}, variant };
}

export function buildHubModuleState(
  moduleType: ModuleType,
  status: ModuleStatus,
  rawData: RawModuleData | null,
  isStale: boolean,
  isFinalized: boolean
): HubModuleState {
  const primaryLabel = getPrimaryLabel(moduleType, status);
  const secondaryLabels = getSecondaryLabels(status);

  return {
    type: moduleType,
    status,
    title: MODULE_TITLES[moduleType],
    badgeLabel: getBadgeLabel(status),
    progressText: rawData?.progress_text,
    resultUrl: rawData?.result_url,
    warningText: isStale ? `${MODULE_TITLES[moduleType]} is outdated` : undefined,
    primaryAction: primaryLabel
      ? makeAction(primaryLabel, status === 'notStarted' || status === 'failed' || status === 'stale' ? 'primary' : 'secondary')
      : undefined,
    secondaryActions: secondaryLabels.map((l) => makeAction(l)),
    isStale,
  };
}

export function mapApplicationDataToHubState(
  application: RawApplicationData,
  moduleData: Partial<Record<ModuleType, RawModuleData>>,
  gapAnalysis: RawGapAnalysisData | null,
  cvData: RawCVData | null
): HubState {
  const staleSet = detectStaleness(moduleData, gapAnalysis);

  const moduleStatuses = {} as Record<ModuleType, ModuleStatus>;
  for (const m of ALL_MODULE_TYPES) {
    if (m === 'baseCV') {
      moduleStatuses[m] = cvData?.cv_id ? 'ready' : 'notStarted';
    } else {
      const raw = moduleData[m] ?? null;
      moduleStatuses[m] = deriveModuleStatus(m, raw?.status ?? null, staleSet.has(m), application.is_finalized);
    }
  }

  const hubStatus = deriveHubStatus(moduleStatuses, staleSet, application.is_finalized);

  const modules = {} as Record<ModuleType, HubModuleState>;
  for (const m of ALL_MODULE_TYPES) {
    modules[m] = buildHubModuleState(
      m,
      moduleStatuses[m],
      moduleData[m] ?? null,
      staleSet.has(m),
      application.is_finalized
    );
  }

  const completedStatuses: ModuleStatus[] = ['ready', 'complete', 'edited', 'stale', 'final'];
  const completedCount = ALL_MODULE_TYPES.filter((m) =>
    completedStatuses.includes(moduleStatuses[m])
  ).length;

  return {
    hubStatus,
    modules,
    completedCount,
    totalCount: 7,
    progressPercent: Math.round((completedCount / 7) * 100),
    staleModules: Array.from(staleSet),
    isFinalized: application.is_finalized,
  };
}
