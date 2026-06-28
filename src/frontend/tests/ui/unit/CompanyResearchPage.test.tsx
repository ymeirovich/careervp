import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';

// ─── Hoist API mocks ─────────────────────────────────────────────────────────

const apiMocks = vi.hoisted(() => ({
  getCompanyResearchStatus: vi.fn(),
  getApplication: vi.fn(),
  fetchCompanyResearch: vi.fn(),
}));

// ─── Mock next/navigation ────────────────────────────────────────────────────

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job1' }),
}));

// ─── Mock api/methods ────────────────────────────────────────────────────────

vi.mock('../../../api/methods', () => ({
  api: apiMocks,
}));

// ─── Fixtures ────────────────────────────────────────────────────────────────

const APP_DATA = {
  application: { application_id: 'job1', state: 'active', created_at: '', trial_credit_consumed: false },
  job: {
    job_id: 'job1', user_id: 'u1', title: 'Engineer', company_name: 'Acme',
    status: 'active', created_at: '', requirements: [], url: 'https://acme.com/jobs/1',
  },
  cv: { cv_id: 'cv1' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'pending' as const, artifact_id: null },
    cover_letter: { status: 'pending' as const, artifact_id: null },
    interview_prep: { status: 'pending' as const, artifact_id: null },
    cv_tailored: { status: 'pending' as const, artifact_id: null },
    gap_analysis: { status: 'pending' as const, artifact_id: null },
  },
};

const COMPLETED_DATA = {
  company_name: 'Acme Corp',
  industry: 'Technology',
  size_range: '1000-5000',
  funding_status: 'Public',
  mission: 'Build great software',
  culture: 'Collaborative',
  values: ['Integrity', 'Innovation'],
  products: ['Product A'],
  recent_news: [{ title: 'Acme raises Series C', date: '2026-01-01' }],
};

// ─── Helper: import inner component (bypasses Suspense / use(params)) ─────────

async function importContent() {
  const mod = await import('../../../app/applications/[id]/company-research/page');
  return mod.CompanyResearchContent;
}

// ─── Category A: mount_polling → SC1, SC5 ────────────────────────────────────

describe('mount_polling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    apiMocks.getApplication.mockResolvedValue(APP_DATA);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('test_mount_processing_starts_polling', async () => {
    apiMocks.getCompanyResearchStatus
      .mockResolvedValueOnce({ status: 'processing', data: null })
      .mockResolvedValue({ status: 'completed', data: COMPLETED_DATA });

    const Content = await importContent();

    await act(async () => {
      render(<Content jobId="job1" />);
    });

    // After first render: processing state, no research card
    expect(screen.queryByText('Acme Corp')).toBeNull();
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(1);

    // Advance 10s → first poll tick fires, returns completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(2);

    // Advance 10s more to ensure React has re-rendered
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    // Research card should now be rendered
    expect(screen.getByText('Acme Corp')).toBeDefined();
  }, 15_000);

  it('test_poll_cleanup_on_unmount', async () => {
    apiMocks.getCompanyResearchStatus.mockResolvedValue({ status: 'processing', data: null });

    const Content = await importContent();

    let unmount: () => void;
    await act(async () => {
      const result = render(<Content jobId="job1" />);
      unmount = result.unmount;
    });

    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(1);

    // Advance 5s (no poll tick yet - interval is 10s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });

    // Unmount - should clearInterval
    act(() => { unmount(); });

    const callsAtUnmount = apiMocks.getCompanyResearchStatus.mock.calls.length;

    // Advance 15s more - no additional calls should happen after unmount
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });

    expect(apiMocks.getCompanyResearchStatus.mock.calls.length).toBe(callsAtUnmount);
  }, 15_000);
});

// ─── Category B: remount_resume → SC1, SC2 ───────────────────────────────────

