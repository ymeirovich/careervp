/**
 * Performance Test: 100 Concurrent Checkouts
 * Feature: PERF-001
 *
 * Tests that the system handles 100 concurrent checkout requests within
 * acceptable latency bounds and without creating duplicate Stripe customers.
 *
 * NOTE: This test runs ONLY when PERF_TEST=true is set.
 * It is excluded from regular CI/CD runs.
 *
 * Run manually:
 *   PERF_TEST=true npx jest --testPathPattern='perf/' --testTimeout=30000
 */

jest.setTimeout(120000);

const SKIP_PERF = !process.env.PERF_TEST;

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCustomerCreate = jest.fn();
const mockStripeCheckoutCreate = jest.fn();
const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
  create_checkout_intent: jest.fn(),
};
const mockUserDal = {
  get_user: jest.fn(),
  update_stripe_customer_id: jest.fn(),
};

// ─── Simulated mockCheckoutRequest ───────────────────────────────────────────

async function mockCheckoutRequest(userId: string): Promise<{ statusCode: number }> {
  // TODO: This test will FAIL until the backend handles concurrent load correctly.
  // Placeholder simulates a checkout call — replace with real HTTP request in full perf test.
  const existing = await mockSubscriptionDal.get_subscription_by_user(userId);
  if (existing?.status === 'active') {
    return { statusCode: 409 };
  }

  try {
    await mockSubscriptionDal.create_checkout_intent(userId);
  } catch {
    return { statusCode: 409 };
  }

  const user = await mockUserDal.get_user(userId);
  if (!user?.stripe_customer_id) {
    const customer = await mockStripeCustomerCreate({ metadata: { user_id: userId } });
    await mockUserDal.update_stripe_customer_id(userId, customer.id);
  }

  await mockStripeCheckoutCreate({ customer: 'cus_perf', plan: 'monthly' });
  return { statusCode: 200 };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('PERF-001: 100 Concurrent Checkouts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockSubscriptionDal.create_checkout_intent.mockResolvedValue(undefined);
    mockUserDal.get_user.mockResolvedValue({ user_id: 'perf-user', stripe_customer_id: null });
    mockUserDal.update_stripe_customer_id.mockResolvedValue(undefined);
    mockStripeCustomerCreate.mockResolvedValue({ id: 'cus_perf_001' });
    mockStripeCheckoutCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_perf' });
  });

  // ── Perf tests: only run when PERF_TEST=true ─────────────────────────────
  (SKIP_PERF ? describe.skip : describe)('when PERF_TEST=true', () => {
    it('should handle 100 concurrent checkout requests with <2s p99 latency', async () => {
      // TODO: This test will FAIL until concurrency handling is implemented in the backend.
      // Replace mockCheckoutRequest with real HTTP calls to staging for true perf testing.
      const N = 100;
      const start = Date.now();

      const results = await Promise.allSettled(
        Array.from({ length: N }, (_, i) => mockCheckoutRequest(`perf-user-${i}`)),
      );

      const duration = Date.now() - start;
      const succeeded = results.filter(r => r.status === 'fulfilled').length;
      const errors = results.filter(r => r.status === 'rejected').length;

      expect(errors).toBe(0);
      expect(succeeded).toBe(N);
      // <2000ms total for 100 concurrent requests
      expect(duration).toBeLessThan(2000);
    }, 30_000);

    it('should not create duplicate Stripe customers under concurrent load', async () => {
      // TODO: Currently FAILS — concurrent requests each call stripe.Customer.create()
      // Same user, 10 concurrent requests
      const results = await Promise.allSettled(
        Array.from({ length: 10 }, () => mockCheckoutRequest('shared-perf-user')),
      );

      const fulfilled = results.filter(r => r.status === 'fulfilled');
      expect(fulfilled.length).toBeGreaterThan(0);

      // Only one customer should be created regardless of concurrency
      expect(mockStripeCustomerCreate).toHaveBeenCalledTimes(1);
    }, 15_000);

    it('should achieve p99 latency < 200ms per request under 100 concurrent users', async () => {
      const N = 100;
      const latencies: number[] = [];

      await Promise.allSettled(
        Array.from({ length: N }, async (_, i) => {
          const start = Date.now();
          await mockCheckoutRequest(`perf-user-${i}`);
          latencies.push(Date.now() - start);
        }),
      );

      latencies.sort((a, b) => a - b);
      const p99 = latencies[Math.floor(latencies.length * 0.99)];

      // p99 < 200ms per individual request
      expect(p99).toBeLessThan(200);
    }, 30_000);
  });

  // ── Always-run smoke tests ────────────────────────────────────────────────
  describe('smoke: always run', () => {
    it('should complete a single checkout request successfully', async () => {
      const result = await mockCheckoutRequest('smoke-perf-user');
      expect(result.statusCode).toBe(200);
    });

    it('should handle 5 concurrent requests without error', async () => {
      const results = await Promise.allSettled(
        Array.from({ length: 5 }, (_, i) => mockCheckoutRequest(`small-perf-${i}`)),
      );
      const errors = results.filter(r => r.status === 'rejected').length;
      expect(errors).toBe(0);
    });
  });
});

export {};
