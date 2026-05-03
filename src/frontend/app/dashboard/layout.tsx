'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../contexts/AuthContext';
import { useUserContext } from '../../hooks/useUserContext';
import { DashboardContext } from '../../contexts/DashboardContext';
import { AppShell } from '../../components/layout/AppShell';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { Spinner } from '../../components/ui/Spinner';

function DashboardError() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-text-muted">
        We&apos;re having trouble loading the dashboard. Please refresh.
      </p>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" aria-label="Loading…" />
      </div>
    );
  }

  const creditsUsed = userCtx.usage?.applications.used ?? 0;
  const creditsTotal = creditsUsed + (userCtx.usage?.applications.remaining ?? 0);
  const isUnlimited = userCtx.subscription?.has_active_subscription ?? false;

  return (
    <DashboardContext.Provider
      value={{
        userName: userCtx.user?.name ?? userCtx.user?.email ?? '',
        usage: userCtx.usage,
        subscription: userCtx.subscription,
        hasActiveAccess: userCtx.hasActiveAccess,
        applicationsRemaining: userCtx.applicationsRemaining,
      }}
    >
      <AppShell
        user={{
          name: userCtx.user?.name ?? userCtx.user?.email ?? 'User',
          email: userCtx.user?.email ?? '',
          creditsUsed,
          creditsTotal: creditsTotal || 3,
          isUnlimited,
        }}
      >
        <ErrorBoundary cloudwatchKey="dashboard" fallback={<DashboardError />}>
          {children}
        </ErrorBoundary>
      </AppShell>
    </DashboardContext.Provider>
  );
}
