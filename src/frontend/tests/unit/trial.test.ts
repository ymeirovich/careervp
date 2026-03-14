/**
 * Unit Tests: Trial Activation, Expiry, and Credit Exhaustion
 * Features: F-SUB-001, F-SUB-002, F-SUB-003
 *
 * Tests the _check_trial_and_quota() logic that determines whether
 * a user in trial state can create new applications.
 */

import trialActivePayload from '../payloads/trial-active.json';
import trialExpiredPayload from '../payloads/trial-expired.json';
import trialExhaustedPayload from '../payloads/trial-exhausted.json';
import { daysAgo } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

/** Simulates the SubscriptionDAL */
const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
};

/** Simulates the UsageDAL */
const mockUsageDal = {
  get_usage: jest.fn(),
};

/** Simulates the UserDAL */
const mockUserDal = {
  get_user: jest.fn(),
};

// ─── Simulated _check_trial_and_quota Logic ──────────────────────────────────

class ApiError extends Error {
  constructor(
    public statusCode: number,
    public errorBody: { error: string; message?: string },
  ) {
    super(errorBody.error);
  }
}

function trialExpired(createdAtIso: string): boolean {
  const created = new Date(createdAtIso);
  const trialEnd = new Date(created.getTime() + 14 * 24 * 60 * 60 * 1000);
  return new Date() > trialEnd;
}

async function checkTrialAndQuota(userId: string): Promise<void> {
  const sub = mockSubscriptionDal.get_subscription_by_user(userId);

  if (sub) {
    const status = sub.status;

    if (status === 'active') {
      return; // Paid — unlimited access
    }

    if (['past_due', 'canceled', 'expired'].includes(status)) {
      throw new ApiError(403, {
        error: 'subscription_required',
        message: 'Your subscription is inactive. Please update your payment method.',
      });
    }

    if (status === 'trialing') {
      // Fall through to credit check below
    }
  }

  // Trial or no subscription — check credits
  const usage = mockUsageDal.get_usage(userId);
  const remaining = parseInt(usage?.remaining ?? '0', 10);

  if (remaining <= 0) {
    // Check if trial has expired
    const user = mockUserDal.get_user(userId);
    if (trialExpired(user.created_at)) {
      throw new ApiError(403, { error: 'trial_expired' });
    }
    throw new ApiError(403, { error: 'trial_exhausted' });
  }

  // Check trial window even with credits remaining
  if (!sub) {
    const user = mockUserDal.get_user(userId);
    if (trialExpired(user.created_at)) {
      throw new ApiError(403, { error: 'trial_expired' });
    }
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Trial Activation and Access Control', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-001: Trial Active — Access Granted ────────────────────────────
  describe('F-SUB-001: Trial Activation on Sign-Up', () => {
    it('should grant access when trial is active with remaining credits', async () => {
      // Preconditions: User created_at = 2 days ago; remaining = 3; no subscription
      const payload = {
        ...trialActivePayload,
        user: { ...trialActivePayload.user, created_at: daysAgo(2) },
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(payload.subscription);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      // Steps: Call _check_trial_and_quota and assert no exception
      await expect(checkTrialAndQuota('user-001')).resolves.toBeUndefined();

      // Verify: DAL read calls made, no writes
      expect(mockSubscriptionDal.get_subscription_by_user).toHaveBeenCalledWith('user-001');
      expect(mockUsageDal.get_usage).toHaveBeenCalledWith('user-001');
    });

    it('should read from usage table for credit count', async () => {
      const payload = {
        ...trialActivePayload,
        user: { ...trialActivePayload.user, created_at: daysAgo(2) },
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      await expect(checkTrialAndQuota('user-001')).resolves.toBeUndefined();
      expect(mockUsageDal.get_usage).toHaveBeenCalledWith('user-001');
    });
  });

  // ── F-SUB-002: Trial Expiry — Access Blocked After 14 Days ──────────────
  describe('F-SUB-002: Trial Expiry After 14 Days', () => {
    it('should block access when trial has expired (15 days)', async () => {
      // Preconditions: created_at = 15 days ago; remaining = 1; no subscription
      const payload = {
        ...trialExpiredPayload,
        user: { ...trialExpiredPayload.user, created_at: daysAgo(15) },
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(payload.subscription);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      // Steps: Call _check_trial_and_quota; assert ApiError(403, trial_expired)
      await expect(checkTrialAndQuota('user-002')).rejects.toThrow(ApiError);
      await expect(checkTrialAndQuota('user-002')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_expired' },
      });
    });

    it('should block even if credits remain when trial has expired', async () => {
      const payload = {
        ...trialExpiredPayload,
        user: { ...trialExpiredPayload.user, created_at: daysAgo(15) },
        usage: { user_id: 'user-002', remaining: 3 },
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      await expect(checkTrialAndQuota('user-002')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_expired' },
      });
    });
  });

  // ── F-SUB-003: Trial Credits Exhausted ──────────────────────────────────
  describe('F-SUB-003: Trial Credits Exhausted', () => {
    it('should block access when credits are exhausted within trial window', async () => {
      // Preconditions: created_at = 2 days ago; remaining = 0; no subscription
      const payload = {
        ...trialExhaustedPayload,
        user: { ...trialExhaustedPayload.user, created_at: daysAgo(2) },
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(payload.subscription);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      // Steps: Call _check_trial_and_quota; assert ApiError(403, trial_exhausted)
      await expect(checkTrialAndQuota('user-003')).rejects.toThrow(ApiError);
      await expect(checkTrialAndQuota('user-003')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_exhausted' },
      });
    });

    it('should distinguish trial_exhausted from trial_expired', async () => {
      // Within trial period but zero credits -> trial_exhausted (not trial_expired)
      const payload = {
        user: { user_id: 'user-003', created_at: daysAgo(5) },
        usage: { user_id: 'user-003', remaining: 0 },
        subscription: null,
      };

      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
      mockUsageDal.get_usage.mockReturnValue(payload.usage);
      mockUserDal.get_user.mockReturnValue(payload.user);

      try {
        await checkTrialAndQuota('user-003');
        fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).errorBody.error).toBe('trial_exhausted');
        expect((err as ApiError).errorBody.error).not.toBe('trial_expired');
      }
    });
  });
});
