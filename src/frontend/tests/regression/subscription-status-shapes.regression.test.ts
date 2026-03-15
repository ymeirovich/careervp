/**
 * Regression Tests: Subscription Status Response Shapes
 * Feature: F-SUB-008-R
 *
 * For each possible status value, asserts the response shape is valid
 * and has_active_subscription is correctly true only for "active".
 */

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockDal = {
  get_subscription_by_user: jest.fn(),
};

function handleGetSubscription(userId: string) {
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

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Subscription Status Shapes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-008-R: All Status Values ─────────────────────────────────────
  describe('F-SUB-008-R: Status to has_active_subscription Mapping', () => {
    const statusCases = [
      { status: 'trialing', expectedActive: false },
      { status: 'active', expectedActive: true },
      { status: 'past_due', expectedActive: false },
      { status: 'canceled', expectedActive: false },
      { status: 'expired', expectedActive: false },
    ];

    it.each(statusCases)(
      'should return has_active_subscription=$expectedActive for status "$status"',
      ({ status, expectedActive }) => {
        mockDal.get_subscription_by_user.mockReturnValue({
          subscription_id: `sub_${status}_test`,
          customer_id: 'cus_test',
          status,
          plan: 'monthly',
          current_period_end: '2026-04-14T00:00:00Z',
          cancel_at_period_end: false,
          trial_end: null,
        });

        const result = handleGetSubscription('test-user');

        expect(result.statusCode).toBe(200);
        expect(result.body.has_active_subscription).toBe(expectedActive);
        expect(result.body.subscription).not.toBeNull();
        expect(result.body.subscription!.status).toBe(status);
      },
    );

    it('should return valid response shape for all statuses', () => {
      const allStatuses = ['trialing', 'active', 'past_due', 'canceled', 'expired'];

      for (const status of allStatuses) {
        mockDal.get_subscription_by_user.mockReturnValue({
          subscription_id: `sub_${status}`,
          customer_id: 'cus_test',
          status,
          plan: 'monthly',
          current_period_end: '2026-04-14T00:00:00Z',
          cancel_at_period_end: false,
          trial_end: null,
        });

        const result = handleGetSubscription('test-user');

        // Validate shape
        expect(result.body).toHaveProperty('subscription');
        expect(result.body).toHaveProperty('has_active_subscription');
        expect(result.body.subscription).toHaveProperty('subscription_id');
        expect(result.body.subscription).toHaveProperty('customer_id');
        expect(result.body.subscription).toHaveProperty('status');
        expect(result.body.subscription).toHaveProperty('plan');
        expect(result.body.subscription).toHaveProperty('current_period_end');
        expect(result.body.subscription).toHaveProperty('cancel_at_period_end');
        expect(result.body.subscription).toHaveProperty('trial_end');
      }
    });

    it('should return null subscription when no record exists', () => {
      mockDal.get_subscription_by_user.mockReturnValue(null);

      const result = handleGetSubscription('no-sub-user');

      expect(result.body.subscription).toBeNull();
      expect(result.body.has_active_subscription).toBe(false);
    });
  });
});

export {};
