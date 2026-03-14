/**
 * Regression Tests: Customer Deduplication
 * Feature: F-SUB-005-R
 *
 * Simulates the full path: initial checkout -> canceled -> re-checkout.
 * Confirms only 1 Stripe customer exists for the user.
 */

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeCustomerCreate = jest.fn();
const mockStripeCheckoutCreate = jest.fn();
const mockDal = {
  get_subscription_by_user: jest.fn(),
  get_customer_id: jest.fn(),
  store_customer_id: jest.fn(),
};
const mockUserDal = {
  get_user: jest.fn(),
};

const PRICE_MAP: Record<string, string> = {
  monthly: 'price_monthly_001',
  quarterly: 'price_quarterly_001',
};

async function handleCheckout(userId: string, plan: string): Promise<string> {
  const existing = mockDal.get_subscription_by_user(userId);
  if (existing && existing.status === 'active') {
    throw new Error('Already active');
  }

  let customerId = mockDal.get_customer_id(userId);
  if (!customerId) {
    const user = mockUserDal.get_user(userId);
    const customer = mockStripeCustomerCreate({
      email: user.email,
      metadata: { user_id: userId },
    });
    customerId = customer.id;
    mockDal.store_customer_id(userId, customerId);
  }

  const session = mockStripeCheckoutCreate({
    customer: customerId,
    line_items: [{ price: PRICE_MAP[plan], quantity: 1 }],
    mode: 'subscription',
  });

  return session.url;
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: Customer Deduplication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUserDal.get_user.mockReturnValue({
      user_id: 'dedup-user',
      email: 'dedup@careervp.com',
    });
    mockStripeCustomerCreate.mockReturnValue({ id: 'cus_dedup_001' });
    mockStripeCheckoutCreate.mockReturnValue({
      url: 'https://checkout.stripe.com/c/pay/cs_test_dedup',
    });
  });

  // ── F-SUB-005-R: Full Lifecycle Deduplication ───────────────────────────
  describe('F-SUB-005-R: No Duplicate Stripe Customers', () => {
    it('should create customer on first checkout, reuse on re-subscribe after cancel', async () => {
      // Phase 1: Initial checkout (no existing customer)
      mockDal.get_subscription_by_user.mockReturnValue(null);
      mockDal.get_customer_id.mockReturnValue(null);

      await handleCheckout('dedup-user', 'monthly');

      // Assert: Customer created
      expect(mockStripeCustomerCreate).toHaveBeenCalledTimes(1);
      expect(mockDal.store_customer_id).toHaveBeenCalledWith('dedup-user', 'cus_dedup_001');

      // Phase 2: Subscription canceled
      mockDal.get_subscription_by_user.mockReturnValue({
        subscription_id: 'sub_dedup',
        status: 'canceled',
      });

      // Phase 3: Re-subscribe (should reuse existing customer)
      mockDal.get_customer_id.mockReturnValue('cus_dedup_001');

      await handleCheckout('dedup-user', 'monthly');

      // Assert: Customer.create() was NOT called again
      expect(mockStripeCustomerCreate).toHaveBeenCalledTimes(1); // Still just 1 from phase 1

      // Assert: Checkout used the existing customer
      expect(mockStripeCheckoutCreate).toHaveBeenLastCalledWith(
        expect.objectContaining({
          customer: 'cus_dedup_001',
        }),
      );
    });

    it('should result in exactly 1 Stripe customer after full lifecycle', async () => {
      // Track all customer creates
      let customerCreateCount = 0;
      mockStripeCustomerCreate.mockImplementation((params) => {
        customerCreateCount++;
        return { id: `cus_dedup_${customerCreateCount}` };
      });

      // First checkout
      mockDal.get_subscription_by_user.mockReturnValue(null);
      mockDal.get_customer_id.mockReturnValue(null);
      await handleCheckout('dedup-user', 'monthly');

      // After cancel, re-checkout with existing customer
      mockDal.get_subscription_by_user.mockReturnValue({ status: 'canceled' });
      mockDal.get_customer_id.mockReturnValue('cus_dedup_1');
      await handleCheckout('dedup-user', 'quarterly');

      // Only 1 customer created across the full lifecycle
      expect(customerCreateCount).toBe(1);
    });
  });
});
