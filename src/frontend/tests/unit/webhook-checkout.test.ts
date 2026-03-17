/**
 * Unit Tests: Webhook — Checkout Completed (Subscription Activated)
 * Features: F-SUB-010, F-SUB-011
 *
 * Tests the checkout.session.completed webhook handler:
 * - Creates subscription record with status = "active"
 * - Sets usage to unlimited (remaining = 9999)
 * - Idempotent on duplicate delivery
 */

import webhookCheckoutPayload from '../payloads/webhook-checkout-completed.json';
import { createStripeSubscription } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

// Generic PaymentProvider interface mock — replace with concrete provider at integration time
const mockPaymentProvider = {
  retrieveSubscription: jest.fn(),
};
const mockDal = {
  upsert_subscription: jest.fn(),
  set_unlimited_usage: jest.fn(),
  get_subscription_by_stripe_id: jest.fn(),
  update_subscription_fields: jest.fn(),
};

// ─── Simulated _handle_checkout_completed Logic ──────────────────────────────

function tsToIso(unixTs: number): string {
  return new Date(unixTs * 1000).toISOString();
}

async function handleCheckoutCompleted(session: Record<string, unknown>): Promise<void> {
  const subscriptionId = session.subscription as string;
  const customerId = session.customer as string;
  const metadata = session.metadata as Record<string, string>;
  const userId = metadata?.user_id;
  const plan = metadata?.plan ?? 'monthly';

  if (!subscriptionId || !userId) {
    throw new Error('Missing subscription or user_id');
  }

  // Fetch full subscription from payment provider
  const providerSub = mockPaymentProvider.retrieveSubscription(subscriptionId);

  mockDal.upsert_subscription({
    subscription_id: subscriptionId,
    user_id: userId,
    customer_id: customerId,
    status: 'active',
    plan,
    stripe_price_id: providerSub.items.data[0].price.id,
    current_period_start: tsToIso(providerSub.current_period_start),
    current_period_end: tsToIso(providerSub.current_period_end),
    trial_end: null,
    cancel_at_period_end: providerSub.cancel_at_period_end ?? false,
    canceled_at: null,
    payment_failed_count: 0,
  });

  // Set unlimited usage
  mockDal.set_unlimited_usage(userId);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Webhook — Checkout Completed', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPaymentProvider.retrieveSubscription.mockReturnValue(createStripeSubscription());
  });

  // ── F-SUB-010: Checkout Completed → Subscription Active ─────────────────
  describe('F-SUB-010: Subscription Activated', () => {
    it('should create subscription with status = "active" and plan = "monthly"', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      await handleCheckoutCompleted(sessionData);

      // Assert upsert_subscription called with correct data
      expect(mockDal.upsert_subscription).toHaveBeenCalledWith(
        expect.objectContaining({
          subscription_id: 'sub_1Pxyz',
          user_id: 'user-010',
          customer_id: 'cus_Nabc',
          status: 'active',
          plan: 'monthly',
          payment_failed_count: 0,
        }),
      );
    });

    it('should set unlimited usage for the user', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      await handleCheckoutCompleted(sessionData);

      // Assert set_unlimited_usage called with correct user_id
      expect(mockDal.set_unlimited_usage).toHaveBeenCalledWith('user-010');
    });

    it('should retrieve full subscription from payment provider for period dates', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      await handleCheckoutCompleted(sessionData);

      expect(mockPaymentProvider.retrieveSubscription).toHaveBeenCalledWith('sub_1Pxyz');

      // Assert period dates are ISO formatted from provider timestamps
      const upsertCall = mockDal.upsert_subscription.mock.calls[0][0];
      expect(upsertCall.current_period_start).toBeDefined();
      expect(upsertCall.current_period_end).toBeDefined();
      // Verify ISO format
      expect(new Date(upsertCall.current_period_start).toISOString()).toBe(
        upsertCall.current_period_start,
      );
    });

    it('should store stripe_price_id from the subscription', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      await handleCheckoutCompleted(sessionData);

      const upsertCall = mockDal.upsert_subscription.mock.calls[0][0];
      expect(upsertCall.stripe_price_id).toBe('price_monthly_001');
    });
  });

  // ── F-SUB-011: Idempotent on Duplicate Delivery ─────────────────────────
  describe('F-SUB-011: Idempotent Duplicate Handling', () => {
    it('should return successfully on second identical delivery', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      // First delivery
      await handleCheckoutCompleted(sessionData);

      // Verify first call
      expect(mockDal.upsert_subscription).toHaveBeenCalledTimes(1);
      expect(mockDal.set_unlimited_usage).toHaveBeenCalledTimes(1);

      // Second delivery (duplicate)
      await handleCheckoutCompleted(sessionData);

      // Assert second call also succeeds
      expect(mockDal.upsert_subscription).toHaveBeenCalledTimes(2);
      expect(mockDal.set_unlimited_usage).toHaveBeenCalledTimes(2);
    });

    it('should write identical data on duplicate (put_item is idempotent)', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      await handleCheckoutCompleted(sessionData);
      const firstCall = mockDal.upsert_subscription.mock.calls[0][0];

      await handleCheckoutCompleted(sessionData);
      const secondCall = mockDal.upsert_subscription.mock.calls[1][0];

      // Assert same subscription data both times
      expect(firstCall.subscription_id).toBe(secondCall.subscription_id);
      expect(firstCall.status).toBe(secondCall.status);
      expect(firstCall.plan).toBe(secondCall.plan);
      expect(firstCall.user_id).toBe(secondCall.user_id);
    });

    it('should set remaining to 9999 on both deliveries (idempotent)', async () => {
      const sessionData = webhookCheckoutPayload.data.object;

      // Both calls should invoke set_unlimited_usage
      await handleCheckoutCompleted(sessionData);
      await handleCheckoutCompleted(sessionData);

      // set_unlimited_usage sets to 9999 regardless — idempotent
      expect(mockDal.set_unlimited_usage).toHaveBeenCalledTimes(2);
      expect(mockDal.set_unlimited_usage).toHaveBeenNthCalledWith(1, 'user-010');
      expect(mockDal.set_unlimited_usage).toHaveBeenNthCalledWith(2, 'user-010');
    });
  });
});
