/**
 * Integration tests for Hub Generate UX — RED phase.
 * Tests cancel endpoints, localStorage persistence, state transitions,
 * and UI behaviors across all 4 generatable module types.
 * All tests should FAIL until the cancel/UX implementation is added.
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import { useGenerateModule } from '../../hooks/useGenerateModule';
import { useModuleStatus } from '../../hooks/useModuleStatus';
import { deriveModuleStatus } from '../../adapters/mapApplicationDataToHubState';
import { getArtifact, clearArtifact, persistArtifact } from '../../lib/artifactStorage';
import { api } from '../../api/methods';
import type { ModuleType } from '../../types/enums';

vi.mock('../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
  signOut: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
  resendConfirmationCode: vi.fn(),
  forgotPassword: vi.fn(),
  confirmForgotPassword: vi.fn(),
  getCurrentCognitoUser: vi.fn().mockReturnValue(null),
}));

const BASE_URL = 'http://localhost:3000';

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
  localStorage.clear();
  vi.useRealTimers();
});
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// --- URL maps for each module type ---

const generateUrl: Record<string, string> = {
  vpr: `${BASE_URL}/vpr/generate`,
  coverLetter: `${BASE_URL}/cover-letter/generate`,
  interviewPrep: `${BASE_URL}/interview-prep/generate`,
  tailoredCV: `${BASE_URL}/cv-tailoring/generate`,
};

const cancelUrl = (moduleType: string, taskId: string): string => {
  const paths: Record<string, string> = {
    vpr: `/vpr/${taskId}/cancel`,
    coverLetter: `/cover-letter/${taskId}/cancel`,
    interviewPrep: `/interview-prep/${taskId}/cancel`,
    tailoredCV: `/cv-tailoring/${taskId}/cancel`,
  };
  return `${BASE_URL}${paths[moduleType]}`;
};

const pollSpyMethod: Record<string, keyof typeof api> = {
  vpr: 'pollVPRStatus',
  coverLetter: 'pollCoverLetterStatus',
  interviewPrep: 'pollInterviewPrepStatus',
  tailoredCV: 'pollCVTailored',
};

// --- Parametrized tests across all 4 generatable modules ---

const MODULES: ModuleType[] = ['vpr', 'coverLetter', 'interviewPrep', 'tailoredCV'];

describe.each(MODULES.map((m) => [m]))('useGenerateModule — %s — generate persists to localStorage', (moduleType) => {
  it('after generate() resolves, localStorage has the taskId', async () => {
    const taskId = `task-${moduleType}-persist`;
    const jobId = `job-${moduleType}`;

    server.use(
      http.post(generateUrl[moduleType], () =>
        HttpResponse.json({ request_id: taskId, status: 'processing' }),
      ),
    );

    const { result } = renderHook(
      () => useGenerateModule(moduleType as ModuleType, jobId),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.generate({ cvId: 'cv-1', gapResponseIds: [] });
    });

    // useGenerateModule must call persistArtifact — not yet implemented
    expect(getArtifact(jobId, moduleType)).toBe(taskId);
  });
});

describe.each(MODULES.map((m) => [m]))('useGenerateModule — %s — cancel flow', (moduleType) => {
  it('cancel() POSTs to the correct cancel endpoint and resets state to notStarted', async () => {
    const taskId = `task-${moduleType}-cancel`;
    const jobId = `job-cancel-${moduleType}`;

    persistArtifact(jobId, moduleType, taskId);

    const cancelRequests: string[] = [];
    server.use(
      http.post(cancelUrl(moduleType, taskId), () => {
        cancelRequests.push(taskId);
        return HttpResponse.json({ cancelled: true });
      }),
    );

    const { result } = renderHook(
      () => useGenerateModule(moduleType as ModuleType, jobId),
      { wrapper: makeWrapper() },
    );

    // cancel() does not exist yet — this will TypeError until implemented
    await act(async () => {
      await result.current.cancel(taskId);
    });

    expect(cancelRequests).toHaveLength(1);
    expect(result.current.taskId).toBeNull();
    expect(getArtifact(jobId, moduleType)).toBeNull();
  });

  it('409 from cancel endpoint still clears state without throwing', async () => {
    const taskId = `task-${moduleType}-409`;
    const jobId = `job-cancel-409-${moduleType}`;

    persistArtifact(jobId, moduleType, taskId);

    server.use(
      http.post(cancelUrl(moduleType, taskId), () =>
        HttpResponse.json({ error: 'Cannot cancel terminal task' }, { status: 409 }),
      ),
    );

    const { result } = renderHook(
      () => useGenerateModule(moduleType as ModuleType, jobId),
      { wrapper: makeWrapper() },
    );

    await expect(
      act(async () => { await result.current.cancel(taskId); }),
    ).resolves.not.toThrow();

    expect(result.current.taskId).toBeNull();
    expect(getArtifact(jobId, moduleType)).toBeNull();
  });
});

describe.each(MODULES.map((m) => [m]))('useModuleStatus — %s — cancelled stops polling', (moduleType) => {
  it('stops polling and isPolling=false when status becomes "cancelled"', async () => {
    vi.useFakeTimers();

    const pollMethod = pollSpyMethod[moduleType] as keyof typeof api;
    const pollSpy = vi
      .spyOn(api, pollMethod as 'pollVPRStatus')
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'cancelled' as never });

    const { result } = renderHook(
      () => useModuleStatus(moduleType as ModuleType, 'job1', `task-${moduleType}`, true),
      { wrapper: makeWrapper() },
    );

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('cancelled');
    expect(result.current.isPolling).toBe(false);

    const callCount = pollSpy.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(9000); });
    // No additional polls after 'cancelled'
    expect(pollSpy.mock.calls.length).toBe(callCount);
  });
});

// --- deriveModuleStatus — 'cancelled' → 'notStarted' ---

describe('deriveModuleStatus — cancelled status', () => {
  it('maps "cancelled" poll status to "notStarted" (not "ready")', () => {
    // 'cancelled' is not in ArtifactStatus type yet — cast to test the intent
    const result = deriveModuleStatus('vpr', 'cancelled' as never, false, false);
    expect(result).toBe('notStarted');
  });

  it.each(MODULES)('maps "cancelled" to "notStarted" for %s', (moduleType) => {
    const result = deriveModuleStatus(moduleType as ModuleType, 'cancelled' as never, false, false);
    expect(result).toBe('notStarted');
  });
});

// --- Poll 'failed' → error state resets to Generate ---

describe.each(MODULES.map((m) => [m]))('useModuleStatus — %s — failed poll clears polling', (moduleType) => {
  it('isPolling becomes false and status is "failed" after poll returns failed', async () => {
    vi.useFakeTimers();

    const pollMethod = pollSpyMethod[moduleType] as keyof typeof api;
    vi.spyOn(api, pollMethod as 'pollVPRStatus').mockResolvedValue({ status: 'failed' });

    const { result } = renderHook(
      () => useModuleStatus(moduleType as ModuleType, 'job1', `task-fail-${moduleType}`, true),
      { wrapper: makeWrapper() },
    );

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('failed');
    expect(result.current.isPolling).toBe(false);
  });
});

// --- Poll 'completed' → Regenerate + View available ---

describe.each(MODULES.map((m) => [m]))('useModuleStatus — %s — completed sets status', (moduleType) => {
  it('status becomes "completed" and isPolling=false after poll returns completed', async () => {
    vi.useFakeTimers();

    const pollMethod = pollSpyMethod[moduleType] as keyof typeof api;
    vi.spyOn(api, pollMethod as 'pollVPRStatus').mockResolvedValue({
      id: 'some-result',
      status: 'completed',
    });

    const { result } = renderHook(
      () => useModuleStatus(moduleType as ModuleType, 'job1', `task-done-${moduleType}`, true),
      { wrapper: makeWrapper() },
    );

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('completed');
    expect(result.current.isPolling).toBe(false);
  });
});
