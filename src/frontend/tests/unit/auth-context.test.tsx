import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { useAuth, AuthProvider } from '../../contexts/AuthContext';
import { CognitoUser } from 'amazon-cognito-identity-js';

// Stable mock session factories — recreated per test via beforeEach
let mockGetJwtToken = vi.fn().mockReturnValue('test-token');
let mockIsValid = vi.fn().mockReturnValue(true);

function makeMockSession() {
  return {
    isValid: mockIsValid,
    getIdToken: vi.fn().mockReturnValue({ getJwtToken: mockGetJwtToken }),
  };
}

let mockAuthenticateUser = vi.fn();
let mockGetSession = vi.fn();
let mockSignOut = vi.fn();

vi.mock('amazon-cognito-identity-js', () => {
  return {
    CognitoUserPool: vi.fn().mockImplementation(function () {
      return {
        getCurrentUser: vi.fn(() => ({
          getSession: mockGetSession,
          signOut: mockSignOut,
          authenticateUser: mockAuthenticateUser,
          changePassword: vi.fn((_o: string, _n: string, cb: (e: Error | null, r: string) => void) =>
            cb(null, 'SUCCESS'),
          ),
        })),
        signUp: vi.fn(
          (_e: string, _p: string, _a: unknown[], _v: unknown, cb: (e: Error | null) => void) =>
            cb(null),
        ),
      };
    }),
    CognitoUser: vi.fn().mockImplementation(function () {
      return {
        getSession: mockGetSession,
        signOut: mockSignOut,
        authenticateUser: mockAuthenticateUser,
        changePassword: vi.fn((_o: string, _n: string, cb: (e: Error | null, r: string) => void) =>
          cb(null, 'SUCCESS'),
        ),
        resendConfirmationCode: vi.fn((cb: (e: Error | null) => void) => cb(null)),
      };
    }),
    AuthenticationDetails: vi.fn().mockImplementation(function () { return {}; }),
    CognitoUserAttribute: vi.fn().mockImplementation(function () { return {}; }),
  };
});

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Suppress fire-and-forget fetch in signOut
vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(AuthProvider, null, children);

beforeEach(() => {
  // Reset cookie
  document.cookie = 'cognito_id_token=; path=/; max-age=0';

  mockGetJwtToken = vi.fn().mockReturnValue('test-token');
  mockIsValid = vi.fn().mockReturnValue(true);

  const session = makeMockSession();
  mockGetSession = vi.fn((cb: (e: Error | null, s: typeof session) => void) => cb(null, session));
  mockAuthenticateUser = vi.fn(
    (_details: unknown, handlers: { onSuccess: (s: typeof session) => void; onFailure: (e: Error) => void }) =>
      handlers.onSuccess(session),
  );
  mockSignOut = vi.fn();
});

describe('AuthContext — signIn', () => {
  it('sets user, idToken, and writes cookie on success', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Wait for mount session restoration
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    // signIn with test-token (set by beforeEach mock)
    await act(async () => {
      await result.current.signIn('user@test.com', 'password');
    });

    expect(result.current.idToken).toBe('test-token');
    expect(result.current.isAuthenticated).toBe(true);
    expect(document.cookie).toContain('cognito_id_token=test-token');
  });

  it('throws NotAuthorizedException and leaves context state unchanged', async () => {
    vi.mocked(CognitoUser).mockImplementationOnce(function () {
      return {
        authenticateUser: vi.fn(
          (_: unknown, handlers: { onSuccess: () => void; onFailure: (e: { code: string; message: string }) => void }) =>
            handlers.onFailure({ code: 'NotAuthorizedException', message: 'Incorrect username or password.' }),
        ),
        getSession: mockGetSession,
        signOut: mockSignOut,
      } as unknown as CognitoUser;
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    // Mount: session restoration runs — mock still returns valid for getCurrentUser
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    // Now signIn fails
    await expect(
      act(async () => result.current.signIn('user@test.com', 'bad')),
    ).rejects.toBeTruthy();

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.idToken).toBeNull();
  });
});

describe('AuthContext — signOut', () => {
  it('clears user, idToken, and removes cookie', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Let session restore (authenticated via mock)
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });
    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => { await result.current.signOut(); });

    expect(result.current.user).toBeNull();
    expect(result.current.idToken).toBeNull();
    expect(document.cookie).not.toContain('cognito_id_token=test-token');
  });
});

describe('AuthContext — session restoration on mount', () => {
  it('restores session when valid Cognito session exists', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.idToken).toBe('test-token');
  });

  it('stays unauthenticated when no Cognito session', async () => {
    // Override getSession to return null (no active session)
    mockGetSession = vi.fn((cb: (e: Error | null, s: null) => void) => cb(null, null));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });
});
