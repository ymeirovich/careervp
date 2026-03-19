/**
 * Global test setup for CareerVP Subscription Service tests.
 *
 * Configures:
 * - Environment variables for Lambda mocking
 * - Stripe mock defaults
 * - DynamoDB mock defaults
 * - Cognito JWT mock helpers
 */

// ─── Environment Variables ───────────────────────────────────────────────────
process.env.STRIPE_SECRET_KEY = 'sk_test_mock_key_for_testing';
process.env.STRIPE_PRICE_MONTHLY = 'price_monthly_001';
process.env.STRIPE_PRICE_QUARTERLY = 'price_quarterly_001';
process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_mock_secret';
process.env.SUBSCRIPTIONS_TABLE_NAME = 'careervp-subscriptions-dev';
process.env.USERS_TABLE_NAME = 'careervp-users-dev';
process.env.USAGE_TABLE_NAME = 'careervp-usage-dev';
process.env.ALLOWED_ORIGINS = 'https://app.careervp.com';
process.env.AWS_REGION = 'us-east-1';

// ─── Date Helpers ────────────────────────────────────────────────────────────
/**
 * Generates an ISO 8601 date string offset from now by the given number of days.
 */
export function daysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
}

export function daysFromNow(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

export function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
}

// ─── Mock Factories ──────────────────────────────────────────────────────────

/** Create a mock Lambda event for API Gateway proxy integration */
export function createApiGatewayEvent(overrides: {
  httpMethod?: string;
  path?: string;
  body?: string | null;
  headers?: Record<string, string>;
  requestContext?: Record<string, unknown>;
}): Record<string, unknown> {
  return {
    httpMethod: overrides.httpMethod ?? 'GET',
    path: overrides.path ?? '/',
    body: overrides.body ?? null,
    headers: overrides.headers ?? { 'Content-Type': 'application/json' },
    queryStringParameters: null,
    pathParameters: null,
    stageVariables: null,
    isBase64Encoded: false,
    requestContext: {
      authorizer: {
        claims: {
          sub: 'test-user-id',
          email: 'test@careervp.com',
        },
      },
      ...overrides.requestContext,
    },
  };
}

/** Create a mock Cognito JWT claims object */
export function createCognitoClaims(userId: string, email = 'test@careervp.com') {
  return {
    sub: userId,
    email,
    'cognito:username': userId,
    token_use: 'id',
    auth_time: Math.floor(Date.now() / 1000),
    iss: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_WiHMRqLpe',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };
}

/** Create a mock Stripe subscription retrieve response */
export function createStripeSubscription(overrides: Partial<{
  id: string;
  current_period_start: number;
  current_period_end: number;
  cancel_at_period_end: boolean;
  price_id: string;
  status: string;
}> = {}) {
  return {
    id: overrides.id ?? 'sub_1Pxyz',
    status: overrides.status ?? 'active',
    current_period_start: overrides.current_period_start ?? 1741996800,
    current_period_end: overrides.current_period_end ?? 1744675200,
    cancel_at_period_end: overrides.cancel_at_period_end ?? false,
    items: {
      data: [{
        price: { id: overrides.price_id ?? 'price_monthly_001' },
      }],
    },
  };
}

// ─── Global Mocks ────────────────────────────────────────────────────────────

// Auto-clear mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
});
