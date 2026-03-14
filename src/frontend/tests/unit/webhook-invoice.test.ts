/**
 * Unit Tests: Webhook — Invoice Payment Succeeded and Failed
 * Features: F-SUB-012, F-SUB-013
 *
 * Tests:
 * - invoice.payment_succeeded: recovery from past_due to active
 * - invoice.payment_failed: mark subscription as past_due
 */

import webhookInvoiceSucceededPayload from '../payloads/webhook-invoice-succeeded.json';
import webhookInvoiceFailedPayload from '../payloads/webhook-invoice-failed.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockDal = {
  get_subscription_by_stripe_id: jest.fn(),
  update_subscription_fields: jest.fn(),
};

// ─── Simulated Invoice Handlers ──────────────────────────────────────────────

async function handleInvoiceSucceeded(invoice: Record<string, unknown>): Promise<void> {
  const subscriptionId = invoice.subscription as string;

  if (!subscriptionId) return;

  const sub = mockDal.get_subscription_by_stripe_id(subscriptionId);
  if (!sub) return;

  mockDal.update_subscription_fields(subscriptionId, {
    status: 'active',
    payment_failed_count: 0,
    last_invoice_id: invoice.id as string,
  });
}

async function handleInvoiceFailed(invoice: Record<string, unknown>): Promise<void> {
  const subscriptionId = invoice.subscription as string;
  const attemptCount = (invoice.attempt_count as number) ?? 1;

  if (!subscriptionId) return;

  const sub = mockDal.get_subscription_by_stripe_id(subscriptionId);
  if (!sub) return;

  mockDal.update_subscription_fields(subscriptionId, {
    status: 'past_due',
    payment_failed_count: attemptCount,
    last_invoice_id: invoice.id as string,
  });
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Webhook — Invoice Events', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-012: Invoice Succeeded (Recovery) ─────────────────────────────
  describe('F-SUB-012: Invoice Payment Succeeded', () => {
    it('should set status to active and reset payment_failed_count', async () => {
      // Preconditions: subscription exists with status = "past_due", payment_failed_count = 2
      mockDal.get_subscription_by_stripe_id.mockReturnValue({
        subscription_id: 'sub_1Pxyz',
        status: 'past_due',
        payment_failed_count: 2,
      });

      const invoiceData = webhookInvoiceSucceededPayload.data.object;
      await handleInvoiceSucceeded(invoiceData);

      // Assert update_subscription_fields called with recovery data
      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith('sub_1Pxyz', {
        status: 'active',
        payment_failed_count: 0,
        last_invoice_id: 'in_recovered001',
      });
    });

    it('should skip processing when subscription_id is missing', async () => {
      await handleInvoiceSucceeded({ id: 'in_nosubscription' });

      expect(mockDal.get_subscription_by_stripe_id).not.toHaveBeenCalled();
      expect(mockDal.update_subscription_fields).not.toHaveBeenCalled();
    });

    it('should skip processing when no local subscription record exists', async () => {
      mockDal.get_subscription_by_stripe_id.mockReturnValue(null);

      const invoiceData = webhookInvoiceSucceededPayload.data.object;
      await handleInvoiceSucceeded(invoiceData);

      expect(mockDal.update_subscription_fields).not.toHaveBeenCalled();
    });
  });

  // ── F-SUB-013: Invoice Payment Failed (Past Due) ───────────────────────
  describe('F-SUB-013: Invoice Payment Failed', () => {
    it('should set status to past_due and record attempt_count', async () => {
      // Preconditions: subscription exists with status = "active"
      mockDal.get_subscription_by_stripe_id.mockReturnValue({
        subscription_id: 'sub_1Pxyz',
        status: 'active',
        payment_failed_count: 0,
      });

      const invoiceData = webhookInvoiceFailedPayload.data.object;
      await handleInvoiceFailed(invoiceData);

      // Assert update_subscription_fields called with past_due status
      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith('sub_1Pxyz', {
        status: 'past_due',
        payment_failed_count: 1,
        last_invoice_id: 'in_fail001',
      });
    });

    it('should use attempt_count from Stripe payload, not local counter', async () => {
      mockDal.get_subscription_by_stripe_id.mockReturnValue({
        subscription_id: 'sub_1Pxyz',
        status: 'past_due',
        payment_failed_count: 1,
      });

      // Second failure with attempt_count = 2
      await handleInvoiceFailed({
        id: 'in_fail002',
        subscription: 'sub_1Pxyz',
        customer: 'cus_Nabc',
        attempt_count: 2,
      });

      expect(mockDal.update_subscription_fields).toHaveBeenCalledWith('sub_1Pxyz', {
        status: 'past_due',
        payment_failed_count: 2,
        last_invoice_id: 'in_fail002',
      });
    });

    it('should skip processing when subscription_id is missing', async () => {
      await handleInvoiceFailed({ id: 'in_nosubscription', attempt_count: 1 });

      expect(mockDal.get_subscription_by_stripe_id).not.toHaveBeenCalled();
    });

    it('should skip processing when no local subscription record exists', async () => {
      mockDal.get_subscription_by_stripe_id.mockReturnValue(null);

      const invoiceData = webhookInvoiceFailedPayload.data.object;
      await handleInvoiceFailed(invoiceData);

      expect(mockDal.update_subscription_fields).not.toHaveBeenCalled();
    });
  });
});
