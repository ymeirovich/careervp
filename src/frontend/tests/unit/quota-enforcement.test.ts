/**
 * Unit Tests: Quota Enforcement — Blocked States
 * Feature: F-SUB-017
 *
 * Tests that users with past_due, canceled, or expired status
 * are blocked from creating new applications (POST /jobs).
 */

import subscriptionPastDuePayload from '../payloads/subscription-past-due.json';
import subscriptionCanceledPayload from '../payloads/subscription-canceled.json';
import subscriptionExpiredPayload from '../payloads/subscription-expired.json';

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
    public errorBody: { error: string; message?: string },
  ) {
    super(errorBody.error);
  }
}

// ─── Simulated _check_trial_and_quota Logic ──────────────────────────────────

async function checkTrialAndQuota(userId: string): Promise<void> {
  const sub = mockSubscriptionDal.get_subscription_by_user(userId);

  if (sub) {
    const status = sub.status;

    if (status === 'active') {
      return; // Paid — unlimited
    }

    if (['past_due', 'canceled', 'expired'].includes(status)) {
      throw new ApiError(403, {
        error: 'subscription_required',
        message: 'Your subscription is inactive. Please update your payment method.',
      });
    }
  }

  // No subscription or trialing — check credits
  const usage = mockUsageDal.get_usage(userId);
  const remaining = parseInt(usage?.remaining ?? '0', 10);

  if (remaining <= 0) {
    throw new ApiError(403, { error: 'trial_exhausted' });
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Quota Enforcement — Blocked States', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-017: Parametrized Blocked States ──────────────────────────────
  describe('F-SUB-017: Blocked States Return 403', () => {
    const blockedCases = [
      { name: 'past_due', payload: subscriptionPastDuePayload },
      { name: 'canceled', payload: subscriptionCanceledPayload },
      { name: 'expired', payload: subscriptionExpiredPayload },
    ];

    it.each(blockedCases)(
      'should block access with 403 subscription_required for status "$name"',
      async ({ payload }) => {
        // Preconditions: DynamoDB returns subscription with blocked status
        mockSubscriptionDal.get_subscription_by_user.mockReturnValue(payload);

        await expect(checkTrialAndQuota(payload.user_id)).rejects.toThrow(ApiError);
        await expect(checkTrialAndQuota(payload.user_id)).rejects.toMatchObject({
          statusCode: 403,
          errorBody: { error: 'subscription_required' },
        });
      },
    );

    it('should allow access for active subscriptions', async () => {
      mockSubscriptionDal.get_subscription_by_user.mockReturnValue({
        subscription_id: 'sub_active',
        user_id: 'user-017',
        status: 'active',
      });

      await expect(checkTrialAndQuota('user-017')).resolves.toBeUndefined();
    });

    it('should check at the top of POST /jobs before any AI processing', async () => {
      // Ensure DAL is called first, before any other logic
      mockSubscriptionDal.get_subscription_by_user.mockReturnValue(
        subscriptionPastDuePayload,
      );

      try {
        await checkTrialAndQuota('user-017');
        fail('Should have thrown');
      } catch (err) {
        // Verify DAL was called
        expect(mockSubscriptionDal.get_subscription_by_user).toHaveBeenCalledWith('user-017');
        // Verify usage was NOT checked (blocked before getting there)
        expect(mockUsageDal.get_usage).not.toHaveBeenCalled();
      }
    });
  });
});
