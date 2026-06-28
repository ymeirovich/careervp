import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardContext } from '../../contexts/DashboardContext';
import type { DashboardContextValue } from '../../contexts/DashboardContext';
import type { HubState } from '../../types/hub-state';
import type { ModuleType } from '../../types/enums';

const apiMocks = vi.hoisted(() => ({
  fetchCompanyResearch: vi.fn().mockResolvedValue({ request_id: 'cr-retry-1', status: 'processing' }),
}));

// ── next/navigation mocks ──────────────────────────────────────────────────
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useParams: () => ({ id: 'job1' }),
}));

vi.mock('../../api/methods', () => ({
  api: apiMocks,
}));

// ── Hook mocks ──────────────────────────────────────────────────────────────
const mockGenerate = vi.fn().mockResolvedValue(undefined);

vi.mock('../../hooks/useGenerateModule', () => ({
  useGenerateModule: () => ({
    generate: mockGenerate,
    isGenerating: false,
    taskId: null,
    error: null,
  }),
}));

vi.mock('../../hooks/useCV', () => ({
  useCV: () => ({
    cv: { cv_id: 'cv-1' },
    isLoading: false,
    isSaving: false,
    saveCV: vi.fn(),
    error: null,
  }),
}));

const mockApplicationHub = vi.fn();
vi.mock('../../hooks/useApplicationHub', () => ({
  useApplicationHub: (...args: unknown[]) => mockApplicationHub(...args),
}));

const mockJobs = vi.fn();
vi.mock('../../hooks/useJobs', () => ({
  useJobs: () => mockJobs(),
}));

// ── Helpers ─────────────────────────────────────────────────────────────────
function makeHubState(overrides: Partial<HubState> = {}): HubState {
  const ALL: ModuleType[] = [
    'baseCV', 'gapAnalysis', 'vpr', 'tailoredCV',
    'coverLetter', 'interviewPrep', 'companyResearch',
  ];
  const modules = Object.fromEntries(
    ALL.map((m) => [
      m,
      {
        type: m,
        status: 'notStarted' as const,
        title: m,
        isStale: false,
        primaryAction: { label: 'Generate', onClick: vi.fn(), variant: 'primary' as const },
        secondaryActions: [],
      },
    ]),
  ) as unknown as HubState['modules'];

  return {
    hubStatus: 'INIT',
    modules,
    completedCount: 0,
    totalCount: 7,
    progressPercent: 0,
    staleModules: [],
    isFinalized: false,
    ...overrides,
  };
}

function makeDashboardCtx(partial: Partial<DashboardContextValue> = {}): DashboardContextValue {
  return {
    userName: 'Test User',
    usage: null,
    subscription: null,
    hasActiveAccess: true,
    applicationsRemaining: null,
    ...partial,
  };
}

function renderWithProviders(
  ui: React.ReactElement,
  dashCtx: DashboardContextValue = makeDashboardCtx(),
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <DashboardContext.Provider value={dashCtx}>
        {ui}
      </DashboardContext.Provider>
    </QueryClientProvider>,
  );
}

// Lazy-import pages so mocks are established first
async function getHubPage() {
  const mod = await import('../../app/applications/[id]/page');
  return mod.default;
}

async function getDashboardPage() {
  const mod = await import('../../app/dashboard/page');
  return mod.default;
}