describe('remount_resume', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    apiMocks.getApplication.mockResolvedValue(APP_DATA);
    apiMocks.fetchCompanyResearch.mockResolvedValue({ task_id: 'task1' });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('test_remount_mid_run_resumes', async () => {
    apiMocks.getCompanyResearchStatus
      .mockResolvedValueOnce({ status: 'processing', data: null }) // first mount
      .mockResolvedValueOnce({ status: 'processing', data: null }) // remount
      .mockResolvedValue({ status: 'completed', data: COMPLETED_DATA }); // poll ticks

    const Content = await importContent();

    // First render
    let unmount: () => void;
    await act(async () => {
      const result = render(<Content jobId="job1" />);
      unmount = result.unmount;
    });
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(1);

    // Unmount (navigate away)
    act(() => { unmount(); });

    // Remount (return to page)
    await act(async () => {
      render(<Content jobId="job1" />);
    });

    // Assert: getCompanyResearchStatus called again on remount (no POST fired)
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(2);
    expect(apiMocks.fetchCompanyResearch).not.toHaveBeenCalled();

    // Advance timers to trigger poll tick → completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(screen.getByText('Acme Corp')).toBeDefined();
  }, 15_000);

  it('test_navigate_away_and_return', async () => {
    apiMocks.getCompanyResearchStatus
      .mockResolvedValueOnce({ status: 'processing', data: null }) // first mount
      .mockResolvedValueOnce({ status: 'processing', data: null }) // remount
      .mockResolvedValue({ status: 'completed', data: COMPLETED_DATA }); // poll ticks

    const Content = await importContent();

    // Render (GET=processing)
    let unmount: () => void;
    await act(async () => {
      const result = render(<Content jobId="job1" />);
      unmount = result.unmount;
    });
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(1);

    // Unmount (navigate away)
    act(() => { unmount(); });

    // Remount (return)
    await act(async () => {
      render(<Content jobId="job1" />);
    });
    expect(apiMocks.getCompanyResearchStatus).toHaveBeenCalledTimes(2);

    // Advance timers to completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(screen.getByText('Acme Corp')).toBeDefined();

    // fetchCompanyResearch was never called
    expect(apiMocks.fetchCompanyResearch).not.toHaveBeenCalled();
  }, 15_000);
});

// ─── Category C: not_generated_cta → SC3 ─────────────────────────────────────

describe('not_generated_cta', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(APP_DATA);
  });

  it('test_not_generated_renders_cta', async () => {
    apiMocks.getCompanyResearchStatus.mockResolvedValue({ status: 'not_generated', data: null });

    const Content = await importContent();

    await act(async () => {
      render(<Content jobId="job1" />);
    });

    // Assert: "Research this company" button visible
    await waitFor(() => {
      expect(screen.getByTestId('research-company-btn')).toBeDefined();
    }, { timeout: 3000 });
    expect(screen.getByTestId('research-company-btn').textContent).toBe('Research this company');

    // Assert: NO element with role="alert" rendered
    expect(screen.queryByRole('alert')).toBeNull();

    // Assert: no error div present
    expect(screen.queryByText(/failed/i)).toBeNull();
    expect(screen.queryByText(/error/i)).toBeNull();
  });
});

// ─── Category D: terminal_states → SC4 ───────────────────────────────────────

describe('terminal_states', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getApplication.mockResolvedValue(APP_DATA);
  });

  it('test_failed_renders_error', async () => {
    apiMocks.getCompanyResearchStatus.mockResolvedValue({ status: 'failed', data: null });

    const Content = await importContent();

    await act(async () => {
      render(<Content jobId="job1" />);
    });

    // Assert: error div rendered
    await waitFor(() => {
      expect(screen.getByText(/company research failed/i)).toBeDefined();
    }, { timeout: 3000 });

    // Assert: no research card
    expect(screen.queryByText('Acme Corp')).toBeNull();
  });

  it('test_completed_renders_card', async () => {
    apiMocks.getCompanyResearchStatus.mockResolvedValue({
      status: 'completed',
      data: COMPLETED_DATA,
    });

    const Content = await importContent();

    await act(async () => {
      render(<Content jobId="job1" />);
    });

    // Assert: company name visible (no timer advances needed - completed is terminal on mount)
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeDefined();
    }, { timeout: 3000 });

    // Assert: no error
    expect(screen.queryByText(/failed/i)).toBeNull();
  });
});
