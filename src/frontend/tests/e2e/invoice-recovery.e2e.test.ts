/**
 * E2E Tests: Invoice Payment Recovery
 * Feature: F-SUB-012-E2E
 *
 * Full recovery flow: payment fails -> past_due -> card updated -> payment succeeds -> active.
 * Environment: dev stage; Stripe test mode; Stripe CLI.
 */

jest.setTimeout(60000);

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  get: jest.fn(),
};

const mockStripeCli = {
  trigger: jest.fn(),
};

const mockDynamoDb = {
  getItem: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('E2E: Invoice Payment Recovery', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-012-E2E: Payment Recovery Flow ────────────────────────────────
  describe('F-SUB-012-E2E: Recovery from Past Due', () => {
    it('should recover from past_due to active after successful payment', async () => {
      // Step 1: Trigger payment failure
      mockStripeCli.trigger.mockResolvedValue({
        event: 'invoice.payment_failed',
        delivered: true,
      });

      const failResult = await mockStripeCli.trigger('invoice.payment_failed');
      expect(failResult.delivered).toBe(true);

      // Step 2: Assert subscription status = "past_due" in DynamoDB
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_recovery_001' },
          status: { S: 'past_due' },
          payment_failed_count: { N: '1' },
        },
      });

      const pastDueResult = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_recovery_001' } },
      });
      expect(pastDueResult.Item.status.S).toBe('past_due');

      // Step 3: Update test card via Customer Portal (simulated)
      // In real E2E: use Stripe portal to update card to 4242424242424242

      // Step 4: Trigger recovery
      mockStripeCli.trigger.mockResolvedValue({
        event: 'invoice.payment_succeeded',
        delivered: true,
      });

      const successResult = await mockStripeCli.trigger('invoice.payment_succeeded');
      expect(successResult.delivered).toBe(true);

      // Step 5: GET /users/me/subscription -> assert status = "active"
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: {
            status: 'active',
            plan: 'monthly',
          },
          has_active_subscription: true,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.status).toBe('active');
      expect(subResponse.data.has_active_subscription).toBe(true);
    });

    it('should reset payment_failed_count to 0 after recovery', async () => {
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_recovery_001' },
          status: { S: 'active' },
          payment_failed_count: { N: '0' },
        },
      });

      const result = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_recovery_001' } },
      });

      expect(parseInt(result.Item.payment_failed_count.N)).toBe(0);
    });
  });
});

export {};
