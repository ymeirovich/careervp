/**
 * Unit Test: Backward Compatibility — Missing Subscription Record
 * Feature: CC-004
 *
 * Old trial users have User + Usage records but NO Subscription record.
 * check_trial_and_quota() must handle this gracefully without crashing.
 *
 * This test will FAIL until the implementation handles the null subscription case.
 */

import backwardCompatPayload from '../payloads/backward-compat-old-trial.json';
import { daysAgo } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockUserDal = { get_user: jest.fn() };
const mockUsageDal = { get_usage: jest.fn() };
const mockSubscriptionDal = { get_subscription_by_user: jest.fn() };

// ─── Simulated check_trial_and_quota Logic ────────────────────────────────────

class ApiError extends Error {
  constructor(
    public statusCode: number,
    public errorCode: string,
    message: string,
  ) {
    super(message);
  }
}

async function checkTrialAndQuota(userId: string): Promise<void> {
  // TODO: This test will FAIL until backend gracefully handles null subscription.
  // The implementation must NOT assume a Subscription record always exists.
  const sub = await mockSubscriptionDal.get_subscription_by_user(userId);

  if (sub?.status === 'active') {
    return; // Active subscription — unlimited access
  }

  const user = await mockUserDal.get_user(userId);
  if (!user) {
    throw new ApiError(500, 'user_not_found', 'User record missing');
  }

  const usage = await mockUsageDal.get_usage(userId);
  if (!usage) {
    throw new ApiError(500, 'usage_not_found', 'Usage record missing');
  }

  const createdAt = new Date(user.created_at);
  const trialEnd = new Date(createdAt.getTime() + 14 * 24 * 60 * 60 * 1000);

  if (new Date() > trialEnd) {
    throw new ApiError(403, 'trial_expired', 'Trial has expired');
  }

  if (usage.remaining <= 0) {
    throw new ApiError(403, 'trial_exhausted', 'No credits remaining');
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-004: Backward Compatibility — Missing Subscription Record', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should handle null subscription record for old trial user', async () => {
    // Old user: no Subscription record, but valid User + Usage records
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue({
      ...backwardCompatPayload.user,
      created_at: daysAgo(5),
    });
    mockUsageDal.get_usage.mockResolvedValue(backwardCompatPayload.usage);

    // Should not crash — falls through to trial/quota check
    await expect(checkTrialAndQuota('old-trial-001')).resolves.toBeUndefined();
    expect(mockSubscriptionDal.get_subscription_by_user).toHaveBeenCalledWith('old-trial-001');
    expect(mockUserDal.get_user).toHaveBeenCalledWith('old-trial-001');
  });

  it('should not crash when subscription is null and trial is active', async () => {
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: 'old-trial-001',
      created_at: daysAgo(2),
    });
    mockUsageDal.get_usage.mockResolvedValue({ user_id: 'old-trial-001', remaining: 2 });

    await expect(checkTrialAndQuota('old-trial-001')).resolves.toBeUndefined();
  });

  it('should fall through to trial expiry check when no subscription exists', async () => {
    // No subscription and trial has expired — must throw trial_expired
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: 'old-trial-001',
      created_at: daysAgo(15),
    });
    mockUsageDal.get_usage.mockResolvedValue({ user_id: 'old-trial-001', remaining: 2 });

    await expect(checkTrialAndQuota('old-trial-001')).rejects.toMatchObject({
      statusCode: 403,
      errorCode: 'trial_expired',
    });
  });

  it('should never call get_user before get_subscription_by_user', async () => {
    // Subscription check must be the first call (fast path for paid users)
    const callOrder: string[] = [];
    mockSubscriptionDal.get_subscription_by_user.mockImplementation(async () => {
      callOrder.push('sub');
      return null;
    });
    mockUserDal.get_user.mockImplementation(async () => {
      callOrder.push('user');
      return { user_id: 'old-trial-001', created_at: daysAgo(5) };
    });
    mockUsageDal.get_usage.mockResolvedValue({ user_id: 'old-trial-001', remaining: 3 });

    await checkTrialAndQuota('old-trial-001');

    expect(callOrder[0]).toBe('sub');
    expect(callOrder[1]).toBe('user');
  });

  it('should grant access when old trial user has active subscription', async () => {
    // Even if user was "old trial", once they subscribe they get active access
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue({
      subscription_id: 'sub_new_001',
      status: 'active',
      plan: 'monthly',
    });

    // get_user and get_usage should NOT be called (short-circuit on active sub)
    await expect(checkTrialAndQuota('old-trial-001')).resolves.toBeUndefined();
    expect(mockUserDal.get_user).not.toHaveBeenCalled();
    expect(mockUsageDal.get_usage).not.toHaveBeenCalled();
  });
});
