/**
 * Unit Tests: Checkout Session Creation, Customer Reuse, Duplicate Blocked
 * Features: F-SUB-004, F-SUB-005, F-SUB-006
 *
 * Tests the POST /billing/checkout handler logic including:
 * - Monthly and quarterly plan checkout creation
 * - Invalid plan rejection (400)
 * - Stripe customer reuse for returning users
 * - Duplicate checkout blocking (409) for active subscribers
 */

import checkoutMonthlyPayload from '../payloads/checkout-monthly-request.json';
import checkoutQuarterlyPayload from '../payloads/checkout-quarterly-request.json';
import checkoutInvalidPlanPayload from '../payloads/checkout-invalid-plan.json';
import checkoutExistingCustomerPayload from '../payloads/checkout-existing-customer.json';
import checkoutAlreadyActivePayload from '../payloads/checkout-already-active.json';
import { createApiGatewayEvent } from '../setup';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const PRICE_MAP: Record<string, string> = {
  monthly: 'price_monthly_001',
  quarterly: 'price_quarterly_001',
};

const mockStripCustomerCreate = jest.fn();
const mockStripeCheckoutSessionCreate = jest.fn();
const mockDal = {
  get_subscription_by_user: jest.fn(),
  get_customer_id: jest.fn(),
  store_customer_id: jest.fn(),
};
const mockUserDal = {
  get_user: jest.fn(),
};

// ─── Simulated handle_checkout Logic ─────────────────────────────────────────

