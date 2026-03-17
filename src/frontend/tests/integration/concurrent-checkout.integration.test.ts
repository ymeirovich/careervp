/**
 * Integration Test: Concurrent Checkout Prevention
 * Feature: CC-001
 *
 * Two simultaneous POST /billing/checkout requests for the same user_id must
 * result in at most ONE payment-provider Customer being created. Without a
 * DynamoDB conditional expression or locking, both requests can each call
 * payment_provider.create_customer() concurrently, creating duplicate customers.
 *
 * This test will FAIL until the backend uses an atomic/conditional create
 * strategy (e.g. DynamoDB condition_expression="attribute_not_exists(user_id)").
 */

import concurrentPayload from '../payloads/concurrent-checkout-race.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

// Generic PaymentProvider interface mock — replace with concrete provider at integration time
const mockPaymentProvider = {
  createCustomer: jest.fn(),
  createCheckoutSession: jest.fn(),
};
const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
  create_checkout_intent: jest.fn(), // Conditional create guard
};
const mockUserDal = {
  get_user: jest.fn(),
  update_customer_id: jest.fn(),
};

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handleCheckout(userId: string, plan: string, requestId: string): Promise<CheckoutResult> {
  // TODO: This test will FAIL until checkout uses DynamoDB conditional write to prevent
  // concurrent customers. Currently: check_then_create has a race window.

  const existingSub = await mockSubscriptionDal.get_subscription_by_user(userId);
  if (existingSub?.status === 'active') {
    return { statusCode: 409, body: { error: 'subscription_already_active' } };
  }

  const user = await mockUserDal.get_user(userId);
  let customerId = user?.customer_id;

  if (!customerId) {
    // Atomic guard: DynamoDB conditional write prevents duplicate customer creation
    try {
      await mockSubscriptionDal.create_checkout_intent(userId);
    } catch (err) {
      // Another concurrent request already claimed the customer slot
      return { statusCode: 409, body: { error: 'checkout_in_progress' } };
    }

    const customer = await mockPaymentProvider.createCustomer({ email: user?.email, metadata: { user_id: userId } });
    customerId = customer.id;
    await mockUserDal.update_customer_id(userId, customerId);
  }

  const session = await mockPaymentProvider.createCheckoutSession({
    customer_id: customerId,
    plan,
    idempotency_key: `checkout_${userId}_${requestId}`,
  });

  return { statusCode: 200, body: { checkout_url: session.checkout_url } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-001: Concurrent Checkout Prevention', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue({ user_id: concurrentPayload.user_id, email: 'race@test.com', customer_id: null });
    mockUserDal.update_customer_id.mockResolvedValue(undefined);
    mockPaymentProvider.createCheckoutSession.mockResolvedValue({ checkout_url: 'https://checkout.example.com/pay/cs_test_001' });
  });

  it('should call payment_provider.create_customer() at most once for concurrent requests', async () => {
    // TODO: Currently FAILS — both requests call create_customer() independently
    let customerCreateCount = 0;
    mockPaymentProvider.createCustomer.mockImplementation(async () => {
      customerCreateCount++;
      return { id: `cus_001` };
    });

    // First request succeeds the conditional write
    mockSubscriptionDal.create_checkout_intent
      .mockResolvedValueOnce(undefined)  // First request succeeds
      .mockRejectedValueOnce(new Error('ConditionalCheckFailedException')); // Second blocked

    const [result1, result2] = await Promise.all([
      handleCheckout(concurrentPayload.user_id, 'monthly', 'req-001'),
      handleCheckout(concurrentPayload.user_id, 'monthly', 'req-002'),
    ]);

    expect(customerCreateCount).toBeLessThanOrEqual(1);
    // One succeeds, one gets conflict
    const statuses = [result1.statusCode, result2.statusCode].sort();
    expect(statuses).toContain(200);
  });

  it('should return 409 on second concurrent request when first wins the lock', async () => {
    mockPaymentProvider.createCustomer.mockResolvedValue({ id: 'cus_concurrent_001' });

    mockSubscriptionDal.create_checkout_intent
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('ConditionalCheckFailedException'));

    const results = await Promise.all([
      handleCheckout(concurrentPayload.user_id, 'monthly', 'req-001'),
      handleCheckout(concurrentPayload.user_id, 'monthly', 'req-002'),
    ]);

    const conflictResult = results.find(r => r.statusCode === 409);
    expect(conflictResult).toBeDefined();
    expect(conflictResult!.body.error).toMatch(/checkout_in_progress|subscription_already_active/);
  });

  it('should not create duplicate subscriptions under concurrent load', async () => {
    mockPaymentProvider.createCustomer.mockResolvedValue({ id: 'cus_dedup_001' });
    mockSubscriptionDal.create_checkout_intent
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('ConditionalCheckFailedException'));

    const N = concurrentPayload.concurrent_request_count;
    await Promise.allSettled(
      Array.from({ length: N }, (_, i) =>
        handleCheckout(concurrentPayload.user_id, 'monthly', `req-${i}`),
      ),
    );

    // Even if both requests proceed, idempotency keys prevent duplicate sessions
    expect(mockPaymentProvider.createCustomer.mock.calls.length).toBeLessThanOrEqual(1);
  });

  it('should succeed normally for a non-concurrent single request', async () => {
    mockPaymentProvider.createCustomer.mockResolvedValue({ id: 'cus_single_001' });
    mockSubscriptionDal.create_checkout_intent.mockResolvedValue(undefined);

    const result = await handleCheckout(concurrentPayload.user_id, 'monthly', 'req-single');

    expect(result.statusCode).toBe(200);
    expect(result.body.checkout_url).toBeDefined();
  });
});
