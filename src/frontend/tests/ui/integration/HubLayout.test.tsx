import '../../vitest-setup';
import '../setup';

import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { HubModuleState, HubState } from '../../../types/hub-state';
import type { ModuleType } from '../../../types/enums';

const nextNavigationMocks = vi.hoisted(() => ({
  push: vi.fn(),
}));

const applicationHubMocks = vi.hoisted(() => ({
  hubState: null as HubState | null,
  isLoading: false,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'app_123' }),
  useRouter: () => ({ push: nextNavigationMocks.push }),
}));

vi.mock('../../../hooks/useApplicationHub', () => ({
  useApplicationHub: () => ({
    hubState: applicationHubMocks.hubState,
    isLoading: applicationHubMocks.isLoading,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../../../hooks/useCV', () => ({
  useCV: () => ({
    cv: { cv_id: 'cv_123' },
    isLoading: false,
    isSaving: false,
    saveCV: vi.fn(),
    error: null,
  }),
}));

vi.mock('../../../hooks/useGenerateModule', () => ({
  useGenerateModule: () => ({
    generate: vi.fn().mockResolvedValue(undefined),
    isGenerating: false,
    taskId: null,
    error: null,
  }),
}));

vi.mock('../../../components/ModuleCard/ModuleCard', () => ({
  ModuleCard: ({ module }: { module: ModuleType }) => <div data-testid={`module-card-${module}`} />,
}));

import ApplicationHubPage from '../../../app/applications/[id]/page';

function buildHubModuleState(moduleType: ModuleType): HubModuleState {
  return {
    type: moduleType,
    status: 'notStarted',
    title: moduleType,
    isStale: false,
  };
}

function buildHubState(): HubState {
  const modules: Record<ModuleType, HubModuleState> = {
    baseCV: buildHubModuleState('baseCV'),
    gapAnalysis: buildHubModuleState('gapAnalysis'),
    vpr: buildHubModuleState('vpr'),
    tailoredCV: buildHubModuleState('tailoredCV'),
    coverLetter: buildHubModuleState('coverLetter'),
    interviewPrep: buildHubModuleState('interviewPrep'),
    companyResearch: buildHubModuleState('companyResearch'),
  };

  return {
    hubStatus: 'INIT',
    modules,
    completedCount: 0,
    totalCount: 0,
    progressPercent: 0,
    staleModules: [],
    isFinalized: false,
  };
}

describe('FE-UI-005 integration — ApplicationHubPage grid defaults', () => {
  beforeEach(() => {
    nextNavigationMocks.push.mockReset();
    applicationHubMocks.isLoading = false;
    applicationHubMocks.hubState = buildHubState();
  });

  it('renders the module grid as a 2-column max layout (no xl:grid-cols-3)', () => {
    render(<ApplicationHubPage />);

    const vprCard = screen.getByTestId('module-card-vpr');
    const grid = vprCard.parentElement;

    expect(grid).not.toBeNull();
    expect(grid).toHaveClass('grid');
    expect(grid).toHaveClass('grid-cols-1');
    expect(grid).toHaveClass('md:grid-cols-2');
    expect(grid).not.toHaveClass('xl:grid-cols-3');
  });
});
