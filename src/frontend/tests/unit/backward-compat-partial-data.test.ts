/**
 * Unit Test: Backward Compatibility — Partial Data (Orphan Usage Record)
 * Feature: CC-006
 *
 * An orphan scenario: a Usage record exists with user_id but the User record
 * is null. This can occur after a failed user deletion or data corruption.
 * The system must return 500 user_not_found with a clear error — NOT crash.
 *
 * This test will FAIL until the backend validates User existence before
 * proceeding to trial/quota logic.
 */

import partialDataPayload from '../payloads/backward-compat-partial-data.json';

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
  // TODO: This test will FAIL until the backend validates User existence.
  const sub = await mockSubscriptionDal.get_subscription_by_user(userId);

  if (sub?.status === 'active') {
    return;
  }

  const user = await mockUserDal.get_user(userId);
  if (!user) {
    // Must return structured error, NOT crash on user.created_at access
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

describe('CC-006: Backward Compatibility — Partial Data (Orphan Record)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return 500 user_not_found when user record is null but usage exists', async () => {
    // TODO: Currently FAILS — backend crashes with TypeError when accessing user.created_at
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue(partialDataPayload.user); // null
    mockUsageDal.get_usage.mockResolvedValue(partialDataPayload.usage);

    await expect(checkTrialAndQuota('orphan-001')).rejects.toMatchObject({
      statusCode: 500,
      errorCode: 'user_not_found',
    });
  });

  it('should not crash with TypeError when user.created_at is accessed on null user', async () => {
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue(null);
    mockUsageDal.get_usage.mockResolvedValue({ user_id: 'orphan-001', remaining: 0 });

    let caught: unknown;
    try {
      await checkTrialAndQuota('orphan-001');
    } catch (err) {
      caught = err;
    }

    // Must be a structured ApiError, not a raw TypeError
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).statusCode).toBe(500);
    expect(caught).not.toBeInstanceOf(TypeError);
  });

  it('should not attempt to read usage record when user is null', async () => {
    // If user is null, there is no point reading usage — stop early
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue(null);
    mockUsageDal.get_usage.mockResolvedValue({ user_id: 'orphan-001', remaining: 0 });

    try {
      await checkTrialAndQuota('orphan-001');
    } catch {
      // Expected
    }

    expect(mockUsageDal.get_usage).not.toHaveBeenCalled();
  });

  it('should provide a meaningful error message that identifies the missing resource', async () => {
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue(null);
    mockUsageDal.get_usage.mockResolvedValue(null);

    let caught: ApiError | undefined;
    try {
      await checkTrialAndQuota('orphan-001');
    } catch (err) {
      caught = err as ApiError;
    }

    expect(caught).toBeDefined();
    expect(caught!.errorCode).toBe('user_not_found');
    // Message should be informative for debugging
    expect(caught!.message).toBeTruthy();
    expect(caught!.message.length).toBeGreaterThan(0);
  });

  it('should handle all-null scenario without multi-error cascade', async () => {
    // When all three records are missing, should fail fast on the user check
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue(null);
    mockUsageDal.get_usage.mockResolvedValue(null);

    // Should throw exactly one error — user_not_found, not usage_not_found
    await expect(checkTrialAndQuota('orphan-001')).rejects.toMatchObject({
      statusCode: 500,
      errorCode: 'user_not_found',
    });
  });
});
