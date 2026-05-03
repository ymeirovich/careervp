import React, { Suspense } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const apiMocks = vi.hoisted(() => ({
  getApplication: vi.fn(),
  getJob: vi.fn(),
  getVPR: vi.fn(),
  exportArtifact: vi.fn(),
}));

// ─── Mock next/navigation ────────────────────────────────────────────────────

const mockReplace = vi.fn();
const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job1' }),
}));

// ─── Mock api ────────────────────────────────────────────────────────────────

vi.mock('../../api/methods', () => ({
  api: apiMocks,
}));

// ─── Helper: wrap in Suspense so use(params) can suspend ─────────────────────

function renderWithSuspense(ui: React.ReactElement) {
  return render(<Suspense fallback={<div data-testid="suspense-fallback" />}>{ui}</Suspense>);
}

// ─── Fixtures ────────────────────────────────────────────────────────────────

const HUB_WITH_VPR = {
  application: { application_id: 'job1', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job1', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
  cv: { cv_id: 'cv1' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'completed' as const, artifact_id: 'art1' },
    cover_letter: { status: 'pending' as const, artifact_id: null },
    interview_prep: { status: 'pending' as const, artifact_id: null },
    cv_tailored: { status: 'pending' as const, artifact_id: null },
    gap_analysis: { status: 'pending' as const, artifact_id: null },
  },
};

const JOB_DETAIL = {
  job_id: 'job1', title: 'Engineer', company_name: 'Acme',
  status: 'active', created_at: '', user_id: 'u1', requirements: [],
};

const VPR_STATUS_WITH_URL = {
  id: 'art1',
  status: 'completed' as const,
  result: { download_url: 'https://s3.example.com/vpr.json' },
};

const VPR_STATUS_SUMMARY_ONLY = {
  id: 'art1',
  status: 'completed' as const,
  result: { uvp: 'Test UVP text' },
};

const FULL_VPR_DATA = {
  applicationId: 'job1',
  metadata: { reportDate: '2026-01-01', candidateName: 'Jane Doe', targetRole: 'Engineer', targetCompany: 'Acme' },
  executiveSummary: {
    overallFitScore: 85,
    fitRationale: 'Strong alignment',
    topThreeStrengths: [{ strength: 'Leadership', evidence: 'Led 3 teams', relevanceToRole: 'Critical' }],
    topThreeConcerns: [{ concern: 'Limited Python', severity: 'medium', mitigation: 'Quick learner' }],
    recommendedApproach: 'aggressive_apply',
  },
  roleAlignment: { coreResponsibilities: [], requirementBreakdown: { mustHave: [], niceToHave: [] } },
  experienceMapping: { relevantExperiences: [], experienceGaps: [] },
  skillsAnalysis: { technicalSkills: [], softSkills: [] },
  evidenceGaps: { priorityGapsToAddress: [] },
  differentiators: { uniqueStrengths: [], positioningStatement: '' },
  concernsAndMitigations: { likelyObjections: [], preemptiveResponses: [] },
  valueProposition: { primaryValue: { statement: '', evidence: '', outcomeForCompany: '' }, elevatorPitch: '' },
  applicationStrategy: {
    messagingApproach: 'Lead with results',
    atsKeywords: { primary: ['Python'], secondary: ['AWS'] },
    cvLeadDifferentiator: 'Results-driven engineer',
    sectionsToCompress: [],
  },
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('VPR page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('renders executive summary section from full VPR data', async () => {
    apiMocks.getApplication.mockResolvedValue(HUB_WITH_VPR);
    apiMocks.getJob.mockResolvedValue(JOB_DETAIL);
    apiMocks.getVPR.mockResolvedValue(VPR_STATUS_WITH_URL);
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => FULL_VPR_DATA,
    });

    const { default: VPRPage } = await import('../../app/applications/[id]/vpr/page');
    renderWithSuspense(<VPRPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('vpr-exec-summary')).toBeDefined();
    }, { timeout: 3000 });

    expect(screen.getByTestId('vpr-fit-score').textContent).toBe('85');
  });

  it('shows fallback summary when no S3 download_url', async () => {
    apiMocks.getApplication.mockResolvedValue(HUB_WITH_VPR);
    apiMocks.getJob.mockResolvedValue(JOB_DETAIL);
    apiMocks.getVPR.mockResolvedValue(VPR_STATUS_SUMMARY_ONLY);

    const { default: VPRPage } = await import('../../app/applications/[id]/vpr/page');
    renderWithSuspense(<VPRPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByText('Test UVP text')).toBeDefined();
    }, { timeout: 3000 });
  });

  it('redirects to hub when artifact not completed', async () => {
    const hubNoArtifact = {
      ...HUB_WITH_VPR,
      artifacts: {
        ...HUB_WITH_VPR.artifacts,
        vpr: { status: 'processing' as const, artifact_id: null },
      },
    };
    apiMocks.getApplication.mockResolvedValue(hubNoArtifact);
    apiMocks.getJob.mockResolvedValue(JOB_DETAIL);

    const { default: VPRPage } = await import('../../app/applications/[id]/vpr/page');
    renderWithSuspense(<VPRPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/applications/job1');
    }, { timeout: 3000 });
  });

  it('shows error state when fetch fails', async () => {
    apiMocks.getApplication.mockResolvedValue(HUB_WITH_VPR);
    apiMocks.getJob.mockResolvedValue(JOB_DETAIL);

    const apiError = Object.assign(new Error('Server error'), { status: 500, isApiError: true });
    apiMocks.getVPR.mockRejectedValue(apiError);

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);

    const { default: VPRPage } = await import('../../app/applications/[id]/vpr/page');
    renderWithSuspense(<VPRPage params={Promise.resolve({ id: 'job1' })} />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load value proposition report/i)).toBeDefined();
    }, { timeout: 3000 });

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });
});
