'use client';

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { flushSync } from 'react-dom';
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js';

interface AuthContextValue {
  user: CognitoUser | null;
  idToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  confirmForgotPassword: (email: string, code: string, newPassword: string) => Promise<void>;
  refreshSession: () => Promise<string>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function setTokenCookie(token: string) {
  if (typeof document !== 'undefined') {
    document.cookie = `cognito_id_token=${token}; path=/; SameSite=Strict`;
  }
}

function clearTokenCookie() {
  if (typeof document !== 'undefined') {
    document.cookie = 'cognito_id_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const poolRef = useRef<CognitoUserPool | null>(null);

  function getPool(): CognitoUserPool {
    if (!poolRef.current) {
      poolRef.current = new CognitoUserPool({
        UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? 'us-east-1_WiHMRqLpe',
        ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '7blipbarsisbctqh6hlsj46sqa',
      });
    }
    return poolRef.current;
  }

  const [user, setUser] = useState<CognitoUser | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const pool = getPool();
    const currentUser = pool.getCurrentUser();
    if (!currentUser) {
      setIsLoading(false);
      return;
    }
    currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session?.isValid()) {
        setIsLoading(false);
        return;
      }
      const token = session.getIdToken().getJwtToken();
      setUser(currentUser);
      setIdToken(token);
      setTokenCookie(token);
      setIsLoading(false);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback((email: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const pool = getPool();
      const authDetails = new AuthenticationDetails({ Username: email, Password: password });
      const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
      cognitoUser.authenticateUser(authDetails, {
        onSuccess(session: CognitoUserSession) {
          const token = session.getIdToken().getJwtToken();
          flushSync(() => {
            setUser(cognitoUser);
            setIdToken(token);
          });
          setTokenCookie(token);
          resolve();
        },
        onFailure(err: Error) {
          flushSync(() => {
            setUser(null);
            setIdToken(null);
          });
          clearTokenCookie();
          reject(err);
        },
      });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signOut = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      const pool = getPool();
      const currentUser = user ?? pool.getCurrentUser();
      if (currentUser) {
        currentUser.signOut();
      }
      setUser(null);
      setIdToken(null);
      clearTokenCookie();
      resolve();
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const signUp = useCallback((email: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const pool = getPool();
      const attributes = [new CognitoUserAttribute({ Name: 'email', Value: email })];
      pool.signUp(email, password, attributes, [], (err) => {
        if (err) { reject(err); return; }
        resolve();
      });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirmSignUp = useCallback((email: string, code: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const pool = getPool();
      const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
      cognitoUser.confirmRegistration(code, true, (err) => {
        if (err) { reject(err); return; }
        resolve();
      });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const forgotPassword = useCallback((email: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const pool = getPool();
      const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
      cognitoUser.forgotPassword({
        onSuccess: () => resolve(),
        onFailure: (err) => reject(err),
      });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirmForgotPassword = useCallback(
    (email: string, code: string, newPassword: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        const pool = getPool();
        const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
        cognitoUser.confirmPassword(code, newPassword, {
          onSuccess: () => resolve(),
          onFailure: (err) => reject(err),
        });
      });
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  []);

  const refreshSession = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const pool = getPool();
      const currentUser = user ?? pool.getCurrentUser();
      if (!currentUser) { reject(new Error('No current user')); return; }
      currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session?.isValid()) { reject(err ?? new Error('Invalid session')); return; }
        const token = session.getIdToken().getJwtToken();
        setIdToken(token);
        setTokenCookie(token);
        resolve(token);
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
        forgotPassword,
        confirmForgotPassword,
        refreshSession,
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
