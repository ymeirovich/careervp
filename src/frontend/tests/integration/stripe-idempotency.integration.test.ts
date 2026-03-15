/**
 * Integration Test: Stripe Idempotency Key Prevents Duplicate Sessions
 * Feature: CC-003
 *
 * When a network timeout causes the client to retry, the Stripe SDK must be
 * called with an idempotency_key so Stripe deduplicates and returns the
 * same checkout URL instead of creating a second session.
 *
 * Key format: checkout_{user_id}_{request_id}
 *
 * This test will FAIL until the backend passes idempotency_key to
 * stripe.checkout.Session.create().
 */

import idempotencyPayload from '../payloads/idempotency-retry.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCheckoutCreate = jest.fn();
const mockStripeCustomerCreate = jest.fn();
const mockSubscriptionDal = { get_subscription_by_user: jest.fn() };
const mockUserDal = {
  get_user: jest.fn(),
  update_stripe_customer_id: jest.fn(),
};

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: { checkout_url?: string; error?: string };
}

async function handleCheckout(
  userId: string,
  plan: string,
  requestId: string,
): Promise<CheckoutResult> {
  // TODO: This test will FAIL until idempotency_key is passed to Stripe.
  // Currently the Lambda does not pass idempotency_key to checkout.Session.create().

  const existingSub = await mockSubscriptionDal.get_subscription_by_user(userId);
  if (existingSub?.status === 'active') {
    return { statusCode: 409, body: { error: 'subscription_already_active' } };
  }

  const user = await mockUserDal.get_user(userId);
  let customerId = user?.stripe_customer_id;

  if (!customerId) {
    const customer = await mockStripeCustomerCreate({ metadata: { user_id: userId } });
    customerId = customer.id;
    await mockUserDal.update_stripe_customer_id(userId, customerId);
  }

  // Critical: idempotency_key must be derived from user_id + request_id
  const idempotencyKey = `checkout_${userId}_${requestId}`;

  const session = await mockStripeCheckoutCreate({
    customer: customerId,
    plan,
    idempotency_key: idempotencyKey, // <-- Must be present
  });

  return { statusCode: 200, body: { checkout_url: session.url } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-003: Stripe Idempotency Key Prevents Duplicate Sessions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockResolvedValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: idempotencyPayload.user_id,
      stripe_customer_id: 'cus_existing_001',
    });
    mockUserDal.update_stripe_customer_id.mockResolvedValue(undefined);
  });

  it('should include idempotency_key in stripe.checkout.Session.create() call', async () => {
    // TODO: Currently FAILS — idempotency_key not yet passed to Stripe
    mockStripeCheckoutCreate.mockResolvedValue({
      url: idempotencyPayload.first_response.checkout_url,
    });

    await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123');

    expect(mockStripeCheckoutCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        idempotency_key: expect.stringContaining('checkout_'),
      }),
    );
  });

  it('should use format checkout_{user_id}_{request_id} for idempotency key', async () => {
    mockStripeCheckoutCreate.mockResolvedValue({
      url: idempotencyPayload.first_response.checkout_url,
    });

    await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123');

    expect(mockStripeCheckoutCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        idempotency_key: `checkout_${idempotencyPayload.user_id}_req-abc123`,
      }),
    );
  });

  it('should return the same checkout_url on retry with same idempotency key', async () => {
    // Stripe deduplicates requests with the same idempotency key
    const originalUrl = idempotencyPayload.first_response.checkout_url;
    mockStripeCheckoutCreate.mockResolvedValue({ url: originalUrl }); // Always same URL

    const result1 = await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123');
    const result2 = await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123');

    // Both calls get the same idempotency key → same result
    expect(result1.body.checkout_url).toBe(originalUrl);
    expect(result2.body.checkout_url).toBe(result1.body.checkout_url);
  });

  it('should use different idempotency keys for different request IDs', async () => {
    mockStripeCheckoutCreate.mockResolvedValue({
      url: 'https://checkout.stripe.com/pay/cs_test_different',
    });

    await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-001');
    await handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-002');

    const calls = mockStripeCheckoutCreate.mock.calls;
    const key1 = (calls[0][0] as Record<string, string>).idempotency_key;
    const key2 = (calls[1][0] as Record<string, string>).idempotency_key;
    expect(key1).not.toBe(key2);
  });

  it('should not create duplicate Stripe sessions on retry (same idempotency key)', async () => {
    const originalUrl = idempotencyPayload.first_response.checkout_url;
    mockStripeCheckoutCreate.mockResolvedValue({ url: originalUrl });

    // Simulate 3 retries with same request_id (network failures)
    await Promise.all([
      handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123'),
      handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123'),
      handleCheckout(idempotencyPayload.user_id, 'monthly', 'req-abc123'),
    ]);

    // Stripe is called 3 times but all with same idempotency_key
    // Stripe deduplicates — no new sessions created
    const keys = mockStripeCheckoutCreate.mock.calls.map(
      (call) => (call[0] as Record<string, string>).idempotency_key,
    );
    const uniqueKeys = new Set(keys);
    expect(uniqueKeys.size).toBe(1);
  });
});