// ── Tests ───────────────────────────────────────────────────────────────────
describe('ApplicationHubPage — action handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGenerate.mockResolvedValue(undefined);
  });

  it('Generate CTA calls useGenerateModule.generate with correct moduleType', async () => {
    const hubState = makeHubState();
    mockApplicationHub.mockReturnValue({ hubState, isLoading: false, error: null, refetch: vi.fn(), gapResponseIds: [], vprId: null, companyResearchId: null, cvId: 'cv-1', cvName: null, companyResearchError: false, applicationState: null });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    const vprCard = screen.getByTestId('module-card-vpr');
    const btn = vprCard.querySelector('[data-testid="primary-cta"]') as HTMLButtonElement;
    expect(btn).toBeTruthy();

    await act(async () => {
      fireEvent.click(btn);
    });

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledTimes(1);
    });
  });

  it('View CTA navigates to artifact page with artifact ID', async () => {
    const hubState = makeHubState({
      modules: {
        ...makeHubState().modules,
        vpr: {
          type: 'vpr',
          status: 'ready',
          title: 'VPR',
          isStale: false,
          resultUrl: 'art1',
          primaryAction: { label: 'View', onClick: vi.fn(), variant: 'secondary' as const },
          secondaryActions: [],
        },
      },
    });
    mockApplicationHub.mockReturnValue({ hubState, isLoading: false, error: null, refetch: vi.fn(), gapResponseIds: [], vprId: null, companyResearchId: null, cvId: 'cv-1', cvName: null, companyResearchError: false, applicationState: null });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    const vprCard = screen.getByTestId('module-card-vpr');
    const btn = vprCard.querySelector('[data-testid="primary-cta"]') as HTMLButtonElement;
    expect(btn).toBeTruthy();

    fireEvent.click(btn);

    expect(mockPush).toHaveBeenCalledWith('/applications/job1/vpr?id=art1');
  });

  it('Spinner shown when module status is processing', async () => {
    const hubState = makeHubState({
      modules: {
        ...makeHubState().modules,
        vpr: {
          type: 'vpr',
          status: 'processing',
          title: 'VPR',
          isStale: false,
          primaryAction: undefined,
          secondaryActions: [],
        },
      },
    });
    mockApplicationHub.mockReturnValue({ hubState, isLoading: false, error: null, refetch: vi.fn(), gapResponseIds: [], vprId: null, companyResearchId: null, cvId: 'cv-1', cvName: null, companyResearchError: false, applicationState: null });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    const vprCard = screen.getByTestId('module-card-vpr');
    expect(vprCard.querySelector('[data-testid="spinner"]')).toBeTruthy();
    expect(vprCard.querySelector('[data-testid="primary-cta"]')).toBeNull();
  });

  it('shows CR failure warning, disables downstream generation, and retries company research in place', async () => {
    const refetch = vi.fn();
    const hubState = makeHubState({
      modules: {
        ...makeHubState().modules,
        companyResearch: {
          type: 'companyResearch',
          status: 'failed',
          title: 'Company Research',
          isStale: false,
          primaryAction: { label: 'Retry', onClick: vi.fn(), variant: 'primary' as const },
          secondaryActions: [],
        },
      },
    });
    mockApplicationHub.mockReturnValue({
      hubState,
      isLoading: false,
      error: null,
      refetch,
      gapResponseIds: [],
      vprId: null,
      companyResearchId: null,
      cvId: 'cv-1',
      cvName: null,
      companyResearchError: true,
      applicationState: 'cr_failed',
    });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    expect(screen.getByRole('alert')).toHaveTextContent('Company research failed. Retry to unlock your documents.');
    expect(screen.getByTestId('module-card-vpr').querySelector('[data-testid="primary-cta"]')).toBeDisabled();

    await act(async () => {
      fireEvent.click(screen.getByTestId('module-card-companyResearch').querySelector('[data-testid="primary-cta"]') as HTMLButtonElement);
    });

    // CR retry now goes through the unified generate path (useGenerateModule) with force:true
    expect(mockGenerate).toHaveBeenCalledWith(expect.objectContaining({ force: true }));
    expect(refetch).toHaveBeenCalled();
  });

  it('shows chain progress and disables manual generation while cr_pending is active', async () => {
    const hubState = makeHubState({
      modules: {
        ...makeHubState().modules,
        companyResearch: {
          type: 'companyResearch',
          status: 'processing',
          title: 'Company Research',
          isStale: false,
          primaryAction: undefined,
          secondaryActions: [],
        },
      },
    });
    mockApplicationHub.mockReturnValue({
      hubState,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      gapResponseIds: [],
      vprId: null,
      companyResearchId: null,
      cvId: 'cv-1',
      cvName: null,
      companyResearchError: false,
      applicationState: 'cr_pending',
    });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    expect(screen.getByTestId('chain-progress-bar')).toBeInTheDocument();
    expect(screen.getByText('CR')).toBeInTheDocument();
    expect(screen.getByText('Tailored CV')).toBeInTheDocument();
    expect(screen.getByTestId('module-card-vpr').querySelector('[data-testid="primary-cta"]')).toBeDisabled();
  });

  it('uses the tailored CV versioning copy in the regenerate modal', async () => {
    const hubState = makeHubState({
      modules: {
        ...makeHubState().modules,
        tailoredCV: {
          type: 'tailoredCV',
          status: 'edited',
          title: 'Tailored CV',
          isStale: false,
          primaryAction: { label: 'Regenerate', onClick: vi.fn(), variant: 'primary' as const },
          secondaryActions: [],
        },
      },
    });
    mockApplicationHub.mockReturnValue({
      hubState,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      gapResponseIds: [],
      vprId: 'vpr-1',
      companyResearchId: 'cr-1',
      cvId: 'cv-1',
      cvName: 'Base CV',
      companyResearchError: false,
      applicationState: null,
    });

    const HubPage = await getHubPage();
    renderWithProviders(<HubPage />);

    fireEvent.click(screen.getByTestId('module-card-tailoredCV').querySelector('[data-testid="primary-cta"]') as HTMLButtonElement);

    expect(screen.getByRole('dialog')).toHaveTextContent('Generate New Tailored CV?');
    expect(screen.getByRole('dialog')).toHaveTextContent('Your previous CV stays available in the Tailored CVs list.');
    expect(screen.getByRole('button', { name: 'Generate New Version' })).toBeInTheDocument();
  });
});

describe('DashboardPage — UsageGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockJobs.mockReturnValue({ jobs: [], isLoading: false, createJob: vi.fn(), isCreating: false, error: null });
  });

  it('UsageGate hides New Application button when hasActiveAccess=false', async () => {
    const DashPage = await getDashboardPage();
    renderWithProviders(<DashPage />, makeDashboardCtx({ hasActiveAccess: false }));

    expect(screen.queryByTestId('new-application-btn')).toBeNull();
    expect(screen.getByTestId('usage-gate-no-subscription')).toBeDefined();
  });

  it('UsageGate shows New Application button when hasActiveAccess=true', async () => {
    const DashPage = await getDashboardPage();
    renderWithProviders(<DashPage />, makeDashboardCtx({ hasActiveAccess: true }));

    expect(screen.getByTestId('new-application-btn')).toBeDefined();
    expect(screen.queryByTestId('usage-gate-no-subscription')).toBeNull();
  });

  it('New Application button navigates to the full-page form', async () => {
    const DashPage = await getDashboardPage();
    renderWithProviders(<DashPage />, makeDashboardCtx({ hasActiveAccess: true }));

    fireEvent.click(screen.getByTestId('new-application-btn'));

    expect(mockPush).toHaveBeenCalledWith('/applications/new');
  });
});
