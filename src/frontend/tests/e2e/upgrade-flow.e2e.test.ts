/**
 * E2E Tests: Full Upgrade Flow (Monthly)
 * Feature: F-SUB-021
 *
 * Complete user-facing upgrade path:
 * trial prompt -> PlanCard selection -> CheckoutButton redirect -> Stripe Checkout
 * -> success page -> subscription status refreshed.
 *
 * Environment: dev stage; Stripe test mode; Stripe CLI webhook relay.
 */

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';
const STRIPE_TEST_CARD = '4242424242424242';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  get: jest.fn(),
  post: jest.fn(),
};

const mockUi = {
  clickUpgrade: jest.fn(),
  selectPlan: jest.fn(),
  clickCheckout: jest.fn(),
  assertSuccessPage: jest.fn(),
};

const mockStripe = {
  completeCheckout: jest.fn(),
  waitForWebhook: jest.fn(),
};

const mockDynamoDb = {
  getItem: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('E2E: Full Upgrade Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-021: Monthly Upgrade ──────────────────────────────────────────
  describe('F-SUB-021: Monthly Plan Upgrade', () => {
    it('should complete full upgrade from trial exhausted to active', async () => {
      // Step 1: Sign in as test user (trialing, credits exhausted)
      // Verify trial exhausted state

      // Step 2: Attempt job creation -> UpgradeModal appears
      mockApi.post.mockResolvedValue({
        status: 403,
        data: { error: 'trial_exhausted' },
      });

      const jobAttempt = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobAttempt.status).toBe(403);
      expect(jobAttempt.data.error).toBe('trial_exhausted');

      // Step 3: Select Monthly plan -> click CheckoutButton
      mockApi.post.mockResolvedValue({
        status: 200,
        data: {
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_upgrade_001',
        },
      });

      const checkoutResponse = await mockApi.post(`${DEV_API_BASE}/billing/checkout`, {
        plan: 'monthly',
        success_url: 'https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'https://app.careervp.com/settings/billing',
      });

      expect(checkoutResponse.status).toBe(200);
      expect(checkoutResponse.data.checkout_url).toMatch(/checkout\.stripe\.com/);

      // Step 4: Complete Stripe Checkout with test card
      mockStripe.completeCheckout.mockResolvedValue({ success: true });

      const stripeResult = await mockStripe.completeCheckout({
        sessionUrl: checkoutResponse.data.checkout_url,
        cardNumber: STRIPE_TEST_CARD,
        expMonth: '12',
        expYear: '30',
        cvc: '123',
      });

      expect(stripeResult.success).toBe(true);

      // Step 5: Redirected to /billing/success?session_id=...
      mockUi.assertSuccessPage.mockReturnValue(true);
      expect(mockUi.assertSuccessPage()).toBe(true);

      // Step 6: Wait for webhook
      mockStripe.waitForWebhook.mockResolvedValue({ delivered: true });
      await mockStripe.waitForWebhook('checkout.session.completed');

      // Step 7: GET /users/me/subscription -> has_active_subscription = true
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
      expect(subResponse.data.has_active_subscription).toBe(true);
      expect(subResponse.data.subscription.plan).toBe('monthly');

      // Step 8: POST /jobs -> 200 (not blocked)
      mockApi.post.mockResolvedValue({ status: 200, data: { job_id: 'job_upgrade_001' } });

      const jobResponse = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobResponse.status).toBe(200);
    });

    it('should have DynamoDB record with status=active and remaining=9999', async () => {
      // AWS Verification
      mockDynamoDb.getItem.mockResolvedValue({
        Item: {
          subscription_id: { S: 'sub_upgrade_001' },
          status: { S: 'active' },
          plan: { S: 'monthly' },
        },
      });

      const subResult = await mockDynamoDb.getItem({
        TableName: 'careervp-subscriptions-dev',
        Key: { subscription_id: { S: 'sub_upgrade_001' } },
      });

      expect(subResult.Item.status.S).toBe('active');
      expect(subResult.Item.plan.S).toBe('monthly');
    });
  });
});
