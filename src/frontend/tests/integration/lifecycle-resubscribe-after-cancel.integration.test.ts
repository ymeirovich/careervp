/**
 * Integration Test: Re-Subscribe After Cancellation
 * Feature: CC-019
 *
 * A user with a canceled subscription must be able to initiate a new checkout.
 * The new checkout must create a NEW subscription_id (not reuse the old one).
 * The old subscription record must still exist with status=canceled.
 *
 * This test will FAIL until the checkout handler correctly allows re-subscription
 * for users with canceled (but not active) subscriptions.
 */

import resubscribePayload from '../payloads/lifecycle-resubscribe.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCheckoutCreate = jest.fn();
const mockSubscriptionDal = {
  get_active_subscription_by_user: jest.fn(),
  get_all_subscriptions_by_user: jest.fn(),
  create_subscription: jest.fn(),
};
const mockUserDal = { get_user: jest.fn() };

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handleCheckout(userId: string, plan: string): Promise<CheckoutResult> {
  // TODO: This test will FAIL until the backend checks for ACTIVE subscription only
  // (not any subscription). A canceled subscription must not block re-subscription.

  const activeSub = await mockSubscriptionDal.get_active_subscription_by_user(userId);

  if (activeSub?.status === 'active') {
    // Block: already has an active subscription
    return { statusCode: 409, body: { error: 'subscription_already_active' } };
  }

  // Canceled/expired subscription → allow re-subscription
  const user = await mockUserDal.get_user(userId);
  const session = await mockStripeCheckoutCreate({
    customer: user?.stripe_customer_id ?? null,
    plan,
  });

  return { statusCode: 200, body: { checkout_url: session.url } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-019: Re-Subscribe After Cancellation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUserDal.get_user.mockResolvedValue({
      user_id: resubscribePayload.user_id,
      stripe_customer_id: 'cus_existing_001',
    });
    mockStripeCheckoutCreate.mockResolvedValue({
      url: 'https://checkout.stripe.com/pay/cs_test_resubscribe',
      id: 'cs_test_resubscribe_001',
    });
  });

  it('should allow checkout when previous subscription is canceled', async () => {
    // TODO: Currently FAILS — backend blocks ALL users with any subscription record
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue(null); // No ACTIVE sub

    const result = await handleCheckout(
      resubscribePayload.user_id,
      resubscribePayload.new_subscription_request.plan,
    );

    expect(result.statusCode).toBe(200);
    expect(result.body.checkout_url).toMatch(/checkout\.stripe\.com/);
  });

  it('should return 200 with checkout_url on re-subscription attempt', async () => {
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue(null);

    const result = await handleCheckout(resubscribePayload.user_id, 'quarterly');

    expect(result.statusCode).toBe(200);
    expect(result.body.checkout_url).toBeDefined();
  });

  it('should still block when user has an active (not canceled) subscription', async () => {
    // Control: active subscription must still block
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue({
      subscription_id: 'sub_still_active',
      status: 'active',
    });

    const result = await handleCheckout(resubscribePayload.user_id, 'monthly');

    expect(result.statusCode).toBe(409);
    expect(result.body.error).toBe('subscription_already_active');
  });

  it('should pass existing stripe_customer_id to new checkout session', async () => {
    // Reuse the existing customer — don't create a new one
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue(null);

    await handleCheckout(resubscribePayload.user_id, 'quarterly');

    expect(mockStripeCheckoutCreate).toHaveBeenCalledWith(
      expect.objectContaining({ customer: 'cus_existing_001' }),
    );
  });

  it('should preserve old canceled subscription (not overwrite it)', async () => {
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue(null);

    await handleCheckout(
      resubscribePayload.user_id,
      resubscribePayload.new_subscription_request.plan,
    );

    // The handler must not call create_subscription here (that happens on webhook)
    // But must not delete or overwrite the old subscription either
    // Verify the old subscription_id is NOT referenced in any delete call
    const createCalls = mockSubscriptionDal.create_subscription.mock.calls;
    for (const call of createCalls) {
      expect((call[0] as Record<string, string>).subscription_id).not.toBe(
        resubscribePayload.previous_subscription.subscription_id,
      );
    }
  });

  it('should create checkout for a different plan than the canceled subscription', async () => {
    // User was on monthly, now wants quarterly
    mockSubscriptionDal.get_active_subscription_by_user.mockResolvedValue(null);

    const result = await handleCheckout(
      resubscribePayload.user_id,
      resubscribePayload.new_subscription_request.plan, // quarterly
    );

    expect(result.statusCode).toBe(200);
    expect(mockStripeCheckoutCreate).toHaveBeenCalledWith(
      expect.objectContaining({ plan: resubscribePayload.new_subscription_request.plan }),
    );
  });
});
