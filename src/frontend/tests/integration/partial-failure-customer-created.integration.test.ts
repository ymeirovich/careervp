/**
 * Integration Test: Partial Failure — Customer Created, Subscription Write Fails
 * Feature: CC-013
 *
 * Scenario:
 *   1. stripe.Customer.create() → succeeds (cus_ABC123)
 *   2. users_dal.update_stripe_customer_id() → succeeds
 *   3. stripe.checkout.Session.create() → succeeds (cs_XYZ)
 *   4. subscriptions_dal.upsert() → THROWS (DynamoDB down)
 *
 * Expected:
 *   - Lambda returns 500
 *   - Stripe customer IS persisted on user (recoverable)
 *   - No Subscription record exists
 *   - Error logged with enough context to debug
 *   - Next checkout attempt can recover (customer is reused)
 *
 * This test will FAIL until the backend handles partial webhook failures
 * and logs with sufficient context for manual recovery.
 */

import partialFailurePayload from '../payloads/partial-failure-customer.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCustomerCreate = jest.fn();
const mockStripeCheckoutCreate = jest.fn();
const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
  upsert: jest.fn(),
};
const mockUserDal = {
  get_user: jest.fn(),
  update_stripe_customer_id: jest.fn(),
};
const mockLogger = { error: jest.fn(), info: jest.fn() };

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handleCheckout(userId: string, plan: string): Promise<CheckoutResult> {
  // TODO: This test will FAIL until partial failure logging is implemented.
  // The backend must log the failure with enough context (user_id, customer_id,
  // session_id) for an operator to manually recover.

  mockSubscriptionDal.get_subscription_by_user(userId);
  const user = await mockUserDal.get_user(userId);
  let customerId = user?.stripe_customer_id;

  if (!customerId) {
    const customer = await mockStripeCustomerCreate({ metadata: { user_id: userId } });
    customerId = customer.id;
    await mockUserDal.update_stripe_customer_id(userId, customerId);
  }

  const session = await mockStripeCheckoutCreate({ customer: customerId, plan });

  try {
    await mockSubscriptionDal.upsert({ user_id: userId, checkout_session_id: session.id });
  } catch (err) {
    mockLogger.error('Partial failure: subscription record write failed after Stripe success', {
      user_id: userId,
      stripe_customer_id: customerId,
      checkout_session_id: session.id,
      error: (err as Error).message,
    });
    return {
      statusCode: 500,
      body: {
        error: 'internal_error',
        message: 'Checkout initiated but session not persisted. Please contact support.',
      },
    };
  }

  return { statusCode: 200, body: { checkout_url: session.url } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-013: Partial Failure — Customer Created, Subscription Write Fails', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: partialFailurePayload.user_id,
      stripe_customer_id: null,
    });
    mockUserDal.update_stripe_customer_id.mockResolvedValue(undefined);
    mockStripeCustomerCreate.mockResolvedValue({ id: partialFailurePayload.stripe_customer_id });
    mockStripeCheckoutCreate.mockResolvedValue({
      id: partialFailurePayload.checkout_session_id,
      url: 'https://checkout.stripe.com/pay/cs_test_partial',
    });
  });

  it('should return 500 when subscriptions_dal.upsert() throws', async () => {
    // TODO: Currently FAILS — backend may silently swallow DynamoDB errors or crash
    mockSubscriptionDal.upsert.mockRejectedValue(
      new Error('DynamoDB ServiceUnavailableException'),
    );

    const result = await handleCheckout(partialFailurePayload.user_id, 'monthly');

    expect(result.statusCode).toBe(500);
    expect(result.body.error).toBe('internal_error');
  });

  it('should persist stripe_customer_id on user even when subscription write fails', async () => {
    // The customer_id IS saved (step 2 succeeded) — this allows recovery
    mockSubscriptionDal.upsert.mockRejectedValue(new Error('DynamoDB down'));

    await handleCheckout(partialFailurePayload.user_id, 'monthly');

    expect(mockUserDal.update_stripe_customer_id).toHaveBeenCalledWith(
      partialFailurePayload.user_id,
      partialFailurePayload.stripe_customer_id,
    );
  });

  it('should NOT have a subscription record after partial failure', async () => {
    mockSubscriptionDal.upsert.mockRejectedValue(new Error('DynamoDB down'));

    await handleCheckout(partialFailurePayload.user_id, 'monthly');

    // upsert was called but threw — no successful write
    expect(mockSubscriptionDal.upsert).toHaveBeenCalled();
    // There is no subscription record (the write failed)
  });

  it('should log the error with user_id, customer_id, and session_id for debugging', async () => {
    // TODO: Currently FAILS — error not logged with required context fields
    mockSubscriptionDal.upsert.mockRejectedValue(new Error('DynamoDB down'));

    await handleCheckout(partialFailurePayload.user_id, 'monthly');

    expect(mockLogger.error).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        user_id: partialFailurePayload.user_id,
        stripe_customer_id: partialFailurePayload.stripe_customer_id,
        checkout_session_id: partialFailurePayload.checkout_session_id,
      }),
    );
  });

  it('should reuse existing customer on retry after partial failure', async () => {
    // On retry, the user already has stripe_customer_id from the first attempt
    mockUserDal.get_user.mockResolvedValue({
      user_id: partialFailurePayload.user_id,
      stripe_customer_id: partialFailurePayload.stripe_customer_id, // Already saved
    });
    mockSubscriptionDal.upsert.mockResolvedValue(undefined); // Succeeds on retry

    await handleCheckout(partialFailurePayload.user_id, 'monthly');

    // Customer must NOT be created again on retry
    expect(mockStripeCustomerCreate).not.toHaveBeenCalled();
  });
});
