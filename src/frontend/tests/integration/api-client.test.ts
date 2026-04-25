import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const { mockGetCurrentToken } = vi.hoisted(() => ({
  mockGetCurrentToken: vi.fn<() => Promise<string | null>>(),
}));

vi.mock('../../lib/auth', () => ({
  getCurrentToken: mockGetCurrentToken,
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
  vi.clearAllMocks();
});
afterAll(() => server.close());

import { apiClient, setAuthContext, ApiError } from '../../api/client';

describe('Authorization header injection', () => {
  it('sets Authorization header from token on every request', async () => {
    mockGetCurrentToken.mockResolvedValue('test-jwt');

    let capturedAuth: string | undefined;
    server.use(
      http.get(`${BASE_URL}/users/me`, ({ request }) => {
        capturedAuth = request.headers.get('Authorization') ?? undefined;
        return HttpResponse.json({ user_id: 'u1' });
      }),
    );

    await apiClient.get('/users/me');
    expect(capturedAuth).toBe('Bearer test-jwt');
  });

  it('sends no Authorization header when token is null', async () => {
    mockGetCurrentToken.mockResolvedValue(null);

    let capturedAuth: string | null = 'PRESENT';
    server.use(
      http.get(`${BASE_URL}/users/me`, ({ request }) => {
        capturedAuth = request.headers.get('Authorization');
        return HttpResponse.json({ user_id: 'u1' });
      }),
    );

    await apiClient.get('/users/me');
    expect(capturedAuth).toBeNull();
  });
});

describe('401 retry-once pattern', () => {
  it('retries once with refreshed token on 401', async () => {
    mockGetCurrentToken.mockResolvedValue('original-jwt');

    const mockRefreshSession = vi.fn().mockResolvedValue('new-jwt');
    const mockSignOut = vi.fn();
    setAuthContext({ refreshSession: mockRefreshSession, signOut: mockSignOut });

    let callCount = 0;
    let lastAuth: string | undefined;
    server.use(
      http.get(`${BASE_URL}/users/me`, ({ request }) => {
        callCount++;
        lastAuth = request.headers.get('Authorization') ?? undefined;
        if (callCount === 1) {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }
        return HttpResponse.json({ user_id: 'u1' });
      }),
    );

    const result = await apiClient.get('/users/me');
    expect(mockRefreshSession).toHaveBeenCalledOnce();
    expect(lastAuth).toBe('Bearer new-jwt');
    expect(result.data).toEqual({ user_id: 'u1' });
  });

  it('does not retry a second time on consecutive 401s — calls signOut and rejects', async () => {
    mockGetCurrentToken.mockResolvedValue('original-jwt');

    const mockRefreshSession = vi.fn().mockResolvedValue('new-jwt');
    const mockSignOut = vi.fn();
    setAuthContext({ refreshSession: mockRefreshSession, signOut: mockSignOut });

    server.use(
      http.get(`${BASE_URL}/users/me`, () =>
        HttpResponse.json({ error: 'Unauthorized' }, { status: 401 }),
      ),
    );

    let caught: unknown;
    try {
      await apiClient.get('/users/me');
    } catch (err) {
      caught = err;
    }

    expect(mockRefreshSession).toHaveBeenCalledOnce();
    expect(mockSignOut).toHaveBeenCalled();
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(401);
  });
});
