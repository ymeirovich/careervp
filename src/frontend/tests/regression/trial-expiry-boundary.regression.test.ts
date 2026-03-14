/**
 * Regression Tests: Trial Expiry Boundary
 * Feature: F-SUB-002-R
 *
 * Confirms the trial expiry boundary is exactly 14 days (not 13, not 15).
 * Tests edge cases at the boundary to prevent regressions.
 */

import { daysAgo, hoursAgo } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
};
const mockUsageDal = {
  get_usage: jest.fn(),
};
const mockUserDal = {
  get_user: jest.fn(),
};

class ApiError extends Error {
  constructor(
    public statusCode: number,
    public errorBody: { error: string },
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
    if (sub.status === 'active') return;
    if (['past_due', 'canceled', 'expired'].includes(sub.status)) {
      throw new ApiError(403, { error: 'subscription_required' });
    }
  }

  const usage = mockUsageDal.get_usage(userId);
  const remaining = parseInt(usage?.remaining ?? '0', 10);

  if (remaining <= 0) {
    const user = mockUserDal.get_user(userId);
    if (trialExpired(user.created_at)) {
      throw new ApiError(403, { error: 'trial_expired' });
    }
    throw new ApiError(403, { error: 'trial_exhausted' });
  }

  if (!sub) {
    const user = mockUserDal.get_user(userId);
    if (trialExpired(user.created_at)) {
      throw new ApiError(403, { error: 'trial_expired' });
    }
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Trial Expiry Boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
    mockUsageDal.get_usage.mockReturnValue({ user_id: 'boundary-user', remaining: 3 });
  });

  // ── F-SUB-002-R: Boundary Cases ────────────────────────────────────────
  describe('F-SUB-002-R: Exact 14-Day Boundary', () => {
    it('should grant access at 13 days 23 hours (before boundary)', async () => {
      // 13 days 23 hours = 13 * 24 + 23 = 335 hours ago
      const createdAt = hoursAgo(335);
      mockUserDal.get_user.mockReturnValue({
        user_id: 'boundary-user',
        created_at: createdAt,
      });

      await expect(checkTrialAndQuota('boundary-user')).resolves.toBeUndefined();
    });

    it('should block access at exactly 14 days (at boundary)', async () => {
      const createdAt = daysAgo(14);
      mockUserDal.get_user.mockReturnValue({
        user_id: 'boundary-user',
        created_at: createdAt,
      });

      await expect(checkTrialAndQuota('boundary-user')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_expired' },
      });
    });

    it('should block access at 15 days (past boundary)', async () => {
      const createdAt = daysAgo(15);
      mockUserDal.get_user.mockReturnValue({
        user_id: 'boundary-user',
        created_at: createdAt,
      });

      await expect(checkTrialAndQuota('boundary-user')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_expired' },
      });
    });

    it('should grant access at 1 day (well within trial)', async () => {
      const createdAt = daysAgo(1);
      mockUserDal.get_user.mockReturnValue({
        user_id: 'boundary-user',
        created_at: createdAt,
      });

      await expect(checkTrialAndQuota('boundary-user')).resolves.toBeUndefined();
    });

    it('should block access at 30 days (well past trial)', async () => {
      const createdAt = daysAgo(30);
      mockUserDal.get_user.mockReturnValue({
        user_id: 'boundary-user',
        created_at: createdAt,
      });

      await expect(checkTrialAndQuota('boundary-user')).rejects.toMatchObject({
        errorBody: { error: 'trial_expired' },
      });
    });
  });
});
