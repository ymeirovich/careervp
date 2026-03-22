"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
  getCurrentToken,
  getCurrentCognitoUser,
} from "@/lib/auth";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const restore = async () => {
      const cognitoUser = getCurrentCognitoUser();
      if (!cognitoUser) {
        setLoading(false);
        return;
      }
      const t = await getCurrentToken();
      if (t) {
        setToken(t);
        try {
          const me = await api.getMe();
          setUser(me);
        } catch {
          // Session exists but profile fetch failed — treat as logged out
          setToken(null);
        }
      }
      setLoading(false);
    };
    restore();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const t = await cognitoSignIn(email, password);
    setToken(t);
    const me = await api.getMe();
    setUser(me);
  }, []);

  const signOut = useCallback(() => {
    cognitoSignOut();
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
