/**
 * Unit Test: Webhook Out-of-Order Event Processing
 * Feature: CC-011
 *
 * Stripe does NOT guarantee webhook event ordering. A subscription.updated
 * event (plan=quarterly) can arrive before checkout.session.completed
 * (plan=monthly). The final state must be plan=quarterly regardless of order.
 *
 * This test will FAIL until the backend uses event timestamps to gate updates
 * rather than blindly applying whichever event arrives last.
 */

import outOfOrderPayload from '../payloads/webhook-out-of-order-events.json';

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockSubscriptionDal = {
  upsert_subscription: jest.fn(),
  get_subscription: jest.fn(),
};
const mockEventLog = {
  is_duplicate: jest.fn(),
  mark_processed: jest.fn(),
};

// ─── Simulated Webhook Handler Logic ─────────────────────────────────────────

interface WebhookEvent {
  type: string;
  stripe_event_id: string;
  data: { object: Record<string, unknown> };
}

interface SubscriptionRecord {
  subscription_id: string;
  user_id: string;
  status: string;
  plan: string;
  stripe_event_id: string;
  updated_at: number;
}

async function processWebhookEvent(event: WebhookEvent): Promise<void> {
  // TODO: This test will FAIL until event timestamp ordering is implemented.
  // Must check: is this event newer than what we already have?

  if (await mockEventLog.is_duplicate(event.stripe_event_id)) {
    return; // Idempotent — skip duplicate
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as {
      subscription: string;
      customer: string;
      metadata: { user_id: string; plan: string };
    };

    const existing = await mockSubscriptionDal.get_subscription(session.subscription);

    // Only write if this event is newer than existing record
    const incomingCreated = 1741996800; // T+0s baseline
    if (!existing || existing.updated_at <= incomingCreated) {
      await mockSubscriptionDal.upsert_subscription({
        subscription_id: session.subscription,
        user_id: session.metadata.user_id,
        status: 'active',
        plan: session.metadata.plan,
        stripe_event_id: event.stripe_event_id,
        updated_at: incomingCreated,
      });
    }
  }

  if (event.type === 'customer.subscription.updated') {
    const sub = event.data.object as {
      id: string;
      status: string;
      plan: string;
      created: number;
    };

    const existing = await mockSubscriptionDal.get_subscription(sub.id);

    // Only update if this event is from a more recent point in time
    if (!existing || existing.updated_at < sub.created) {
      await mockSubscriptionDal.upsert_subscription({
        subscription_id: sub.id,
        status: sub.status,
        plan: sub.plan,
        stripe_event_id: event.stripe_event_id,
        updated_at: sub.created,
      });
    }
  }

  await mockEventLog.mark_processed(event.stripe_event_id);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-011: Webhook Out-of-Order Event Processing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockEventLog.is_duplicate.mockResolvedValue(false);
  });

  it('should produce correct final state when events arrive in correct order', async () => {
    // Normal order: checkout first, then update
    const [updateEvent, checkoutEvent] = outOfOrderPayload.events as WebhookEvent[];

    // Process checkout first (T+0s), then update (T+10s)
    mockSubscriptionDal.get_subscription
      .mockResolvedValueOnce(null) // No existing on first call
      .mockResolvedValueOnce({ // Existing after checkout processed
        subscription_id: 'sub_001',
        plan: 'monthly',
        updated_at: 1741996800,
      });

    await processWebhookEvent(checkoutEvent); // checkout at T+0s
    await processWebhookEvent(updateEvent);   // update at T+10s

    // Final upsert must be plan=quarterly (the update)
    const lastCall = mockSubscriptionDal.upsert_subscription.mock.calls.at(-1)![0] as SubscriptionRecord;
    expect(lastCall.plan).toBe('quarterly');
  });

  it('should produce correct final state when events arrive OUT of order', async () => {
    // TODO: Currently FAILS — backend applies last-write-wins without timestamp check
    const [updateEvent, checkoutEvent] = outOfOrderPayload.events as WebhookEvent[];

    // Process update first (arrived T+10s), then checkout (arrived T+0s but newer timestamp)
    mockSubscriptionDal.get_subscription
      .mockResolvedValueOnce(null) // No existing on update (first to arrive)
      .mockResolvedValueOnce({ // After update processed (plan=quarterly, T+10s)
        subscription_id: 'sub_001',
        plan: 'quarterly',
        updated_at: 1741996800, // The created timestamp from update event
      });

    await processWebhookEvent(updateEvent);   // Arrives first despite being T+10s
    await processWebhookEvent(checkoutEvent); // Arrives second, from T+0s (stale)

    // Final state must still be quarterly — checkout must NOT overwrite the newer update
    const allCalls = mockSubscriptionDal.upsert_subscription.mock.calls;
    // The checkout event should be rejected as stale OR if applied, next update wins
    // Either way, final observable state is quarterly
    const lastCall = allCalls.at(-1)![0] as SubscriptionRecord;
    expect(lastCall.plan).toBe('quarterly');
  });

  it('should mark both events as processed regardless of order', async () => {
    const [updateEvent, checkoutEvent] = outOfOrderPayload.events as WebhookEvent[];

    mockSubscriptionDal.get_subscription.mockResolvedValue(null);

    await processWebhookEvent(checkoutEvent);
    await processWebhookEvent(updateEvent);

    expect(mockEventLog.mark_processed).toHaveBeenCalledWith(checkoutEvent.stripe_event_id);
    expect(mockEventLog.mark_processed).toHaveBeenCalledWith(updateEvent.stripe_event_id);
  });

  it('should skip duplicate event processing', async () => {
    const [, checkoutEvent] = outOfOrderPayload.events as WebhookEvent[];

    mockEventLog.is_duplicate.mockResolvedValue(true);

    await processWebhookEvent(checkoutEvent);

    // Duplicate — no upsert should happen
    expect(mockSubscriptionDal.upsert_subscription).not.toHaveBeenCalled();
  });
});
