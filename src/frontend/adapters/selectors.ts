import type { ModuleType, HubStatus } from '../types/enums';
import type { HubState, HubModuleState } from '../types/hub-state';

export function selectHubStatus(hubState: HubState): HubStatus {
  return hubState.hubStatus;
}

export function selectModuleState(hubState: HubState, moduleType: ModuleType): HubModuleState {
  return hubState.modules[moduleType];
}

export function selectStaleModules(hubState: HubState): ModuleType[] {
  return hubState.staleModules;
}

export function selectIsBlocked(hubState: HubState): boolean {
  return hubState.hubStatus === 'PROCESSING_BLOCKED';
}

export function selectProgressPercent(hubState: HubState): number {
  return hubState.progressPercent;
}
