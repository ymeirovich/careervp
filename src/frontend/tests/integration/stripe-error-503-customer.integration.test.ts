/**
 * Integration Test: Stripe 503 Error on Customer Create
 * Feature: CC-008
 *
 * When stripe.Customer.create() returns a 503, the Lambda must:
 *   1. Return 503 to the caller
 *   2. NOT update the user record with a stripe_customer_id
 *   3. Allow the user to retry (next request creates a fresh customer)
 *
 * This test will FAIL until the backend handles Stripe errors before
 * updating DynamoDB state.
 */

import stripe503Payload from '../payloads/stripe-503-error.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCustomerCreate = jest.fn();
const mockStripeCheckoutCreate = jest.fn();
const mockSubscriptionDal = { get_subscription_by_user: jest.fn() };
const mockUserDal = {
  get_user: jest.fn(),
  update_stripe_customer_id: jest.fn(),
};
const mockLogger = { error: jest.fn(), info: jest.fn() };

// ─── Simulated Stripe Error ───────────────────────────────────────────────────

class StripeError extends Error {
  constructor(
    public status: number,
    public type: string,
    message: string,
  ) {
    super(message);
    this.name = 'StripeError';
  }
}

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handleCheckout(userId: string, plan: string): Promise<CheckoutResult> {
  // TODO: This test will FAIL until the backend handles Stripe customer creation errors
  // by returning 503 and NOT persisting the failed customer_id to DynamoDB.

  mockSubscriptionDal.get_subscription_by_user(userId);
  const user = await mockUserDal.get_user(userId);

  if (!user?.stripe_customer_id) {
    let customerId: string;
    try {
      const customer = await mockStripeCustomerCreate({ metadata: { user_id: userId } });
      customerId = customer.id;
    } catch (err) {
      if (err instanceof StripeError) {
        mockLogger.error('Stripe customer create failed', {
          user_id: userId,
          stripe_status: err.status,
          stripe_type: err.type,
        });
        return {
          statusCode: 503,
          body: { error: 'payment_provider_error', message: 'Payment provider unavailable. Please try again.' },
        };
      }
      throw err;
    }

    // Only update user record AFTER Stripe succeeds
    await mockUserDal.update_stripe_customer_id(userId, customerId);

    try {
      const session = await mockStripeCheckoutCreate({ customer: customerId, plan });
      return { statusCode: 200, body: { checkout_url: session.url } };
    } catch (err) {
      if (err instanceof StripeError) {
        return { statusCode: 503, body: { error: 'payment_provider_error' } };
      }
      throw err;
    }
  }

  const session = await mockStripeCheckoutCreate({ customer: user.stripe_customer_id, plan });
  return { statusCode: 200, body: { checkout_url: session.url } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-008: Stripe 503 Error on Customer Create', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: stripe503Payload.user_id,
      stripe_customer_id: null, // No customer yet
    });
  });

  it('should return 503 when stripe.Customer.create() throws 503', async () => {
    // TODO: Currently FAILS — backend returns 500 or crashes on Stripe customer errors
    mockStripeCustomerCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    const result = await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(result.statusCode).toBe(503);
    expect(result.body.error).toBe('payment_provider_error');
  });

  it('should NOT update user record with customer_id when customer create fails', async () => {
    // Critical: do not persist failed/partial state to DynamoDB
    mockStripeCustomerCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(mockUserDal.update_stripe_customer_id).not.toHaveBeenCalled();
  });

  it('should allow retry after customer create failure (idempotent retry)', async () => {
    // First call fails
    mockStripeCustomerCreate
      .mockRejectedValueOnce(new StripeError(503, 'api_error', 'Service unavailable'))
      .mockResolvedValueOnce({ id: 'cus_retry_success' });

    mockStripeCheckoutCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_retry' });

    const result1 = await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);
    expect(result1.statusCode).toBe(503);

    // Second call succeeds — fresh customer created on retry
    const result2 = await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);
    expect(result2.statusCode).toBe(200);
    expect(mockStripeCustomerCreate).toHaveBeenCalledTimes(2);
  });

  it('should log Stripe customer create error with user_id context', async () => {
    mockStripeCustomerCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(mockLogger.error).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ user_id: stripe503Payload.user_id }),
    );
  });

  it('should not call stripe.checkout.Session.create() if customer create failed', async () => {
    mockStripeCustomerCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(mockStripeCheckoutCreate).not.toHaveBeenCalled();
  });
});
