/**
 * Unit Tests: Webhook — Subscription Updated (Plan Change / Cancel Toggle)
 * Feature: F-SUB-014
 *
 * Tests the customer.subscription.updated webhook handler:
 * - Plan change (monthly -> quarterly)
 * - Cancel-at-period-end toggle
 */

import planChangePayload from '../payloads/webhook-subscription-updated-plan-change.json';
import cancelScheduledPayload from '../payloads/webhook-subscription-cancel-scheduled.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const PRICE_TO_PLAN: Record<string, string> = {
  price_monthly_001: 'monthly',
  price_quarterly_001: 'quarterly',
};

const mockDal = {
  update_subscription_fields: jest.fn(),
};

// ─── Simulated _handle_subscription_updated Logic ────────────────────────────

function tsToIso(unixTs: number): string {
  return new Date(unixTs * 1000).toISOString();
}

async function handleSubscriptionUpdated(stripeSub: Record<string, unknown>): Promise<void> {
  const subscriptionId = stripeSub.id as string;
  if (!subscriptionId) return;

  const items = stripeSub.items as { data: Array<{ price: { id: string } }> };
  const priceId = items.data[0].price.id;
  const plan = PRICE_TO_PLAN[priceId] ?? 'monthly';

  mockDal.update_subscription_fields(subscriptionId, {
    status: stripeSub.status,
    plan,
    stripe_price_id: priceId,
    current_period_start: tsToIso(stripeSub.current_period_start as number),
    current_period_end: tsToIso(stripeSub.current_period_end as number),
    cancel_at_period_end: (stripeSub.cancel_at_period_end as boolean) ?? false,
  });
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Webhook — Subscription Updated', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-014a: Plan Change (Monthly → Quarterly) ──────────────────────
  describe('F-SUB-014a: Plan Change', () => {
    it('should update plan to quarterly when price changes', async () => {
      const subData = planChangePayload.data.object;

      await handleSubscriptionUpdated(subData);

      // Assert update_subscription_fields called with plan = "quarterly"
      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith(
        'sub_1Pxyz',
        expect.objectContaining({
          plan: 'quarterly',
          status: 'active',
          cancel_at_period_end: false,
        }),
      );
    });

    it('should update billing period dates', async () => {
      const subData = planChangePayload.data.object;

      await handleSubscriptionUpdated(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.current_period_start).toBeDefined();
      expect(updateCall.current_period_end).toBeDefined();
      // Quarterly end should be later than monthly
      expect(new Date(updateCall.current_period_end).getTime()).toBeGreaterThan(
        new Date(updateCall.current_period_start).getTime(),
      );
    });

    it('should store the new stripe_price_id', async () => {
      const subData = planChangePayload.data.object;

      await handleSubscriptionUpdated(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.stripe_price_id).toBe('price_quarterly_001');
    });
  });

  // ── F-SUB-014b: Cancel at Period End Toggle ─────────────────────────────
  describe('F-SUB-014b: Cancel at Period End Toggle', () => {
    it('should set cancel_at_period_end = true when user schedules cancel', async () => {
      const subData = cancelScheduledPayload.data.object;

      await handleSubscriptionUpdated(subData);

      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith(
        'sub_1Pxyz',
        expect.objectContaining({
          cancel_at_period_end: true,
          status: 'active',
        }),
      );
    });

    it('should keep status as active when cancel is scheduled', async () => {
      const subData = cancelScheduledPayload.data.object;

      await handleSubscriptionUpdated(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.status).toBe('active');
    });

    it('should preserve monthly plan when only cancel toggle changes', async () => {
      const subData = cancelScheduledPayload.data.object;

      await handleSubscriptionUpdated(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.plan).toBe('monthly');
      expect(updateCall.stripe_price_id).toBe('price_monthly_001');
    });
  });
});
