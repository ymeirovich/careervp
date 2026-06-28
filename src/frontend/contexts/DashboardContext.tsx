'use client';

import { createContext, useContext } from 'react';
import type { Usage, SubscriptionResponse } from '../lib/types';

export interface DashboardContextValue {
  userName: string;
  usage: Usage | null;
  subscription: SubscriptionResponse | null;
  hasActiveAccess: boolean;
  applicationsRemaining: number | null;
  isLoading?: boolean;
}

export const DashboardContext = createContext<DashboardContextValue | null>(null);

export function useDashboard(): DashboardContextValue {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within DashboardContext.Provider');
  return ctx;
}
