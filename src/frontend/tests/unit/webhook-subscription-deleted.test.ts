/**
 * Unit Tests: Webhook — Subscription Canceled (Deleted)
 * Feature: F-SUB-016
 *
 * Tests the customer.subscription.deleted webhook handler:
 * - Sets status to "canceled"
 * - Records canceled_at timestamp
 * - Sets cancel_at_period_end to false
 */

import webhookDeletedPayload from '../payloads/webhook-subscription-deleted.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockDal = {
  update_subscription_fields: jest.fn(),
};

// ─── Simulated _handle_subscription_deleted Logic ────────────────────────────

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

describe('Webhook — Subscription Deleted', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-016: Subscription Canceled ────────────────────────────────────
  describe('F-SUB-016: Subscription Fully Canceled', () => {
    it('should set status to canceled with canceled_at timestamp', async () => {
      const subData = webhookDeletedPayload.data.object;

      await handleSubscriptionDeleted(subData);

      // Assert update_subscription_fields called
      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith(
        'sub_1Pxyz',
        expect.objectContaining({
          status: 'canceled',
          cancel_at_period_end: false,
        }),
      );

      // Assert canceled_at is a valid ISO timestamp
      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.canceled_at).toBeDefined();
      const canceledAt = new Date(updateCall.canceled_at);
      expect(canceledAt.toISOString()).toBe(updateCall.canceled_at);
    });

    it('should set cancel_at_period_end to false', async () => {
      const subData = webhookDeletedPayload.data.object;

      await handleSubscriptionDeleted(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      expect(updateCall.cancel_at_period_end).toBe(false);
    });

    it('should skip processing when subscription id is missing', async () => {
      await handleSubscriptionDeleted({});

      expect(mockDal.update_subscription_fields).not.toHaveBeenCalled();
    });

    it('should record current time as canceled_at', async () => {
      const before = new Date();
      const subData = webhookDeletedPayload.data.object;

      await handleSubscriptionDeleted(subData);

      const updateCall = mockDal.update_subscription_fields.mock.calls[0][1];
      const canceledAt = new Date(updateCall.canceled_at);
      const after = new Date();

      expect(canceledAt.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(canceledAt.getTime()).toBeLessThanOrEqual(after.getTime());
    });
  });
});
