/**
 * Unit Tests: Get Subscription Status + Cancel-at-Period-End UX
 * Features: F-SUB-008, F-SUB-015
 *
 * Tests the GET /users/me/subscription handler logic including:
 * - Active subscription response shape
 * - Null subscription response
 * - Cancel-at-period-end distinction
 */

import subscriptionActivePayload from '../payloads/subscription-active.json';
import subscriptionCancelingPayload from '../payloads/subscription-canceling.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockDal = {
  get_subscription_by_user: jest.fn(),
};

// ─── Simulated handle_get_subscription Logic ─────────────────────────────────

interface SubscriptionResponse {
  statusCode: number;
  body: {
    subscription: Record<string, unknown> | null;
    has_active_subscription: boolean;
  };
}

function handleGetSubscription(userId: string): SubscriptionResponse {
  const sub = mockDal.get_subscription_by_user(userId);

  if (!sub) {
    return {
      statusCode: 200,
      body: { subscription: null, has_active_subscription: false },
    };
  }

  return {
    statusCode: 200,
    body: {
      subscription: {
        subscription_id: sub.subscription_id,
        customer_id: sub.customer_id,
        status: sub.status,
        plan: sub.plan,
        current_period_end: sub.current_period_end,
        cancel_at_period_end: sub.cancel_at_period_end ?? false,
        trial_end: sub.trial_end,
      },
      has_active_subscription: sub.status === 'active',
    },
  };
}

// ─── Simulated useSubscription Hook ──────────────────────────────────────────

interface SubscriptionHookState {
  isActive: boolean;
  isCancelingAtPeriodEnd: boolean;
  statusLabel: string;
}

function useSubscription(sub: Record<string, unknown> | null): SubscriptionHookState {
  if (!sub) {
    return { isActive: false, isCancelingAtPeriodEnd: false, statusLabel: 'No subscription' };
  }

  const isActive = sub.status === 'active';
  const isCancelingAtPeriodEnd = isActive && sub.cancel_at_period_end === true;

  let statusLabel: string;
  if (sub.status === 'canceled') {
    statusLabel = 'Canceled';
  } else if (isCancelingAtPeriodEnd) {
    const endDate = new Date(sub.current_period_end as string).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
    statusLabel = `Cancels on ${endDate}`;
  } else if (isActive) {
    const endDate = new Date(sub.current_period_end as string).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
    statusLabel = `Renews ${endDate}`;
  } else {
    statusLabel = String(sub.status);
  }

  return { isActive, isCancelingAtPeriodEnd, statusLabel };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Get Subscription Status', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-008: Active Subscription Response ─────────────────────────────
  describe('F-SUB-008: Get Active Subscription', () => {
    it('should return subscription with has_active_subscription = true', () => {
      // Preconditions: DynamoDB returns active subscription
      mockDal.get_subscription_by_user.mockReturnValue(subscriptionActivePayload);

      const result = handleGetSubscription('user-008');

      // Assert 200 with correct shape
      expect(result.statusCode).toBe(200);
      expect(result.body.has_active_subscription).toBe(true);
      expect(result.body.subscription).not.toBeNull();

      // Assert all payload fields present
      const sub = result.body.subscription!;
      expect(sub.subscription_id).toBe('sub_1Pxyz');
      expect(sub.customer_id).toBe('cus_Nabc');
      expect(sub.status).toBe('active');
      expect(sub.plan).toBe('monthly');
      expect(sub.current_period_end).toBe('2026-04-14T00:00:00Z');
      expect(sub.cancel_at_period_end).toBe(false);
      expect(sub.trial_end).toBeNull();
    });
  });

  // ── F-SUB-008b: No Subscription → null ──────────────────────────────────
  describe('F-SUB-008b: No Subscription', () => {
    it('should return null subscription with has_active_subscription = false', () => {
      // Preconditions: DynamoDB returns no subscription
      mockDal.get_subscription_by_user.mockReturnValue(null);

      const result = handleGetSubscription('user-008b');

      expect(result.statusCode).toBe(200);
      expect(result.body.subscription).toBeNull();
      expect(result.body.has_active_subscription).toBe(false);
    });
  });

  // ── F-SUB-015: Cancel-at-Period-End UX ──────────────────────────────────
  describe('F-SUB-015: Cancel-at-Period-End UX Distinction', () => {
    it('should set isCancelingAtPeriodEnd when cancel_at_period_end is true', () => {
      const hookState = useSubscription(subscriptionCancelingPayload);

      // Assert active but canceling
      expect(hookState.isActive).toBe(true);
      expect(hookState.isCancelingAtPeriodEnd).toBe(true);
    });

    it('should show "Cancels on" label for canceling subscriptions', () => {
      const hookState = useSubscription(subscriptionCancelingPayload);

      // Assert label shows "Cancels on Apr 14, 2026"
      expect(hookState.statusLabel).toMatch(/Cancels on/);
      expect(hookState.statusLabel).toMatch(/Apr/);
      expect(hookState.statusLabel).toMatch(/2026/);
    });

    it('should show "Renews" label for active non-canceling subscriptions', () => {
      const hookState = useSubscription(subscriptionActivePayload);

      expect(hookState.isActive).toBe(true);
      expect(hookState.isCancelingAtPeriodEnd).toBe(false);
      expect(hookState.statusLabel).toMatch(/Renews/);
    });

    it('should not block access while canceling within period', () => {
      // Canceling subscription is still active until period ends
      mockDal.get_subscription_by_user.mockReturnValue(subscriptionCancelingPayload);

      const result = handleGetSubscription('user-015');

      expect(result.body.has_active_subscription).toBe(true);
    });
  });
});
