/**
 * Regression — the Application Hub's Company Research CTA must actually generate.
 *
 * J5 of the journey (`tests/e2e/journey.spec.ts`) had never once passed against
 * deployed code, and the measured reason was that this card's "Generate" button
 * called `router.push()` instead of starting a generation. The user landed on an
 * empty Company Research page carrying a *second* button ("Research this
 * company") that nothing in the hub flow ever pressed, so the worker Lambda
 * recorded zero invocations while the API Lambda recorded only read-side GETs.
 * Every other generatable module generates directly from the hub; this one
 * silently did not, and the card's own "Retry" path already called
 * handleGenerate — so the intent was never in doubt, only the wiring.
 *
 * Two halves, both required for the hub to advance on its own:
 *   1. the CTA POSTs /company-research/fetch instead of navigating away, and
 *   2. the hub polls the research status so the CTA reaches "View" by itself.
 *
 * Half 2 is re-armed from the fetched status rather than from React state, the
 * same failure mode that left gap analysis stuck on "Generating…" forever.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();

const clientMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useSearchParams: () => ({ get: (_k: string) => null }),
  useParams: () => ({ id: 'job1' }),
}));

vi.mock('../../api/client', () => ({
  apiClient: clientMocks,
  apiFetchOrNull: async (fn: () => Promise<unknown>) => {
    try {
      return await fn();
    } catch {
      return null;
    }
  },
  ApiError: class ApiError extends Error {},
  setAuthContext: vi.fn(),
}));

const JOB_ID = 'job1';

const APPLICATION = {
  application: {
    application_id: JOB_ID,
    job_id: JOB_ID,
    user_id: 'u1',
    state: 'active',
    created_at: '2026-09-22T00:00:00Z',
    updated_at: '2026-09-22T00:00:00Z',
    is_finalized: false,
    trial_credit_consumed: false,
    company_research_error: false,
  },
  job: { job_id: JOB_ID, company_name: 'SysAid', url: 'https://www.sysaid.com' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'pending' as const, artifact_id: null },
    cover_letter: { status: 'pending' as const, artifact_id: null },
    interview_prep: { status: 'pending' as const, artifact_id: null },
    cv_tailored: { status: 'pending' as const, artifact_id: null },
    gap_analysis: { status: 'pending' as const, artifact_id: null },
    company_research: { status: 'pending' as const, artifact_id: null },
  },
};

/** The GET /company-research/{jobId} envelope the handler actually returns. */
const CR_NOT_GENERATED = { status: 'not_generated', company_research: null };
const CR_PROCESSING = { status: 'processing', company_research: null };
const CR_COMPLETED = {
  status: 'completed',
  id: 'comp-res-abc',
  company_name: 'SysAid',
  industry: 'ITSM',
  values: [],
  products: [],
  recent_news: [],
};

/** Successive GET /company-research responses; the last one repeats. */
let crResponses: Array<Record<string, unknown>> = [];

function nextCrResponse(): Record<string, unknown> {
  return crResponses.length > 1 ? (crResponses.shift() as Record<string, unknown>) : crResponses[0];
}

async function renderHub(): Promise<void> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  // Imported lazily so the mocks above are installed first.
  const { default: HubPage } = await import('../../app/applications/[id]/page');
  render(
    <QueryClientProvider client={queryClient}>
      <HubPage />
    </QueryClientProvider>,
  );
}

async function companyResearchCta(): Promise<HTMLElement> {
  return await waitFor(() => {
    const card = screen.getByTestId('module-card-companyResearch');
    const cta = card.querySelector('[data-testid="primary-cta"]');
    if (!cta) throw new Error('company research CTA not rendered yet');
    return cta as HTMLElement;
  });
}

describe('Application Hub — Company Research CTA', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    crResponses = [CR_NOT_GENERATED];

    clientMocks.get.mockImplementation(async (url: string) => {
      if (url.startsWith('/company-research/')) return { data: nextCrResponse() };
      if (url.startsWith('/applications/')) return { data: APPLICATION };
      if (url === '/users/me/cv') return { data: { cvs: [{ cv_id: 'cv1', full_name: 'Base CV' }] } };
      if (url.includes('/gap-questions')) return { data: { questions: [], responses: [] } };
      return { data: {} };
    });

    clientMocks.post.mockResolvedValue({
      data: { request_id: 'comp-res-abc', status: 'processing' },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the card with a "Generate" CTA when no research exists', async () => {
    await renderHub();
    const cta = await companyResearchCta();
    expect(cta.textContent?.trim()).toBe('Generate');
  });

  it('clicking "Generate" POSTs /company-research/fetch instead of navigating away', async () => {
    await renderHub();
    const cta = await companyResearchCta();

    await act(async () => {
      cta.click();
    });

    await waitFor(() => {
      expect(clientMocks.post).toHaveBeenCalledWith(
        '/company-research/fetch',
        expect.objectContaining({ job_id: JOB_ID }),
      );
    });

    // The whole defect: the click used to leave the hub for the artifact page,
    // where a second, never-pressed button was the only way to generate.
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('polls the research status and settles on "View" once it completes', async () => {
    crResponses = [CR_NOT_GENERATED, CR_PROCESSING, CR_PROCESSING, CR_COMPLETED];

    await renderHub();
    const cta = await companyResearchCta();

    await act(async () => {
      cta.click();
    });

    // Two consecutive identical 'processing' responses sit in the queue on
    // purpose: a poll re-armed from React state stops dead on the second one.
    await waitFor(
      async () => {
        const card = screen.getByTestId('module-card-companyResearch');
        const current = card.querySelector('[data-testid="primary-cta"]');
        expect(current?.textContent?.trim()).toBe('View');
      },
      { timeout: 20_000, interval: 250 },
    );
  }, 30_000);

  it('stops polling once the research is completed', async () => {
    crResponses = [CR_COMPLETED];
    await renderHub();

    await waitFor(() => {
      const card = screen.getByTestId('module-card-companyResearch');
      const cta = card.querySelector('[data-testid="primary-cta"]');
      expect(cta?.textContent?.trim()).toBe('View');
    });

    const callsAfterSettle = clientMocks.get.mock.calls.filter((c: unknown[]) =>
      String(c[0]).startsWith('/company-research/'),
    ).length;

    await new Promise((resolve) => setTimeout(resolve, 4000));

    const callsLater = clientMocks.get.mock.calls.filter((c: unknown[]) =>
      String(c[0]).startsWith('/company-research/'),
    ).length;

    expect(callsLater).toBe(callsAfterSettle);
  }, 15_000);
});
