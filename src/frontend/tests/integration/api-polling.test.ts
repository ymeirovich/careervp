import { describe, it, expect, beforeEach, afterEach, vi, beforeAll, afterAll } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useModuleStatus } from '../../hooks/useModuleStatus';
import { useGenerateModule } from '../../hooks/useGenerateModule';
import { persistArtifact } from '../../lib/artifactStorage';
import { api } from '../../api/methods';

// Mock lib/auth so tests don't touch real Cognito
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

describe('useModuleStatus — spec-11 polling lifecycle', () => {
  it('polls every 3 seconds until completed', async () => {
    vi.useFakeTimers();

    // Spy directly on the api method to avoid MSW + fake timer conflicts
    const pollSpy = vi
      .spyOn(api, 'pollVPRStatus')
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'completed', result: { uvp: 'Great fit' } });

    const { result } = renderHook(
      () => useModuleStatus('vpr', 'job1', 'task1', true),
      { wrapper: makeWrapper() },
    );

    // Advance through 3 polling intervals (3s each)
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('completed');
    expect(result.current.isPolling).toBe(false);
    expect(pollSpy).toHaveBeenCalledTimes(3);
  });

  it('stops polling on failed status', async () => {
    vi.useFakeTimers();

    const pollSpy = vi
      .spyOn(api, 'pollVPRStatus')
      .mockResolvedValue({ status: 'failed' });

    const { result } = renderHook(
      () => useModuleStatus('vpr', 'job1', 'task-fail', true),
      { wrapper: makeWrapper() },
    );

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('failed');
    expect(result.current.isPolling).toBe(false);

    const callCountAfterFail = pollSpy.mock.calls.length;
    // Advance more time — should not trigger additional polls
    await act(async () => { await vi.advanceTimersByTimeAsync(9000); });
    expect(pollSpy.mock.calls.length).toBe(callCountAfterFail);
  });

  it('does NOT poll when enabled=false', async () => {
    vi.useFakeTimers();

    const pollSpy = vi.spyOn(api, 'pollVPRStatus').mockResolvedValue({ status: 'processing' });

    renderHook(
      () => useModuleStatus('vpr', 'job1', 'task-disabled', false),
      { wrapper: makeWrapper() },
    );

    await act(async () => { await vi.advanceTimersByTimeAsync(9000); });

    expect(pollSpy).not.toHaveBeenCalled();
  });

  it('resumes from localStorage taskId when initialTaskId is null', async () => {
    vi.useFakeTimers();

    persistArtifact('job1', 'vpr', 'stored-task');

    const pollSpy = vi
      .spyOn(api, 'pollVPRStatus')
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'completed', result: {} });

    const { result } = renderHook(
      () => useModuleStatus('vpr', 'job1', null, true),
      { wrapper: makeWrapper() },
    );

    // taskId should be resolved from localStorage immediately
    expect(result.current.taskId).toBe('stored-task');

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(result.current.status).toBe('completed');
    expect(pollSpy).toHaveBeenCalledWith('stored-task');
  });

  it('transient poll error does not stop the polling interval', async () => {
    vi.useFakeTimers();

    const pollSpy = vi
      .spyOn(api, 'pollVPRStatus')
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ status: 'completed', result: {} });

    const { result } = renderHook(
      () => useModuleStatus('vpr', 'job1', 'task-err', true),
      { wrapper: makeWrapper() },
    );

    // First poll: network error — status should stay null, no exception propagated
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(result.current.status).toBeNull();

    // Second poll: returns completed
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(result.current.status).toBe('completed');
    expect(pollSpy).toHaveBeenCalledTimes(2);
  });
});

describe('useGenerateModule — cache-busting', () => {
  it('sends different job_id UUID on each VPR generate call', async () => {
    const capturedBodies: Array<Record<string, unknown>> = [];

    server.use(
      http.post(`${BASE_URL}/vpr/generate`, async ({ request }) => {
        const body = await request.json() as Record<string, unknown>;
        capturedBodies.push(body);
        return HttpResponse.json({ request_id: 'task-new', status: 'processing' });
      }),
    );

    const { result } = renderHook(
      () => useGenerateModule('vpr', 'actual-job-id'),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.generate({ cvId: 'cv-1', gapResponseIds: [] });
    });
    await act(async () => {
      await result.current.generate({ cvId: 'cv-1', gapResponseIds: [] });
    });

    expect(capturedBodies).toHaveLength(2);
    const [first, second] = capturedBodies;

    // Each call must have a unique cache-busting job_id
    expect(first.job_id).not.toBe(second.job_id);

    // Both must be valid UUIDs
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    expect(first.job_id).toMatch(uuidRegex);
    expect(second.job_id).toMatch(uuidRegex);

    // Both must use the actual job ID as application_id
    expect(first.application_id).toBe('actual-job-id');
    expect(second.application_id).toBe('actual-job-id');
  });

  it('sets taskId from response after successful generate', async () => {
    server.use(
      http.post(`${BASE_URL}/vpr/generate`, () =>
        HttpResponse.json({ request_id: 'returned-task', status: 'processing' }),
      ),
    );

    const { result } = renderHook(
      () => useGenerateModule('vpr', 'job-abc'),
      { wrapper: makeWrapper() },
    );

    expect(result.current.taskId).toBeNull();

    await act(async () => {
      await result.current.generate({ cvId: 'cv-1', gapResponseIds: [] });
    });

    expect(result.current.taskId).toBe('returned-task');
  });
});
