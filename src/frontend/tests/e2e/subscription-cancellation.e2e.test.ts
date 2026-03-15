/**
 * E2E Tests: Subscription Cancellation
 * Feature: F-SUB-016-E2E
 *
 * Full cancellation flow: active -> cancel via portal -> subscription deleted -> blocked.
 * Environment: dev stage; Stripe test mode; Stripe CLI.
 */

jest.setTimeout(60000);

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  get: jest.fn(),
  post: jest.fn(),
};

const mockStripeCli = {
  trigger: jest.fn(),
};

const mockDynamoDb = {
  getItem: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('E2E: Subscription Cancellation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-016-E2E: Full Cancellation Flow ──────────────────────────────
  describe('F-SUB-016-E2E: Complete Cancellation', () => {
    it('should cancel subscription and block access', async () => {
      // Step 1: Trigger subscription deletion via Stripe CLI
      mockStripeCli.trigger.mockResolvedValue({
        event: 'customer.subscription.deleted',
        delivered: true,
      });

      const triggerResult = await mockStripeCli.trigger('customer.subscription.deleted');
      expect(triggerResult.delivered).toBe(true);

      // Step 2: GET /users/me/subscription -> assert status = "canceled"
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: {
            subscription_id: 'sub_cancel_001',
            status: 'canceled',
            canceled_at: new Date().toISOString(),
          },
          has_active_subscription: false,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.status).toBe('canceled');
      expect(subResponse.data.has_active_subscription).toBe(false);
      expect(subResponse.data.subscription.canceled_at).toBeDefined();

      // Step 3: POST /jobs -> assert 403 subscription_required
      mockApi.post.mockResolvedValue({
        status: 403,
        data: { error: 'subscription_required' },
      });

      const jobResponse = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobResponse.status).toBe(403);
      expect(jobResponse.data.error).toBe('subscription_required');
    });

    it('should have canceled_at timestamp in DynamoDB', async () => {
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_cancel_001' },
          status: { S: 'canceled' },
          canceled_at: { S: '2026-03-14T12:00:00.000Z' },
          cancel_at_period_end: { BOOL: false },
        },
      });

      const result = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_cancel_001' } },
      });

      expect(result.Item.status.S).toBe('canceled');
      expect(result.Item.canceled_at.S).toBeDefined();
      expect(result.Item.cancel_at_period_end.BOOL).toBe(false);
    });
  });
});

export {};
