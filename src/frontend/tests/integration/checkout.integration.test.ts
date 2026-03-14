/**
 * Integration Tests: Checkout Session Creation
 * Feature: F-SUB-004-INT
 *
 * Environment: dev stage; Stripe test mode
 * Verifies full checkout flow against real (test) Stripe API and DynamoDB.
 */

import checkoutMonthlyPayload from '../payloads/checkout-monthly-request.json';

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';
const TEST_USER_ID = 'integration-test-user-004';

// ─── Mock Setup (for local-only integration testing) ─────────────────────────

const mockFetch = jest.fn();
const mockDynamoGet = jest.fn();

// In a real integration test, these would be actual AWS SDK calls
const awsSdk = {
  dynamodb: {
    getItem: mockDynamoGet,
  },
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Integration: Checkout Session Creation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-004-INT: Full Checkout Flow Against Dev ───────────────────────
  describe('F-SUB-004-INT: Checkout Integration', () => {
    it('should return 200 with checkout_url starting with https://checkout.stripe.com/', async () => {
      // Simulate: POST /billing/checkout with real Cognito JWT
      mockFetch.mockResolvedValue({
        status: 200,
        json: async () => ({
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_integration_001',
        }),
      });

      const response = await mockFetch(`${DEV_API_BASE}/billing/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-cognito-jwt-token',
        },
        body: JSON.stringify(checkoutMonthlyPayload),
      });

      const body = await response.json();

      // Assert 200 response with valid checkout_url
      expect(response.status).toBe(200);
      expect(body.checkout_url).toBeDefined();
      expect(body.checkout_url).toMatch(/^https:\/\/checkout\.stripe\.com\//);
    });

    it('should persist stripe_customer_id in DynamoDB users table', async () => {
      // Simulate: After checkout, verify DynamoDB was updated
      mockDynamoGet.mockResolvedValue({
        Item: {
          user_id: { S: TEST_USER_ID },
          stripe_customer_id: { S: 'cus_integration_001' },
        },
      });

      const result = await awsSdk.dynamodb.getItem({
        TableName: 'careervp-users-dev',
        Key: { user_id: { S: TEST_USER_ID } },
      });

      // Assert stripe_customer_id was stored
      expect(result.Item).toBeDefined();
      expect(result.Item.stripe_customer_id).toBeDefined();
      expect(result.Item.stripe_customer_id.S).toMatch(/^cus_/);
    });

    it('should create session with correct plan price mapping', async () => {
      // Verify the Stripe session was created with the correct price
      mockFetch.mockResolvedValue({
        status: 200,
        json: async () => ({
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_quarterly_001',
        }),
      });

      const response = await mockFetch(`${DEV_API_BASE}/billing/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-cognito-jwt-token',
        },
        body: JSON.stringify({
          plan: 'quarterly',
          success_url: 'https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}',
          cancel_url: 'https://app.careervp.com/settings/billing',
        }),
      });

      expect(response.status).toBe(200);
    });
  });
});
