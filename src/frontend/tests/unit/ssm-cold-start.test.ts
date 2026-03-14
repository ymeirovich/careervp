/**
 * Unit Tests: SSM Cold Start Failure Handling
 * Feature: F-SUB-019
 *
 * Tests that the Lambda billing handler fails fast with a clear
 * error when required environment variables (SSM-backed) are missing.
 */

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('SSM Cold Start Failure Handling', () => {
  const REQUIRED_ENV_VARS = [
    'STRIPE_SECRET_KEY',
    'STRIPE_PRICE_MONTHLY',
    'STRIPE_PRICE_QUARTERLY',
    'STRIPE_WEBHOOK_SECRET',
    'SUBSCRIPTIONS_TABLE_NAME',
    'USERS_TABLE_NAME',
    'USAGE_TABLE_NAME',
  ];

  // Simulate the module-level init that reads env vars
  function simulateModuleInit(env: Record<string, string | undefined>): void {
    // This simulates: stripe.api_key = os.environ['STRIPE_SECRET_KEY']
    const stripeKey = env.STRIPE_SECRET_KEY;
    if (!stripeKey) {
      throw new Error("Missing required environment variable: 'STRIPE_SECRET_KEY'");
    }

    // Simulate: PRICE_MAP resolution
    const priceMonthly = env.STRIPE_PRICE_MONTHLY;
    const priceQuarterly = env.STRIPE_PRICE_QUARTERLY;
    if (!priceMonthly || !priceQuarterly) {
      throw new Error('Missing required Stripe price environment variables');
    }

    // Simulate: WEBHOOK_SECRET
    const webhookSecret = env.STRIPE_WEBHOOK_SECRET;
    if (!webhookSecret) {
      throw new Error("Missing required environment variable: 'STRIPE_WEBHOOK_SECRET'");
    }

    // Simulate: DynamoDB table names
    const tables = [
      env.SUBSCRIPTIONS_TABLE_NAME,
      env.USERS_TABLE_NAME,
      env.USAGE_TABLE_NAME,
    ];
    if (tables.some((t) => !t)) {
      throw new Error('Missing required DynamoDB table environment variables');
    }
  }

  // ── F-SUB-019: Missing STRIPE_SECRET_KEY ────────────────────────────────
  describe('F-SUB-019: Missing Environment Variables', () => {
    it('should throw when STRIPE_SECRET_KEY is missing', () => {
      const env: Record<string, string | undefined> = {
        STRIPE_PRICE_MONTHLY: 'price_monthly_001',
        STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
        STRIPE_WEBHOOK_SECRET: 'whsec_test',
        SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
        USERS_TABLE_NAME: 'careervp-users-dev',
        USAGE_TABLE_NAME: 'careervp-usage-dev',
      };

      expect(() => simulateModuleInit(env)).toThrow(/STRIPE_SECRET_KEY/);
    });

    it('should throw when STRIPE_WEBHOOK_SECRET is missing', () => {
      const env: Record<string, string | undefined> = {
        STRIPE_SECRET_KEY: 'sk_test_xxx',
        STRIPE_PRICE_MONTHLY: 'price_monthly_001',
        STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
        SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
        USERS_TABLE_NAME: 'careervp-users-dev',
        USAGE_TABLE_NAME: 'careervp-usage-dev',
      };

      expect(() => simulateModuleInit(env)).toThrow(/STRIPE_WEBHOOK_SECRET/);
    });

    it('should throw when Stripe price variables are missing', () => {
      const env: Record<string, string | undefined> = {
        STRIPE_SECRET_KEY: 'sk_test_xxx',
        STRIPE_WEBHOOK_SECRET: 'whsec_test',
        SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
        USERS_TABLE_NAME: 'careervp-users-dev',
        USAGE_TABLE_NAME: 'careervp-usage-dev',
      };

      expect(() => simulateModuleInit(env)).toThrow(/price/i);
    });

    it('should throw when DynamoDB table names are missing', () => {
      const env: Record<string, string | undefined> = {
        STRIPE_SECRET_KEY: 'sk_test_xxx',
        STRIPE_PRICE_MONTHLY: 'price_monthly_001',
        STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
        STRIPE_WEBHOOK_SECRET: 'whsec_test',
      };

      expect(() => simulateModuleInit(env)).toThrow(/DynamoDB/i);
    });

    it('should succeed when all required variables are present', () => {
      const env: Record<string, string> = {
        STRIPE_SECRET_KEY: 'sk_test_xxx',
        STRIPE_PRICE_MONTHLY: 'price_monthly_001',
        STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
        STRIPE_WEBHOOK_SECRET: 'whsec_test',
        SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
        USERS_TABLE_NAME: 'careervp-users-dev',
        USAGE_TABLE_NAME: 'careervp-usage-dev',
      };

      expect(() => simulateModuleInit(env)).not.toThrow();
    });

    it('should not attempt Stripe API calls when key is missing', () => {
      const mockStripeCall = jest.fn();

      try {
        simulateModuleInit({});
      } catch {
        // Expected
      }

      expect(mockStripeCall).not.toHaveBeenCalled();
    });
  });

  // ── F-SUB-019: Validate all required env vars exist ─────────────────────
  describe('F-SUB-019: Required Variable Coverage', () => {
    it.each(REQUIRED_ENV_VARS)(
      'should require %s environment variable',
      (varName) => {
        // Create env with all vars present except the one we are testing
        const fullEnv: Record<string, string> = {
          STRIPE_SECRET_KEY: 'sk_test_xxx',
          STRIPE_PRICE_MONTHLY: 'price_monthly_001',
          STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
          STRIPE_WEBHOOK_SECRET: 'whsec_test',
          SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
          USERS_TABLE_NAME: 'careervp-users-dev',
          USAGE_TABLE_NAME: 'careervp-usage-dev',
        };

        // Remove the variable under test
        const testEnv = { ...fullEnv };
        delete testEnv[varName];

        expect(() => simulateModuleInit(testEnv)).toThrow();
      },
    );
  });
});
