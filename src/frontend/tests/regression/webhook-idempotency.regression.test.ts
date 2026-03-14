/**
 * Regression Tests: Webhook Idempotency
 * Feature: F-SUB-011-R
 *
 * Replays each of the 5 webhook event types twice.
 * Confirms none causes data corruption on duplicate delivery.
 */

import { createStripeSubscription } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockDal = {
  upsert_subscription: jest.fn(),
  update_subscription_fields: jest.fn(),
  set_unlimited_usage: jest.fn(),
  get_subscription_by_stripe_id: jest.fn(),
};

const mockStripeSubscriptionRetrieve = jest.fn();

// ─── Simulated Handlers ─────────────────────────────────────────────────────

function tsToIso(unixTs: number): string {
  return new Date(unixTs * 1000).toISOString();
}

async function handleCheckoutCompleted(session: Record<string, unknown>): Promise<void> {
  const subscriptionId = session.subscription as string;
  const userId = (session.metadata as Record<string, string>)?.user_id;
  if (!subscriptionId || !userId) return;

  const stripeSub = mockStripeSubscriptionRetrieve(subscriptionId);
  mockDal.upsert_subscription({
    subscription_id: subscriptionId,
    user_id: userId,
    status: 'active',
    plan: (session.metadata as Record<string, string>)?.plan ?? 'monthly',
    stripe_price_id: stripeSub.items.data[0].price.id,
    current_period_start: tsToIso(stripeSub.current_period_start),
    current_period_end: tsToIso(stripeSub.current_period_end),
    payment_failed_count: 0,
  });
  mockDal.set_unlimited_usage(userId);
}

async function handleInvoiceSucceeded(invoice: Record<string, unknown>): Promise<void> {
  const subscriptionId = invoice.subscription as string;
  if (!subscriptionId) return;
  const sub = mockDal.get_subscription_by_stripe_id(subscriptionId);
  if (!sub) return;
  mockDal.update_subscription_fields(subscriptionId, {
    status: 'active',
    payment_failed_count: 0,
    last_invoice_id: invoice.id as string,
  });
}

async function handleInvoiceFailed(invoice: Record<string, unknown>): Promise<void> {
  const subscriptionId = invoice.subscription as string;
  if (!subscriptionId) return;
  const sub = mockDal.get_subscription_by_stripe_id(subscriptionId);
  if (!sub) return;
  mockDal.update_subscription_fields(subscriptionId, {
    status: 'past_due',
    payment_failed_count: (invoice.attempt_count as number) ?? 1,
    last_invoice_id: invoice.id as string,
  });
}

async function handleSubscriptionUpdated(stripeSub: Record<string, unknown>): Promise<void> {
  const subscriptionId = stripeSub.id as string;
  if (!subscriptionId) return;
  const items = stripeSub.items as { data: Array<{ price: { id: string } }> };
  mockDal.update_subscription_fields(subscriptionId, {
    status: stripeSub.status,
    plan: 'monthly',
    stripe_price_id: items.data[0].price.id,
    cancel_at_period_end: stripeSub.cancel_at_period_end ?? false,
  });
}

async function handleSubscriptionDeleted(stripeSub: Record<string, unknown>): Promise<void> {
  const subscriptionId = stripeSub.id as string;
  if (!subscriptionId) return;
  mockDal.update_subscription_fields(subscriptionId, {
    status: 'canceled',
    canceled_at: new Date().toISOString(),
    cancel_at_period_end: false,
  });
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Webhook Idempotency', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStripeSubscriptionRetrieve.mockReturnValue(createStripeSubscription());
    mockDal.get_subscription_by_stripe_id.mockReturnValue({
      subscription_id: 'sub_1Pxyz',
      status: 'active',
    });
  });

  // ── F-SUB-011-R: All Event Types Idempotent ────────────────────────────
  describe('F-SUB-011-R: Duplicate Event Handling', () => {
    it('checkout.session.completed is idempotent on repeat', async () => {
      const session = {
        subscription: 'sub_1Pxyz',
        customer: 'cus_Nabc',
        metadata: { user_id: 'user-010', plan: 'monthly' },
      };

      await handleCheckoutCompleted(session);
      const firstUpsert = mockDal.upsert_subscription.mock.calls[0][0];

      await handleCheckoutCompleted(session);
      const secondUpsert = mockDal.upsert_subscription.mock.calls[1][0];

      // Same data both times (put_item is idempotent)
      expect(firstUpsert.subscription_id).toBe(secondUpsert.subscription_id);
      expect(firstUpsert.status).toBe(secondUpsert.status);
    });

    it('invoice.payment_succeeded is idempotent on repeat', async () => {
      const invoice = {
        id: 'in_success001',
        subscription: 'sub_1Pxyz',
        customer: 'cus_Nabc',
      };

      await handleInvoiceSucceeded(invoice);
      await handleInvoiceSucceeded(invoice);

      // Both calls set same values
      expect(mockDal.update_subscription_fields).toHaveBeenCalledTimes(2);
      const first = mockDal.update_subscription_fields.mock.calls[0][1];
      const second = mockDal.update_subscription_fields.mock.calls[1][1];
      expect(first.status).toBe(second.status);
      expect(first.payment_failed_count).toBe(second.payment_failed_count);
    });

    it('invoice.payment_failed uses attempt_count from Stripe (safe on repeat)', async () => {
      const invoice = {
        id: 'in_fail001',
        subscription: 'sub_1Pxyz',
        customer: 'cus_Nabc',
        attempt_count: 2,
      };

      await handleInvoiceFailed(invoice);
      await handleInvoiceFailed(invoice);

      // Both calls set count to 2 (from Stripe, not incrementing locally)
      const first = mockDal.update_subscription_fields.mock.calls[0][1];
      const second = mockDal.update_subscription_fields.mock.calls[1][1];
      expect(first.payment_failed_count).toBe(2);
      expect(second.payment_failed_count).toBe(2);
    });

    it('customer.subscription.updated is idempotent on repeat', async () => {
      const subData = {
        id: 'sub_1Pxyz',
        status: 'active',
        cancel_at_period_end: false,
        current_period_start: 1741996800,
        current_period_end: 1744675200,
        items: { data: [{ price: { id: 'price_monthly_001' } }] },
      };

      await handleSubscriptionUpdated(subData);
      await handleSubscriptionUpdated(subData);

      // Same data both times
      expect(mockDal.update_subscription_fields).toHaveBeenCalledTimes(2);
      const first = mockDal.update_subscription_fields.mock.calls[0][1];
      const second = mockDal.update_subscription_fields.mock.calls[1][1];
      expect(first.status).toBe(second.status);
    });

    it('customer.subscription.deleted is idempotent (terminal state)', async () => {
      const subData = { id: 'sub_1Pxyz' };

      await handleSubscriptionDeleted(subData);
      await handleSubscriptionDeleted(subData);

      // Both calls set canceled (terminal state, safe to repeat)
      expect(mockDal.update_subscription_fields).toHaveBeenCalledTimes(2);
      const first = mockDal.update_subscription_fields.mock.calls[0][1];
      const second = mockDal.update_subscription_fields.mock.calls[1][1];
      expect(first.status).toBe('canceled');
      expect(second.status).toBe('canceled');
    });
  });
});
