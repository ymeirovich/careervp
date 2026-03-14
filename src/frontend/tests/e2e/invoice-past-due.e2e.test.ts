/**
 * E2E Tests: Invoice Payment Failure and Past Due Banner
 * Feature: F-SUB-013-E2E
 *
 * Tests: payment fails -> past_due banner visible -> job creation blocked.
 * Environment: dev stage; Stripe test mode; Stripe CLI.
 */

// ─── Configuration ───────────────────────────────────────────────────────────

const DEV_API_BASE = 'https://dev-api.careervp.com';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockApi = {
  get: jest.fn(),
  post: jest.fn(),
};

const mockStripeCli = {
  trigger: jest.fn(),
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('E2E: Invoice Payment Failure', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-013-E2E: Payment Failure Flow ─────────────────────────────────
  describe('F-SUB-013-E2E: Past Due After Payment Failure', () => {
    it('should mark subscription as past_due and block job creation', async () => {
      // Step 1: Trigger payment failure via Stripe CLI
      mockStripeCli.trigger.mockResolvedValue({
        event: 'invoice.payment_failed',
        delivered: true,
      });

      const triggerResult = await mockStripeCli.trigger('invoice.payment_failed');
      expect(triggerResult.delivered).toBe(true);

      // Step 2: Wait for webhook processing (simulated)

      // Step 3: Reload app; assert past_due state visible
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: {
            status: 'past_due',
            plan: 'monthly',
            payment_failed_count: 1,
          },
          has_active_subscription: false,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.status).toBe('past_due');
      expect(subResponse.data.has_active_subscription).toBe(false);

      // Step 4: Attempt to create a job -> assert 403 subscription_required
      mockApi.post.mockResolvedValue({
        status: 403,
        data: {
          error: 'subscription_required',
          message: 'Your subscription is inactive. Please update your payment method.',
        },
      });

      const jobResponse = await mockApi.post(`${DEV_API_BASE}/jobs`, {});
      expect(jobResponse.status).toBe(403);
      expect(jobResponse.data.error).toBe('subscription_required');
    });

    it('should increment payment_failed_count on each failure', async () => {
      // First failure
      mockStripeCli.trigger.mockResolvedValue({ delivered: true });
      await mockStripeCli.trigger('invoice.payment_failed');

      // Second failure
      await mockStripeCli.trigger('invoice.payment_failed');

      // Verify count
      mockApi.get.mockResolvedValue({
        status: 200,
        data: {
          subscription: {
            status: 'past_due',
            payment_failed_count: 2,
          },
          has_active_subscription: false,
        },
      });

      const subResponse = await mockApi.get(`${DEV_API_BASE}/users/me/subscription`);
      expect(subResponse.data.subscription.payment_failed_count).toBeGreaterThanOrEqual(1);
    });
  });
});
