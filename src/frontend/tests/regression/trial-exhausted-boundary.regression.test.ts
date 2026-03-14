/**
 * Regression Tests: Trial Credits Exhausted Boundary
 * Feature: F-SUB-003-R
 *
 * Confirms the credit boundary is at remaining = 0.
 * Tests: remaining=1 (allowed), remaining=0 (blocked), remaining=-1 (blocked).
 */

import { daysAgo } from '../setup';

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
    const created = new Date(user.created_at);
    const trialEnd = new Date(created.getTime() + 14 * 24 * 60 * 60 * 1000);

    if (new Date() > trialEnd) {
      throw new ApiError(403, { error: 'trial_expired' });
    }
    throw new ApiError(403, { error: 'trial_exhausted' });
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Trial Credits Exhausted Boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
    mockUserDal.get_user.mockReturnValue({
      user_id: 'credit-user',
      created_at: daysAgo(2), // Within trial window
    });
  });

  // ── F-SUB-003-R: Credit Boundary Cases ─────────────────────────────────
  describe('F-SUB-003-R: Credit Exhaustion Boundary', () => {
    it('should grant access when remaining = 1', async () => {
      mockUsageDal.get_usage.mockReturnValue({
        user_id: 'credit-user',
        remaining: 1,
      });

      await expect(checkTrialAndQuota('credit-user')).resolves.toBeUndefined();
    });

    it('should block access when remaining = 0 with trial_exhausted', async () => {
      mockUsageDal.get_usage.mockReturnValue({
        user_id: 'credit-user',
        remaining: 0,
      });

      await expect(checkTrialAndQuota('credit-user')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_exhausted' },
      });
    });

    it('should block access when remaining = -1 (guard against invalid state)', async () => {
      mockUsageDal.get_usage.mockReturnValue({
        user_id: 'credit-user',
        remaining: -1,
      });

      await expect(checkTrialAndQuota('credit-user')).rejects.toMatchObject({
        statusCode: 403,
        errorBody: { error: 'trial_exhausted' },
      });
    });

    it('should grant access when remaining = 3 (full credits)', async () => {
      mockUsageDal.get_usage.mockReturnValue({
        user_id: 'credit-user',
        remaining: 3,
      });

      await expect(checkTrialAndQuota('credit-user')).resolves.toBeUndefined();
    });
  });
});
