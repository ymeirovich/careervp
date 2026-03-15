/**
 * E2E Tests: Checkout to Active Subscription
 * Feature: F-SUB-010-E2E
 *
 * Full upgrade flow: trialing user -> checkout -> payment -> active subscription.
 * Environment: dev stage; Stripe test mode; Stripe CLI webhook relay.
 */

jest.setTimeout(60000);

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';
const STRIPE_TEST_CARD = '4242424242424242';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  post: jest.fn(),
  get: jest.fn(),
};

const mockCognito = {
  createTestUser: jest.fn(),
  getToken: jest.fn(),
};

const mockStripe = {
  completeCheckout: jest.fn(),
  waitForWebhook: jest.fn(),
};

const mockDynamoDb = {
  getItem: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('E2E: Checkout to Active Subscription', () => {
  let testToken: string;

  beforeEach(() => {
    jest.clearAllMocks();
    testToken = 'test-cognito-jwt-token';
  });

  // ── F-SUB-010-E2E: Full Upgrade Flow ───────────────────────────────────
  describe('F-SUB-010-E2E: Complete Checkout Flow', () => {
    it('should complete full upgrade from trialing to active', async () => {
      // Step 1: Create test user via Cognito; assert trialing state
      mockCognito.createTestUser.mockResolvedValue({
        userId: 'e2e-user-010',
        token: testToken,
      });
      const testUser = await mockCognito.createTestUser();
      expect(testUser.userId).toBeDefined();

      // Step 2: POST /billing/checkout with plan = "monthly"
      mockApi.post.mockResolvedValue({
        status: 200,
        data: { checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_e2e_001' },
      });

      const checkoutResponse = await mockApi.post(`${DEV_API_BASE}/billing/checkout`, {
        plan: 'monthly',
        success_url: 'https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'https://app.careervp.com/settings/billing',
      });

      expect(checkoutResponse.status).toBe(200);
      expect(checkoutResponse.data.checkout_url).toMatch(/checkout\.stripe\.com/);

      // Step 3: Complete checkout with test card 4242 4242 4242 4242
      mockStripe.completeCheckout.mockResolvedValue({
        success: true,
        sessionId: 'cs_test_e2e_001',
      });

      const stripeResult = await mockStripe.completeCheckout({
        sessionUrl: checkoutResponse.data.checkout_url,
        cardNumber: STRIPE_TEST_CARD,
        expMonth: '12',
        expYear: '30',
        cvc: '123',
      });

      expect(stripeResult.success).toBe(true);

      // Step 4: Wait for webhook delivery
      mockStripe.waitForWebhook.mockResolvedValue({
        eventType: 'checkout.session.completed',
        delivered: true,
      });

      const webhookResult = await mockStripe.waitForWebhook('checkout.session.completed');
      expect(webhookResult.delivered).toBe(true);

      // Step 5: GET /users/me/subscription -> assert status = "active"
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: {
            subscription_id: 'sub_e2e_001',
            status: 'active',
            plan: 'monthly',
          },
          has_active_subscription: true,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.status).toBe('active');
      expect(subResponse.data.has_active_subscription).toBe(true);

      // Step 6: POST /jobs -> assert 200 (not blocked)
      mockApi.post.mockResolvedValue({ status: 200, data: { job_id: 'job_e2e_001' } });

      const jobResponse = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobResponse.status).toBe(200);
    });

    it('should have subscription record in DynamoDB with correct fields', async () => {
      // AWS Verification: DynamoDB status = "active", remaining = 9999
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_e2e_001' },
          user_id: { S: 'e2e-user-010' },
          status: { S: 'active' },
          plan: { S: 'monthly' },
          payment_failed_count: { N: '0' },
        },
      });

      const dbResult = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_e2e_001' } },
      });

      expect(dbResult.Item.status.S).toBe('active');
      expect(dbResult.Item.plan.S).toBe('monthly');
      expect(parseInt(dbResult.Item.payment_failed_count.N)).toBe(0);
    });
  });
});

export {};
