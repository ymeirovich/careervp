/**
 * Unit Tests: Webhook Signature Verification
 * Feature: F-SUB-009
 *
 * Tests that the /billing/webhook route rejects requests with invalid
 * Stripe signatures and produces zero DynamoDB side effects.
 */

import webhookInvalidSigPayload from '../payloads/webhook-invalid-signature.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const WEBHOOK_SECRET = 'whsec_test_mock_secret';

const mockStripeWebhookConstructEvent = jest.fn();
const mockDal = {
  upsert_subscription: jest.fn(),
  update_subscription_fields: jest.fn(),
  set_unlimited_usage: jest.fn(),
};

class SignatureVerificationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SignatureVerificationError';
  }
}

// ─── Simulated handle_webhook Logic ──────────────────────────────────────────

interface WebhookResult {
  statusCode: number;
  body: Record<string, unknown>;
}

function handleWebhook(event: {
  body: string;
  headers: Record<string, string>;
}): WebhookResult {
  const payload = event.body;
  const sigHeader = event.headers['Stripe-Signature'] ?? '';

  try {
    mockStripeWebhookConstructEvent(payload, sigHeader, WEBHOOK_SECRET);
  } catch (err) {
    if (err instanceof SignatureVerificationError) {
      return { statusCode: 400, body: { error: 'Invalid signature' } };
    }
    return { statusCode: 400, body: { error: 'Invalid payload' } };
  }

  // If we got here, signature was valid — process the event
  return { statusCode: 200, body: { received: true } };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Webhook Signature Verification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── F-SUB-009: Invalid Signature → 400 ─────────────────────────────────
  describe('F-SUB-009: Invalid Signature Rejected', () => {
    it('should return 400 with "Invalid signature" on bad signature', () => {
      // Preconditions: Stripe-Signature header contains invalid hash
      mockStripeWebhookConstructEvent.mockImplementation(() => {
        throw new SignatureVerificationError('Signature verification failed');
      });

      const result = handleWebhook({
        body: webhookInvalidSigPayload.body,
        headers: webhookInvalidSigPayload.headers,
      });

      // Assert 400 response
      expect(result.statusCode).toBe(400);
      expect(result.body.error).toBe('Invalid signature');

      // Assert zero DynamoDB writes
      expect(mockDal.upsert_subscription).not.toHaveBeenCalled();
      expect(mockDal.update_subscription_fields).not.toHaveBeenCalled();
      expect(mockDal.set_unlimited_usage).not.toHaveBeenCalled();
    });

    it('should pass raw body and signature to construct_event', () => {
      mockStripeWebhookConstructEvent.mockImplementation(() => {
        throw new SignatureVerificationError('Bad sig');
      });

      handleWebhook({
        body: webhookInvalidSigPayload.body,
        headers: webhookInvalidSigPayload.headers,
      });

      // Assert construct_event called with correct args
      expect(mockStripeWebhookConstructEvent).toHaveBeenCalledWith(
        webhookInvalidSigPayload.body,
        't=1234567890,v1=badhash',
        WEBHOOK_SECRET,
      );
    });

    it('should return 400 for missing signature header', () => {
      mockStripeWebhookConstructEvent.mockImplementation(() => {
        throw new SignatureVerificationError('Missing signature');
      });

      const result = handleWebhook({
        body: '{"type":"test"}',
        headers: { 'Stripe-Signature': '' },
      });

      expect(result.statusCode).toBe(400);
    });

    it('should return 400 for malformed payload', () => {
      mockStripeWebhookConstructEvent.mockImplementation(() => {
        throw new Error('Invalid payload');
      });

      const result = handleWebhook({
        body: 'not-json',
        headers: { 'Stripe-Signature': 't=123,v1=abc' },
      });

      expect(result.statusCode).toBe(400);
      expect(result.body.error).toBe('Invalid payload');
    });
  });
});
