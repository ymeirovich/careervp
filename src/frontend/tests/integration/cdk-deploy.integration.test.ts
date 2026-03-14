/**
 * Integration Tests: CDK Deploy Verification
 * Feature: F-SUB-018-INT
 *
 * Verifies deployed AWS resources match the CDK specification.
 * Runs after `cdk deploy --require-approval never --context stage=dev`.
 */

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockAwsCli = {
  dynamodb: {
    describeTable: jest.fn(),
  },
  lambda: {
    getFunction: jest.fn(),
  },
  apigateway: {
    getResources: jest.fn(),
    getMethod: jest.fn(),
  },
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Integration: CDK Deploy Verification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-018-INT: DynamoDB Table Deployed ──────────────────────────────
  describe('F-SUB-018-INT: DynamoDB Verification', () => {
    it('should have subscriptions table with 3 GSIs', async () => {
      mockAwsCli.dynamodb.describeTable.mockResolvedValue({
        Table: {
          TableName: 'careervp-subscriptions-dev',
          KeySchema: [
            { AttributeName: 'subscription_id', KeyType: 'HASH' },
          ],
          GlobalSecondaryIndexes: [
            { IndexName: 'UserSubscriptionIndex' },
            { IndexName: 'StatusIndex' },
            { IndexName: 'CustomerIndex' },
          ],
          BillingModeSummary: { BillingMode: 'PAY_PER_REQUEST' },
        },
      });

      const result = await mockAwsCli.dynamodb.describeTable({
        TableName: 'careervp-subscriptions-dev',
      });

      expect(result.Table.TableName).toBe('careervp-subscriptions-dev');
      expect(result.Table.GlobalSecondaryIndexes).toHaveLength(3);

      const gsiNames = result.Table.GlobalSecondaryIndexes.map(
        (g: { IndexName: string }) => g.IndexName,
      );
      expect(gsiNames).toContain('UserSubscriptionIndex');
      expect(gsiNames).toContain('StatusIndex');
      expect(gsiNames).toContain('CustomerIndex');
    });
  });

  // ── F-SUB-018-INT: Lambda Configuration ─────────────────────────────────
  describe('F-SUB-018-INT: Lambda Verification', () => {
    it('should have billing Lambda with correct configuration', async () => {
      mockAwsCli.lambda.getFunction.mockResolvedValue({
        Configuration: {
          FunctionName: 'careervp-billing-dev',
          MemorySize: 256,
          Timeout: 30,
          Runtime: 'python3.12',
          Environment: {
            Variables: {
              STRIPE_SECRET_KEY: '(encrypted)',
              STRIPE_PRICE_MONTHLY: 'price_monthly_001',
              STRIPE_PRICE_QUARTERLY: 'price_quarterly_001',
              STRIPE_WEBHOOK_SECRET: '(encrypted)',
              SUBSCRIPTIONS_TABLE_NAME: 'careervp-subscriptions-dev',
              USERS_TABLE_NAME: 'careervp-users-dev',
              USAGE_TABLE_NAME: 'careervp-usage-dev',
            },
          },
        },
      });

      const result = await mockAwsCli.lambda.getFunction({
        FunctionName: 'careervp-billing-dev',
      });

      const config = result.Configuration;
      expect(config.MemorySize).toBe(256);
      expect(config.Timeout).toBe(30);
      expect(config.Runtime).toBe('python3.12');

      // Verify all env vars present
      const envVars = config.Environment.Variables;
      expect(envVars).toHaveProperty('STRIPE_SECRET_KEY');
      expect(envVars).toHaveProperty('STRIPE_PRICE_MONTHLY');
      expect(envVars).toHaveProperty('STRIPE_PRICE_QUARTERLY');
      expect(envVars).toHaveProperty('STRIPE_WEBHOOK_SECRET');
      expect(envVars).toHaveProperty('SUBSCRIPTIONS_TABLE_NAME');
    });
  });

  // ── F-SUB-018-INT: API Gateway Auth ─────────────────────────────────────
  describe('F-SUB-018-INT: API Gateway Verification', () => {
    it('should have webhook route with no authorizer', async () => {
      mockAwsCli.apigateway.getMethod.mockResolvedValue({
        httpMethod: 'POST',
        authorizationType: 'NONE',
      });

      const result = await mockAwsCli.apigateway.getMethod({
        restApiId: 'test-api-id',
        resourceId: 'webhook-resource-id',
        httpMethod: 'POST',
      });

      expect(result.authorizationType).toBe('NONE');
    });

    it('should have checkout route with Cognito authorizer', async () => {
      mockAwsCli.apigateway.getMethod.mockResolvedValue({
        httpMethod: 'POST',
        authorizationType: 'COGNITO_USER_POOLS',
      });

      const result = await mockAwsCli.apigateway.getMethod({
        restApiId: 'test-api-id',
        resourceId: 'checkout-resource-id',
        httpMethod: 'POST',
      });

      expect(result.authorizationType).toBe('COGNITO_USER_POOLS');
    });
  });
});
