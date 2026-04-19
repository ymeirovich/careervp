export type ModuleType =
  | 'vpr'
  | 'tailoredCV'
  | 'coverLetter'
  | 'interviewPrep'
  | 'gapAnalysis'
  | 'companyResearch'
  | 'baseCV';

export type ModuleStatus =
  | 'notStarted'
  | 'processing'
  | 'ready'
  | 'complete'
  | 'edited'
  | 'stale'
  | 'failed'
  | 'timeout'
  | 'final';

export type HubStatus =
  | 'INIT'
  | 'LOADING'
  | 'READY_PARTIAL'
  | 'READY_COMPLETE'
  | 'STALE_DEPENDENCIES'
  | 'PROCESSING_BLOCKED'
  | 'ERROR_RECOVERABLE'
  | 'FINALIZED';
