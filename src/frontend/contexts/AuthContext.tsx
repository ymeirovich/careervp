'use client';

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CognitoUserPool, CognitoUser, type CognitoUserSession } from 'amazon-cognito-identity-js';
import * as auth from '../lib/auth';

interface AuthContextValue {
  user: CognitoUser | null;
  idToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  resendConfirmationCode: (email: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  confirmForgotPassword: (email: string, code: string, newPassword: string) => Promise<void>;
  refreshSession: () => Promise<string>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  beginTotpEnrollment: () => Promise<string>;
  confirmTotpEnrollment: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function setTokenCookie(token: string) {
  if (typeof document !== 'undefined') {
    document.cookie = `cognito_id_token=${token}; path=/; max-age=3600; SameSite=Lax`;
  }
}

function clearTokenCookie() {
  if (typeof document !== 'undefined') {
    document.cookie = 'cognito_id_token=; path=/; max-age=0';
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const poolRef = useRef<CognitoUserPool | null>(null);

  function getPool(): CognitoUserPool {
    if (!poolRef.current) {
      poolRef.current = new CognitoUserPool({
        UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? 'us-east-1_WiHMRqLpe',
        ClientId:
          process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ??
          process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ??
          '7blipbarsisbctqh6hlsj46sqa',
      });
    }
    return poolRef.current;
  }

  const [user, setUser] = useState<CognitoUser | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Session restoration on mount
  useEffect(() => {
    auth.getCurrentToken().then((token) => {
      if (token) {
        const currentUser = getPool().getCurrentUser();
        setUser(currentUser);
        setIdToken(token);
        setTokenCookie(token);
      } else {
        clearTokenCookie();
      }
      setIsLoading(false);
    }).catch(() => {
      clearTokenCookie();
      setIsLoading(false);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback((email: string): Promise<void> => auth.beginPkceSignIn(email), []);

  const signOut = useCallback((): Promise<void> => {
    // Fire-and-forget backend logout — do not block UI on failure
    if (idToken) {
      fetch('/api/proxy/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${idToken}` },
      }).catch(() => undefined);
    }
    const logoutUrl = auth.signOut();
    clearTokenCookie();
    setUser(null);
    setIdToken(null);
    if (logoutUrl) {
      window.location.assign(logoutUrl);
    } else {
      router.push('/login');
    }
    return Promise.resolve();
  }, [idToken, router]);

  const signUp = useCallback(
    (email: string, password: string, name: string): Promise<void> =>
      auth.signUp(email, password, name),
    [],
  );

  const confirmSignUp = useCallback(
    (email: string, code: string): Promise<void> => auth.confirmSignUp(email, code),
    [],
  );

  const resendConfirmationCode = useCallback(
    (email: string): Promise<void> => auth.resendConfirmationCode(email),
    [],
  );

  const forgotPassword = useCallback(
    (email: string): Promise<void> => auth.forgotPassword(email),
    [],
  );

  const confirmForgotPassword = useCallback(
    (email: string, code: string, newPassword: string): Promise<void> =>
      auth.confirmForgotPassword(email, code, newPassword),
    [],
  );

  const refreshSession = useCallback((): Promise<string> => {
    return auth.getCurrentToken().then((token) => {
      if (!token) {
        return signOut().then(() => { throw new Error('Session expired'); });
      }
      setIdToken(token);
      setTokenCookie(token);
      return token;
    });
  }, [signOut]);

  const changePassword = useCallback(
    (oldPassword: string, newPassword: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        const pool = getPool();
        const currentUser = user ?? pool.getCurrentUser();
        if (!currentUser) {
          reject(new Error('No authenticated user'));
          return;
        }
        currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
          if (err || !session?.isValid()) {
            reject(err ?? new Error('Invalid session'));
            return;
          }
          currentUser.changePassword(oldPassword, newPassword, (changeErr) => {
            if (changeErr) { reject(changeErr); return; }
            resolve();
          });
        });
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user],
  );

  const beginTotpEnrollment = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const currentUser = user ?? getPool().getCurrentUser();
      if (!currentUser) {
        reject(new Error('No authenticated user'));
        return;
      }
      currentUser.associateSoftwareToken({
        associateSecretCode: resolve,
        onFailure: reject,
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const confirmTotpEnrollment = useCallback((code: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const currentUser = user ?? getPool().getCurrentUser();
      if (!currentUser) {
        reject(new Error('No authenticated user'));
        return;
      }
      currentUser.verifySoftwareToken(code, 'CareerVP authenticator', {
        onFailure: reject,
        onSuccess: () => {
          currentUser.setUserMfaPreference(
            null,
            { Enabled: true, PreferredMfa: true },
            (preferenceError) => {
              if (preferenceError) {
                reject(preferenceError);
                return;
              }
              resolve();
            },
          );
        },
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        user,
        idToken,
        isLoading,
        isAuthenticated: !!user && !!idToken,
        signIn,
        signOut,
        signUp,
        confirmSignUp,
        resendConfirmationCode,
        forgotPassword,
        confirmForgotPassword,
        refreshSession,
        changePassword,
        beginTotpEnrollment,
        confirmTotpEnrollment,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
