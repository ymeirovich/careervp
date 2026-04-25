'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../api/methods';
import type { User, Usage, SubscriptionResponse } from '../lib/types';

export function useUserContext(): {
  user: User | null;
  usage: Usage | null;
  subscription: SubscriptionResponse | null;
  isLoading: boolean;
  hasActiveAccess: boolean;
  applicationsRemaining: number | null;
} {
  const userQuery = useQuery<User>({
    queryKey: ['user', 'me'],
    queryFn: () => api.getMe(),
  });

  const usageQuery = useQuery<Usage>({
    queryKey: ['user', 'usage'],
    queryFn: () => api.getUsage(),
  });

  const subscriptionQuery = useQuery<SubscriptionResponse>({
    queryKey: ['user', 'subscription'],
    queryFn: () => api.getSubscription(),
  });

  const usage = usageQuery.data ?? null;
  const subscription = subscriptionQuery.data ?? null;

  const hasActiveAccess =
    usage?.trial?.active === true || subscription?.has_active_subscription === true;

  const applicationsRemaining = usage?.applications?.remaining ?? null;

  const isLoading =
    userQuery.isLoading || usageQuery.isLoading || subscriptionQuery.isLoading;

  return {
    user: userQuery.data ?? null,
    usage,
    subscription,
    isLoading,
    hasActiveAccess,
    applicationsRemaining,
  };
}
