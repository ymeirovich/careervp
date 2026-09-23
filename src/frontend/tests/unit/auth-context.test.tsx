import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { useAuth, AuthProvider } from '../../contexts/AuthContext';
import { beginPkceSignIn } from '../../lib/pkce';
import * as apiClientModule from '../../api/client';

vi.mock('../../lib/pkce', () => ({
  beginPkceSignIn: vi.fn(),
  hostedUiLogoutUrl: vi.fn().mockReturnValue(null),
}));

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
let mockAssociateSoftwareToken = vi.fn();
let mockVerifySoftwareToken = vi.fn();
let mockSetUserMfaPreference = vi.fn();

vi.mock('amazon-cognito-identity-js', () => {
  return {
    CognitoUserPool: vi.fn().mockImplementation(function () {
      return {
        getCurrentUser: vi.fn(() => ({
          getSession: mockGetSession,
          signOut: mockSignOut,
          authenticateUser: mockAuthenticateUser,
          associateSoftwareToken: mockAssociateSoftwareToken,
          verifySoftwareToken: mockVerifySoftwareToken,
          setUserMfaPreference: mockSetUserMfaPreference,
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
        associateSoftwareToken: mockAssociateSoftwareToken,
        verifySoftwareToken: mockVerifySoftwareToken,
        setUserMfaPreference: mockSetUserMfaPreference,
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
  mockAssociateSoftwareToken = vi.fn((callbacks: { associateSecretCode: (secret: string) => void }) =>
    callbacks.associateSecretCode('TOTP-SECRET'),
  );
  mockVerifySoftwareToken = vi.fn(
    (_code: string, _deviceName: string, callbacks: { onSuccess: () => void }) => callbacks.onSuccess(),
  );
  mockSetUserMfaPreference = vi.fn(
    (_sms: unknown, _totp: unknown, callback: (error: Error | null) => void) => callback(null),
  );
  vi.mocked(beginPkceSignIn).mockResolvedValue();
});

describe('AuthContext — signIn', () => {
  it('starts authorization-code PKCE sign-in', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Wait for mount session restoration
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    await act(async () => {
      await result.current.signIn('user@test.com');
    });

    expect(beginPkceSignIn).toHaveBeenCalledWith('user@test.com');
  });

  it('surfaces a failure to start the PKCE redirect', async () => {
    vi.mocked(beginPkceSignIn).mockRejectedValueOnce(new Error('redirect failed'));

    const { result } = renderHook(() => useAuth(), { wrapper });

    // Mount: session restoration runs — mock still returns valid for getCurrentUser
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    // Now signIn fails
    await expect(
      act(async () => result.current.signIn('user@test.com')),
    ).rejects.toThrow('redirect failed');
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

describe('AuthContext — axios interceptor wiring', () => {
  it('registers the real refreshSession/signOut with the api client on mount', async () => {
    // Regression test for a bug where the interceptor's authContext stub was
    // never replaced: production 401s silently failed to refresh or sign out
    // because nothing called setAuthContext, even though the real
    // implementations existed here all along.
    const spy = vi.spyOn(apiClientModule, 'setAuthContext');

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });

    expect(spy).toHaveBeenCalled();
    const registered = spy.mock.calls.at(-1)?.[0];
    expect(registered?.refreshSession).toBe(result.current.refreshSession);
    expect(registered?.signOut).toBe(result.current.signOut);
  });
});

describe('AuthContext — TOTP enrollment grace', () => {
  it('associates a software token for an authenticated user', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });

    await expect(result.current.beginTotpEnrollment()).resolves.toBe('TOTP-SECRET');
    expect(mockAssociateSoftwareToken).toHaveBeenCalledOnce();
  });

  it('verifies the code and enables TOTP as the preferred factor', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });

    await result.current.confirmTotpEnrollment('123456');

    expect(mockVerifySoftwareToken).toHaveBeenCalledWith('123456', 'CareerVP authenticator', expect.any(Object));
    expect(mockSetUserMfaPreference).toHaveBeenCalledWith(
      null,
      { Enabled: true, PreferredMfa: true },
      expect.any(Function),
    );
  });
});
