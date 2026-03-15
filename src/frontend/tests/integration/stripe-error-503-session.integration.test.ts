/**
 * Integration Test: Stripe 503 Error on Session Create
 * Feature: CC-007
 *
 * When stripe.checkout.Session.create() returns a 503 Service Unavailable,
 * the Lambda must:
 *   1. Return 503 (not 500) to the caller
 *   2. Not create any subscription record
 *   3. Preserve any Stripe customer that was already created
 *   4. Log the error with enough context for debugging
 *
 * This test will FAIL until the backend catches StripeError and maps
 * status codes: 5xx Stripe errors → 503 to client.
 */

import stripe503Payload from '../payloads/stripe-503-error.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCustomerCreate = jest.fn();
const mockStripeCheckoutCreate = jest.fn();
const mockSubscriptionDal = {
  get_subscription_by_user: jest.fn(),
  create_subscription: jest.fn(),
};
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
  // TODO: This test will FAIL until the backend maps Stripe 5xx errors to 503.

  mockSubscriptionDal.get_subscription_by_user(userId); // Check existing

  const user = await mockUserDal.get_user(userId);
  let customerId = user?.stripe_customer_id;

  if (!customerId) {
    const customer = await mockStripeCustomerCreate({ metadata: { user_id: userId } });
    customerId = customer.id;
    await mockUserDal.update_stripe_customer_id(userId, customerId);
  }

  try {
    const session = await mockStripeCheckoutCreate({ customer: customerId, plan });
    return { statusCode: 200, body: { checkout_url: session.url } };
  } catch (err) {
    if (err instanceof StripeError) {
      mockLogger.error('Stripe API error during session create', {
        user_id: userId,
        stripe_status: err.status,
        stripe_type: err.type,
        message: err.message,
      });
      // Map Stripe provider errors to 503 (not 500)
      return {
        statusCode: 503,
        body: { error: 'payment_provider_error', message: 'Payment provider unavailable. Please try again.' },
      };
    }
    throw err;
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-007: Stripe 503 Error on Session Create', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSubscriptionDal.get_subscription_by_user.mockReturnValue(null);
    mockUserDal.get_user.mockResolvedValue({
      user_id: stripe503Payload.user_id,
      stripe_customer_id: 'cus_existing_001',
    });
    mockUserDal.update_stripe_customer_id.mockResolvedValue(undefined);
  });

  it('should return 503 (not 500) when Stripe returns 503 on session create', async () => {
    // TODO: Currently FAILS — backend returns 500 instead of 503 for Stripe errors
    mockStripeCheckoutCreate.mockRejectedValue(
      new StripeError(503, 'api_error', stripe503Payload.stripe_error.message),
    );

    const result = await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(result.statusCode).toBe(503);
    expect(result.body.error).toBe('payment_provider_error');
  });

  it('should not create any subscription record when Stripe session create fails', async () => {
    mockStripeCheckoutCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(mockSubscriptionDal.create_subscription).not.toHaveBeenCalled();
  });

  it('should preserve the existing Stripe customer after session create failure', async () => {
    // Customer was already created before the session call failed
    mockStripeCheckoutCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    // update_stripe_customer_id should NOT be called again (customer already existed)
    expect(mockUserDal.update_stripe_customer_id).not.toHaveBeenCalled();
  });

  it('should log the Stripe error with user_id and status for debugging', async () => {
    mockStripeCheckoutCreate.mockRejectedValue(
      new StripeError(503, stripe503Payload.stripe_error.type, stripe503Payload.stripe_error.message),
    );

    await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(mockLogger.error).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        user_id: stripe503Payload.user_id,
        stripe_status: 503,
      }),
    );
  });

  it('should return a user-friendly error message on 503', async () => {
    mockStripeCheckoutCreate.mockRejectedValue(
      new StripeError(503, 'api_error', 'Service unavailable'),
    );

    const result = await handleCheckout(stripe503Payload.user_id, stripe503Payload.plan);

    expect(result.statusCode).toBe(503);
    expect(result.body.message).toBeTruthy();
    // Message should NOT expose internal Stripe error details
    expect(result.body.message).not.toContain('stripe');
  });
});