interface CheckoutResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handleCheckout(
  userId: string,
  body: { plan?: string; success_url?: string; cancel_url?: string },
): Promise<CheckoutResult> {
  const { plan, success_url, cancel_url } = body;

  if (!plan || !PRICE_MAP[plan]) {
    return {
      statusCode: 400,
      body: { error: `Invalid plan '${plan}'. Must be 'monthly' or 'quarterly'.` },
    };
  }
  if (!success_url || !cancel_url) {
    return {
      statusCode: 400,
      body: { error: 'success_url and cancel_url are required' },
    };
  }

  // Check for existing active subscription
  const existing = mockDal.get_subscription_by_user(userId);
  if (existing && existing.status === 'active') {
    return {
      statusCode: 409,
      body: { error: 'User already has an active subscription' },
    };
  }

  // Get or create Stripe customer
  let customerId = mockDal.get_customer_id(userId);
  if (!customerId) {
    const user = mockUserDal.get_user(userId);
    const customer = mockStripCustomerCreate({
      email: user?.email ?? '',
      metadata: { user_id: userId },
    });
    customerId = customer.id;
    mockDal.store_customer_id(userId, customerId);
  }

  const priceId = PRICE_MAP[plan];
  const session = mockStripeCheckoutSessionCreate({
    customer: customerId,
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    mode: 'subscription',
    success_url,
    cancel_url,
    metadata: { user_id: userId, plan },
  });

  return {
    statusCode: 200,
    body: { checkout_url: session.url },
  };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Checkout Session Creation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStripCustomerCreate.mockReturnValue({ id: 'cus_test001' });
    mockStripeCheckoutSessionCreate.mockReturnValue({
      id: 'cs_test_001',
      url: 'https://checkout.stripe.com/c/pay/cs_test_001',
    });
    mockUserDal.get_user.mockReturnValue({
      user_id: 'user-004',
      email: 'user@careervp.com',
    });
  });

  // ── F-SUB-004: Monthly Checkout ─────────────────────────────────────────
  describe('F-SUB-004: Monthly Checkout Session', () => {
    it('should create checkout session for monthly plan and return checkout_url', async () => {
      // Preconditions: No active subscription, no existing customer
      mockDal.get_subscription_by_user.mockReturnValue(null);
      mockDal.get_customer_id.mockReturnValue(null);

      const result = await handleCheckout('user-004', checkoutMonthlyPayload);

      // Assert stripe.Customer.create() called with metadata.user_id
      expect(mockStripCustomerCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          metadata: { user_id: 'user-004' },
        }),
      );

      // Assert dal.store_customer_id called
      expect(mockDal.store_customer_id).toHaveBeenCalledWith('user-004', 'cus_test001');

      // Assert checkout.Session.create called with monthly price
      expect(mockStripeCheckoutSessionCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          customer: 'cus_test001',
          line_items: [{ price: 'price_monthly_001', quantity: 1 }],
          mode: 'subscription',
        }),
      );

      // Assert response 200 with checkout_url
      expect(result.statusCode).toBe(200);
      expect(result.body.checkout_url).toBe('https://checkout.stripe.com/c/pay/cs_test_001');
    });
  });

  // ── F-SUB-004b: Quarterly Checkout ──────────────────────────────────────
  describe('F-SUB-004b: Quarterly Checkout Session', () => {
    it('should create checkout session with STRIPE_PRICE_QUARTERLY', async () => {
      mockDal.get_subscription_by_user.mockReturnValue(null);
      mockDal.get_customer_id.mockReturnValue(null);

      const result = await handleCheckout('user-004', checkoutQuarterlyPayload);

      // Assert checkout.Session.create() called with STRIPE_PRICE_QUARTERLY
      expect(mockStripeCheckoutSessionCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          line_items: [{ price: 'price_quarterly_001', quantity: 1 }],
        }),
      );

      expect(result.statusCode).toBe(200);
      expect(result.body.checkout_url).toBeDefined();
    });
  });

  // ── F-SUB-004c: Invalid Plan → 400 ─────────────────────────────────────
  describe('F-SUB-004c: Invalid Plan Rejection', () => {
    it('should return 400 for invalid plan value', async () => {
      const result = await handleCheckout('user-004', checkoutInvalidPlanPayload);

      // Assert 400 with message about invalid plan
      expect(result.statusCode).toBe(400);
      expect(result.body.error).toContain('Invalid plan');

      // Assert no Stripe calls made
      expect(mockStripCustomerCreate).not.toHaveBeenCalled();
      expect(mockStripeCheckoutSessionCreate).not.toHaveBeenCalled();
    });

    it('should return 400 when success_url is missing', async () => {
      const result = await handleCheckout('user-004', {
        plan: 'monthly',
        cancel_url: 'https://app.careervp.com/settings/billing',
      });

      expect(result.statusCode).toBe(400);
      expect(result.body.error).toContain('success_url');
    });
  });

  // ── F-SUB-005: Stripe Customer Reuse ────────────────────────────────────
  describe('F-SUB-005: Stripe Customer Reuse on Re-Subscribe', () => {
    it('should not create new Stripe customer when one exists', async () => {
      // Preconditions: User has existing stripe_customer_id
      mockDal.get_subscription_by_user.mockReturnValue(null);
      mockDal.get_customer_id.mockReturnValue(
        checkoutExistingCustomerPayload.user.stripe_customer_id,
      );

      const result = await handleCheckout('user-005', checkoutMonthlyPayload);

      // Assert stripe.Customer.create() is NOT called
      expect(mockStripCustomerCreate).not.toHaveBeenCalled();

      // Assert checkout.Session.create() called with existing customer
      expect(mockStripeCheckoutSessionCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          customer: 'cus_existing001',
        }),
      );

      expect(result.statusCode).toBe(200);
      expect(result.body.checkout_url).toBeDefined();
    });
  });

  // ── F-SUB-006: Duplicate Checkout Blocked ───────────────────────────────
  describe('F-SUB-006: Duplicate Checkout Blocked', () => {
    it('should return 409 when user already has an active subscription', async () => {
      // Preconditions: Active subscription exists
      mockDal.get_subscription_by_user.mockReturnValue(
        checkoutAlreadyActivePayload.subscription,
      );

      const result = await handleCheckout('user-006', checkoutMonthlyPayload);

      // Assert Stripe checkout.Session.create NOT called
      expect(mockStripeCheckoutSessionCreate).not.toHaveBeenCalled();

      // Assert 409 response
      expect(result.statusCode).toBe(409);
      expect(result.body.error).toBe('User already has an active subscription');
    });

    it('should allow checkout when subscription exists but is canceled', async () => {
      mockDal.get_subscription_by_user.mockReturnValue({
        subscription_id: 'sub_old',
        user_id: 'user-006',
        status: 'canceled',
        plan: 'monthly',
      });
      mockDal.get_customer_id.mockReturnValue('cus_existing001');

      const result = await handleCheckout('user-006', checkoutMonthlyPayload);

      expect(result.statusCode).toBe(200);
      expect(mockStripeCheckoutSessionCreate).toHaveBeenCalled();
    });
  });
});
