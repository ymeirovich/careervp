'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../contexts/AuthContext';
import { useUserContext } from '../../hooks/useUserContext';
import { AppShell } from './AppShell';
import { Spinner } from '../ui/Spinner';

export function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const userCtx = useUserContext();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  if (authLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" aria-label="Loading…" />
      </div>
    );
  }

  const creditsUsed = userCtx.usage?.applications.used ?? 0;
  const creditsTotal = creditsUsed + (userCtx.usage?.applications.remaining ?? 0);

  return (
    <AppShell
      user={{
        name: userCtx.user?.name ?? userCtx.user?.email ?? 'User',
        email: userCtx.user?.email ?? '',
        creditsUsed,
        creditsTotal: creditsTotal || 3,
      }}
    >
      {children}
    </AppShell>
  );
}
