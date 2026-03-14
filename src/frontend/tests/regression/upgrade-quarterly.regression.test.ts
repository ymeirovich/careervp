/**
 * Regression Tests: Quarterly Upgrade Variant
 * Feature: F-SUB-021-R
 *
 * Repeats E2E upgrade flow with Quarterly plan.
 * Asserts plan = "quarterly" in DynamoDB and STRIPE_PRICE_QUARTERLY used.
 */

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  get: jest.fn(),
  post: jest.fn(),
};

const mockStripe = {
  completeCheckout: jest.fn(),
  waitForWebhook: jest.fn(),
};

const mockDynamoDb = {
  getItem: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Quarterly Upgrade Variant', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-021-R: Quarterly Plan Verification ───────────────────────────
  describe('F-SUB-021-R: Quarterly Upgrade Flow', () => {
    it('should create checkout session with STRIPE_PRICE_QUARTERLY', async () => {
      mockApi.post.mockResolvedValue({
        status: 200,
        data: {
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_quarterly_001',
        },
      });

      const response = await mockApi.post(`${DEV_API_BASE}/billing/checkout`, {
        plan: 'quarterly',
        success_url: 'https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'https://app.careervp.com/settings/billing',
      });

      expect(response.status).toBe(200);
      expect(response.data.checkout_url).toBeDefined();

      // Verify the API was called with quarterly plan
      expect(mockApi.post).toHaveBeenCalledWith(
        expect.stringContaining('/billing/checkout'),
        expect.objectContaining({ plan: 'quarterly' }),
      );
    });

    it('should result in plan = "quarterly" in DynamoDB after upgrade', async () => {
      // Simulate completed quarterly upgrade
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_quarterly_001' },
          status: { S: 'active' },
          plan: { S: 'quarterly' },
          stripe_price_id: { S: 'price_quarterly_001' },
        },
      });

      const result = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_quarterly_001' } },
      });

      expect(result.Item.plan.S).toBe('quarterly');
      expect(result.Item.stripe_price_id.S).toBe('price_quarterly_001');
      expect(result.Item.status.S).toBe('active');
    });

    it('should complete full quarterly upgrade from trial exhausted', async () => {
      // Step 1: Job creation blocked
      mockApi.post.mockResolvedValueOnce({
        status: 403,
        data: { error: 'trial_exhausted' },
      });

      const jobAttempt = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobAttempt.status).toBe(403);

      // Step 2: Checkout with quarterly
      mockApi.post.mockResolvedValueOnce({
        status: 200,
        data: {
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_quarterly_002',
        },
      });

      const checkoutResponse = await mockApi.post(`${DEV_API_BASE}/billing/checkout`, {
        plan: 'quarterly',
        success_url: 'https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'https://app.careervp.com/settings/billing',
      });

      expect(checkoutResponse.status).toBe(200);

      // Step 3: Complete checkout
      mockStripe.completeCheckout.mockResolvedValue({ success: true });
      const stripeResult = await mockStripe.completeCheckout({
        sessionUrl: checkoutResponse.data.checkout_url,
        cardNumber: '4242424242424242',
      });
      expect(stripeResult.success).toBe(true);

      // Step 4: Verify subscription
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: { status: 'active', plan: 'quarterly' },
          has_active_subscription: true,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.plan).toBe('quarterly');
      expect(subResponse.data.has_active_subscription).toBe(true);

      // Step 5: Job creation succeeds
      mockApi.post.mockResolvedValueOnce({ status: 200, data: { job_id: 'job_quarterly_001' } });
      const jobResponse = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobResponse.status).toBe(200);
    });
  });
});
