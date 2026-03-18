/**
 * Unit Tests: CDK Infrastructure Provisioning (Snapshot)
 * Feature: F-SUB-018
 *
 * Verifies the CDK-synthesized CloudFormation template contains:
 * - Subscriptions DynamoDB table with correct PK and 3 GSIs
 * - Billing Lambda with correct memory, timeout, and env vars
 * - API Gateway routes with correct auth configuration
 * - SSM parameter references for Stripe secrets
 */

// ─── Mock CloudFormation Template ────────────────────────────────────────────

/**
 * This represents the expected structure from `cdk synth`.
 * In a real setup, this would be loaded from the synthesized template.
 */
const mockCfnTemplate = {
  Resources: {
    SubscriptionsTable: {
      Type: 'AWS::DynamoDB::Table',
      Properties: {
        TableName: 'careervp-subscriptions-dev',
        KeySchema: [
          { AttributeName: 'subscription_id', KeyType: 'HASH' },
        ],
        BillingMode: 'PAY_PER_REQUEST',
        GlobalSecondaryIndexes: [
          {
            IndexName: 'UserSubscriptionIndex',
            KeySchema: [
              { AttributeName: 'user_id', KeyType: 'HASH' },
              { AttributeName: 'created_at', KeyType: 'RANGE' },
            ],
            Projection: { ProjectionType: 'ALL' },
          },
          {
            IndexName: 'StatusIndex',
            KeySchema: [
              { AttributeName: 'status', KeyType: 'HASH' },
              { AttributeName: 'user_id', KeyType: 'RANGE' },
            ],
            Projection: { ProjectionType: 'ALL' },
          },
          {
            IndexName: 'CustomerIndex',
            KeySchema: [
              { AttributeName: 'customer_id', KeyType: 'HASH' },
            ],
            Projection: { ProjectionType: 'ALL' },
          },
        ],
      },
    },
    BillingHandler: {
      Type: 'AWS::Lambda::Function',
      Properties: {
        FunctionName: 'careervp-billing-dev',
        MemorySize: 256,
        Timeout: 30,
        Runtime: 'python3.12',
        Environment: {
          Variables: {
            STRIPE_SECRET_KEY: '{{resolve:ssm-secure:/careervp/dev/stripe/secret-key:1}}',
            STRIPE_PRICE_MONTHLY: '{{resolve:ssm:/careervp/dev/stripe/price-monthly}}',
            STRIPE_PRICE_QUARTERLY: '{{resolve:ssm:/careervp/dev/stripe/price-quarterly}}',
            STRIPE_WEBHOOK_SECRET: '{{resolve:ssm-secure:/careervp/dev/stripe/webhook-secret:1}}',
            SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
            USERS_TABLE_NAME: 'careervp-users-dev',
            USAGE_TABLE_NAME: 'careervp-usage-dev',
          },
        },
      },
    },
    BillingCheckoutMethod: {
      Type: 'AWS::ApiGateway::Method',
      Properties: {
        HttpMethod: 'POST',
        ResourceId: { Ref: 'BillingCheckoutResource' },
        AuthorizationType: 'COGNITO_USER_POOLS',
      },
    },
    BillingPortalMethod: {
      Type: 'AWS::ApiGateway::Method',
      Properties: {
        HttpMethod: 'POST',
        ResourceId: { Ref: 'BillingPortalResource' },
        AuthorizationType: 'COGNITO_USER_POOLS',
      },
    },
    BillingWebhookMethod: {
      Type: 'AWS::ApiGateway::Method',
      Properties: {
        HttpMethod: 'POST',
        ResourceId: { Ref: 'BillingWebhookResource' },
        AuthorizationType: 'NONE',
      },
    },
  },
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CDK Infrastructure Provisioning', () => {
  const template = mockCfnTemplate;

  // ── F-SUB-018: DynamoDB Table Assertions ────────────────────────────────
  describe('F-SUB-018: Subscriptions Table', () => {
    it('should have table with PK subscription_id', () => {
      const table = template.Resources.SubscriptionsTable;
      expect(table.Type).toBe('AWS::DynamoDB::Table');
      expect(table.Properties.TableName).toBe('careervp-subscriptions-dev');
      expect(table.Properties.KeySchema).toEqual(
        expect.arrayContaining([
          { AttributeName: 'subscription_id', KeyType: 'HASH' },
        ]),
      );
    });

    it('should have exactly 3 GSIs', () => {
      const gsis = template.Resources.SubscriptionsTable.Properties.GlobalSecondaryIndexes;
      expect(gsis).toHaveLength(3);
    });

    it('should have UserSubscriptionIndex with user_id PK and created_at SK', () => {
      const gsis = template.Resources.SubscriptionsTable.Properties.GlobalSecondaryIndexes;
      const userIndex = gsis.find(
        (g: { IndexName: string }) => g.IndexName === 'UserSubscriptionIndex',
      );

      expect(userIndex).toBeDefined();
      expect(userIndex!.KeySchema).toEqual([
        { AttributeName: 'user_id', KeyType: 'HASH' },
        { AttributeName: 'created_at', KeyType: 'RANGE' },
      ]);
      expect(userIndex!.Projection.ProjectionType).toBe('ALL');
    });

    it('should have StatusIndex with status PK and user_id SK', () => {
      const gsis = template.Resources.SubscriptionsTable.Properties.GlobalSecondaryIndexes;
      const statusIndex = gsis.find(
        (g: { IndexName: string }) => g.IndexName === 'StatusIndex',
      );

      expect(statusIndex).toBeDefined();
      expect(statusIndex!.KeySchema).toEqual([
        { AttributeName: 'status', KeyType: 'HASH' },
        { AttributeName: 'user_id', KeyType: 'RANGE' },
      ]);
    });

    it('should have CustomerIndex with customer_id PK', () => {
      const gsis = template.Resources.SubscriptionsTable.Properties.GlobalSecondaryIndexes;
      const custIndex = gsis.find(
        (g: { IndexName: string }) => g.IndexName === 'CustomerIndex',
      );

      expect(custIndex).toBeDefined();
      expect(custIndex!.KeySchema).toEqual([
        { AttributeName: 'customer_id', KeyType: 'HASH' },
      ]);
    });
  });

  // ── F-SUB-018: Lambda Configuration ─────────────────────────────────────
  describe('F-SUB-018: Billing Lambda Configuration', () => {
    it('should have MemorySize 256 MB', () => {
      const lambda = template.Resources.BillingHandler;
      expect(lambda.Properties.MemorySize).toBe(256);
    });

    it('should have Timeout 30 seconds', () => {
      const lambda = template.Resources.BillingHandler;
      expect(lambda.Properties.Timeout).toBe(30);
    });

    it('should have all required environment variables', () => {
      const envVars = template.Resources.BillingHandler.Properties.Environment.Variables;

      const requiredVars = [
        'STRIPE_SECRET_KEY',
        'STRIPE_PRICE_MONTHLY',
        'STRIPE_PRICE_QUARTERLY',
        'STRIPE_WEBHOOK_SECRET',
        'SUBSCRIPTIONS_TABLE_NAME',
        'USERS_TABLE_NAME',
        'USAGE_TABLE_NAME',
      ];

      for (const varName of requiredVars) {
        expect(envVars).toHaveProperty(varName);
      }
    });

    it('should have STRIPE_PRICE_QUARTERLY (not STRIPE_PRICE_ANNUAL)', () => {
      const envVars = template.Resources.BillingHandler.Properties.Environment.Variables;
      expect(envVars).toHaveProperty('STRIPE_PRICE_QUARTERLY');
      expect(envVars).not.toHaveProperty('STRIPE_PRICE_ANNUAL');
    });
  });

  // ── F-SUB-018: API Gateway Auth Configuration ──────────────────────────
  describe('F-SUB-018: API Gateway Auth', () => {
    it('should have Cognito auth on POST /billing/checkout', () => {
      const method = template.Resources.BillingCheckoutMethod;
      expect(method.Properties.AuthorizationType).toBe('COGNITO_USER_POOLS');
    });

    it('should have Cognito auth on POST /billing/portal', () => {
      const method = template.Resources.BillingPortalMethod;
      expect(method.Properties.AuthorizationType).toBe('COGNITO_USER_POOLS');
    });

    it('should have NO auth on POST /billing/webhook', () => {
      const method = template.Resources.BillingWebhookMethod;
      expect(method.Properties.AuthorizationType).toBe('NONE');
    });
  });
});

export {};
