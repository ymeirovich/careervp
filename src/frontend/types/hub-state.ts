import type { ModuleType, ModuleStatus, HubStatus } from './enums';

export interface RawApplicationData {
  application_id: string;
  job_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  is_finalized: boolean;
  finalized_at?: string;
  state?: string;
  trial_credit_consumed?: boolean;
  company_research_error?: boolean;
}

export interface RawModuleData {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'expired' | 'not_generated';
  created_at: string;
  updated_at: string;
  result_url?: string;
  error_message?: string;
  progress_text?: string;
}

export interface GapQuestion {
  id: string;
  question: string;
}

export interface GapResponse {
  question_id: string;
  answer: string;
}

export interface RawGapAnalysisData {
  job_id: string;
  questions: GapQuestion[];
  responses?: GapResponse[];
  responses_submitted_at?: string;
}

export interface RawCVData {
  cv_id?: string;
  full_name?: string;
}

export interface ModuleAction {
  label: string;
  onClick: () => void;
  variant: 'primary' | 'secondary' | 'ghost' | 'destructive';
  isLoading?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

export interface HubModuleState {
  type: ModuleType;
  status: ModuleStatus;
  title: string;
  subtitle?: string;
  meta?: string;
  warningText?: string;
  progressText?: string;
  badgeLabel?: string;
  resultUrl?: string;
  primaryAction?: ModuleAction;
  secondaryActions?: ModuleAction[];
  isStale: boolean;
  staleReason?: string;
}

export interface HubState {
  hubStatus: HubStatus;
  modules: Record<ModuleType, HubModuleState>;
  completedCount: number;
  totalCount: number;
  progressPercent: number;
  staleModules: ModuleType[];
  blockedReason?: string;
  isFinalized: boolean;
}

export type { ModuleType, ModuleStatus, HubStatus };
