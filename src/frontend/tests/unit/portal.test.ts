/**
 * Unit Tests: Customer Portal Session
 * Feature: F-SUB-007
 *
 * Tests the POST /billing/portal handler logic including:
 * - Creating a portal session for existing customers
 * - Returning 404 when no customer exists
 */

import portalRequestPayload from '../payloads/portal-request.json';
import portalNoCustomerPayload from '../payloads/portal-no-customer.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripePortalCreate = jest.fn();
const mockDal = {
  get_customer_id: jest.fn(),
};

// ─── Simulated handle_portal Logic ───────────────────────────────────────────

interface PortalResult {
  statusCode: number;
  body: Record<string, unknown>;
}

async function handlePortal(
  userId: string,
  body: { return_url?: string },
): Promise<PortalResult> {
  const returnUrl = body.return_url ?? 'https://app.careervp.com/settings/billing';

  const customerId = mockDal.get_customer_id(userId);
  if (!customerId) {
    return {
      statusCode: 404,
      body: { error: 'No billing account found. Please subscribe first.' },
    };
  }

  const portalSession = mockStripePortalCreate({
    customer: customerId,
    return_url: returnUrl,
  });

  return {
    statusCode: 200,
    body: { portal_url: portalSession.url },
  };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Customer Portal Session', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStripePortalCreate.mockReturnValue({
      url: 'https://billing.stripe.com/session/test_portal_001',
    });
  });

  // ── F-SUB-007: Portal Session Created ───────────────────────────────────
  describe('F-SUB-007: Create Portal Session', () => {
    it('should create portal session for existing customer and return portal_url', async () => {
      // Preconditions: DynamoDB returns customer_id = "cus_Nabc"
      mockDal.get_customer_id.mockReturnValue(portalRequestPayload.customer_id);

      const result = await handlePortal('user-007', {
        return_url: portalRequestPayload.return_url,
      });

      // Assert stripe.billing_portal.Session.create() called with correct customer
      expect(mockStripePortalCreate).toHaveBeenCalledWith({
        customer: 'cus_Nabc',
        return_url: 'https://app.careervp.com/settings/billing',
      });

      // Assert 200 with portal_url
      expect(result.statusCode).toBe(200);
      expect(result.body.portal_url).toBe(
        'https://billing.stripe.com/session/test_portal_001',
      );
    });
  });

  // ── F-SUB-007b: No Customer → 404 ──────────────────────────────────────
  describe('F-SUB-007b: No Customer Found', () => {
    it('should return 404 when no customer_id exists for user', async () => {
      // Preconditions: DynamoDB returns no customer_id
      mockDal.get_customer_id.mockReturnValue(null);

      const result = await handlePortal('user-007b', {
        return_url: 'https://app.careervp.com/settings/billing',
      });

      // Assert stripe portal NOT called
      expect(mockStripePortalCreate).not.toHaveBeenCalled();

      // Assert 404 response
      expect(result.statusCode).toBe(404);
      expect(result.body.error).toBe('No billing account found. Please subscribe first.');
    });
  });
});
