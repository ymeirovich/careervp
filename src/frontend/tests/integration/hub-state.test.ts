import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { DashboardContext } from '../../contexts/DashboardContext';
import type { DashboardContextValue } from '../../contexts/DashboardContext';

const BASE_URL = 'http://localhost:3000';
const JOB_ID = 'job-hub-int-001';

// ── next/navigation mocks ──────────────────────────────────────────────────
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useParams: () => ({ id: JOB_ID }),
}));

// ── MSW server ─────────────────────────────────────────────────────────────
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
  vi.clearAllMocks();
});
afterAll(() => server.close());

// ── Fixtures ───────────────────────────────────────────────────────────────
const defaultApplication = {
  application_id: 'app-001',
  job_id: JOB_ID,
  user_id: 'user-001',
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:00:00Z',
  is_finalized: false,
  artifacts: {
    vpr: { artifact_id: null, status: 'pending' },
    cover_letter: { artifact_id: null, status: 'pending' },
    interview_prep: { artifact_id: null, status: 'pending' },
    cv_tailored: { artifact_id: null, status: 'pending' },
    gap_analysis: { artifact_id: null, status: 'pending' },
  },
};

const defaultCV = {
  cv_id: 'cv-001',
  created_at: '2024-01-01T09:00:00Z',
  updated_at: '2024-01-01T09:00:00Z',
  version: 1,
};

const defaultGapAnalysis = {
  job_id: JOB_ID,
  questions: [],
};

const defaultDashboard: DashboardContextValue = {
  userName: 'Test User',
  usage: null,
  subscription: null,
  hasActiveAccess: true,
  applicationsRemaining: null,
};

// ── Render helper ──────────────────────────────────────────────────────────
function makeWrapper(dashCtx: DashboardContextValue = defaultDashboard) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(DashboardContext.Provider, { value: dashCtx }, children),
    );
  };
}

async function getHubPage() {
  const mod = await import('../../app/applications/[id]/page');
  return mod.default;
}

async function getDashboardPage() {
  const mod = await import('../../app/dashboard/page');
  return mod.default;
}

// ── Tests ───────────────────────────────────────────────────────────────────
describe('Hub page — renders 7 ModuleCards', () => {
  it('renders 7 ModuleCards when hub data loads', async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
    );

    const HubPage = await getHubPage();
    const Wrapper = makeWrapper();

    render(React.createElement(HubPage), { wrapper: Wrapper });

    await waitFor(
      () => {
        const cards = screen.queryAllByTestId(/^module-card-/);
        expect(cards.length).toBe(7);
      },
      { timeout: 5000 },
    );
  });
});

describe('Hub page — hub blocked banner', () => {
  it('hub-blocked-banner shown when cv is null (no CV uploaded)', async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => new HttpResponse(null, { status: 404 })),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
    );

    const HubPage = await getHubPage();
    const Wrapper = makeWrapper();

    render(React.createElement(HubPage), { wrapper: Wrapper });

    await waitFor(
      () => {
        expect(screen.getByTestId('hub-blocked-banner')).toBeDefined();
      },
      { timeout: 5000 },
    );
  });
});

describe('Dashboard page — jobs table', () => {
  it('renders job rows from API response', async () => {
    server.use(
      http.get(`${BASE_URL}/jobs`, () =>
        HttpResponse.json({
          jobs: [
            {
              id: 'j1',
              job_id: 'j1',
              title: 'Engineer',
              company_name: 'Acme',
              status: 'active',
              created_at: new Date().toISOString(),
            },
          ],
        }),
      ),
    );

    const DashPage = await getDashboardPage();
    const Wrapper = makeWrapper();

    render(React.createElement(DashPage), { wrapper: Wrapper });

    await waitFor(
      () => {
        expect(screen.getByText('Engineer')).toBeDefined();
      },
      { timeout: 5000 },
    );
  });
});
