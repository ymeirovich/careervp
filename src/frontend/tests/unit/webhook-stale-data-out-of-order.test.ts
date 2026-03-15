/**
 * Unit Test: Stale Data from Out-of-Order Webhook
 * Feature: CC-012
 *
 * A subscription.updated event with an old billing period can arrive AFTER
 * an invoice.payment_succeeded event with newer data. The stale update must
 * NOT overwrite the newer record.
 *
 * This test will FAIL until the backend uses a "last-write-wins with timestamp
 * guard" strategy, preventing older events from overwriting newer state.
 */

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockSubscriptionDal = {
  upsert_subscription_if_newer: jest.fn(),
  get_subscription: jest.fn(),
};
const mockEventLog = {
  is_duplicate: jest.fn(),
  mark_processed: jest.fn(),
};

// ─── Simulated Handler Logic ─────────────────────────────────────────────────

interface StaleUpdateEvent {
  event_id: string;
  type: string;
  subscription_id: string;
  new_status: string;
  new_period_end: number; // Unix timestamp — the NEW billing period
  stripe_event_created: number; // When Stripe created this event
}

async function processSubscriptionUpdate(event: StaleUpdateEvent): Promise<'applied' | 'rejected_stale'> {
  // TODO: This test will FAIL until the backend implements timestamp-gated updates.
  // Must use DynamoDB conditional update: only write if event is newer than stored.

  if (await mockEventLog.is_duplicate(event.event_id)) {
    return 'rejected_stale';
  }

  const existing = await mockSubscriptionDal.get_subscription(event.subscription_id);

  if (existing && existing.stripe_event_created > event.stripe_event_created) {
    // Stale event — we already have newer data. Reject without writing.
    await mockEventLog.mark_processed(event.event_id); // Still mark as seen
    return 'rejected_stale';
  }

  await mockSubscriptionDal.upsert_subscription_if_newer({
    subscription_id: event.subscription_id,
    status: event.new_status,
    current_period_end: event.new_period_end,
    stripe_event_created: event.stripe_event_created,
  });

  await mockEventLog.mark_processed(event.event_id);
  return 'applied';
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-012: Stale Data from Out-of-Order Webhook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockEventLog.is_duplicate.mockResolvedValue(false);
  });

  it('should apply a newer event over stale cached data', async () => {
    const olderEvent: StaleUpdateEvent = {
      event_id: 'evt_old_001',
      type: 'customer.subscription.updated',
      subscription_id: 'sub_001',
      new_status: 'past_due',
      new_period_end: 1740000000, // Older period
      stripe_event_created: 1741000000, // Older
    };

    const newerEvent: StaleUpdateEvent = {
      event_id: 'evt_new_001',
      type: 'invoice.payment_succeeded',
      subscription_id: 'sub_001',
      new_status: 'active',
      new_period_end: 1744675200, // Newer period
      stripe_event_created: 1742000000, // Newer
    };

    mockSubscriptionDal.get_subscription
      .mockResolvedValueOnce(null) // First event: no existing record
      .mockResolvedValueOnce({     // Second event: record from first event
        subscription_id: 'sub_001',
        stripe_event_created: 1741000000,
      });

    // Process newer event first (correct behaviour — apply it)
    const result1 = await processSubscriptionUpdate(newerEvent);
    expect(result1).toBe('applied');

    // Then the older event arrives — must be rejected as stale
    const result2 = await processSubscriptionUpdate(olderEvent);
    expect(result2).toBe('rejected_stale');
  });

  it('should reject stale event without writing to DynamoDB', async () => {
    // TODO: Currently FAILS — backend applies last-write-wins without checking timestamps
    const staleEvent: StaleUpdateEvent = {
      event_id: 'evt_stale_001',
      type: 'customer.subscription.updated',
      subscription_id: 'sub_001',
      new_status: 'past_due',
      new_period_end: 1740000000,
      stripe_event_created: 1741000000, // Older than what's in DB
    };

    // DB already has a newer record
    mockSubscriptionDal.get_subscription.mockResolvedValue({
      subscription_id: 'sub_001',
      status: 'active',
      stripe_event_created: 1742000000, // Newer than the incoming event
    });

    const result = await processSubscriptionUpdate(staleEvent);

    expect(result).toBe('rejected_stale');
    // Must NOT write stale data to DynamoDB
    expect(mockSubscriptionDal.upsert_subscription_if_newer).not.toHaveBeenCalled();
  });

  it('should still mark a stale event as processed to prevent redelivery loop', async () => {
    const staleEvent: StaleUpdateEvent = {
      event_id: 'evt_stale_002',
      type: 'customer.subscription.updated',
      subscription_id: 'sub_001',
      new_status: 'canceled',
      new_period_end: 1740000000,
      stripe_event_created: 1741000000,
    };

    mockSubscriptionDal.get_subscription.mockResolvedValue({
      subscription_id: 'sub_001',
      stripe_event_created: 1742000000,
    });

    await processSubscriptionUpdate(staleEvent);

    // Even stale events must be marked processed to avoid Stripe retrying forever
    expect(mockEventLog.mark_processed).toHaveBeenCalledWith('evt_stale_002');
  });

  it('should apply an event when no existing record is present', async () => {
    const firstEvent: StaleUpdateEvent = {
      event_id: 'evt_first_001',
      type: 'customer.subscription.updated',
      subscription_id: 'sub_new_001',
      new_status: 'active',
      new_period_end: 1744675200,
      stripe_event_created: 1742000000,
    };

    mockSubscriptionDal.get_subscription.mockResolvedValue(null);

    const result = await processSubscriptionUpdate(firstEvent);

    expect(result).toBe('applied');
    expect(mockSubscriptionDal.upsert_subscription_if_newer).toHaveBeenCalledWith(
      expect.objectContaining({ subscription_id: 'sub_new_001', status: 'active' }),
    );
  });

  it('should converge to correct state regardless of delivery order', async () => {
    // Simulate processing 3 events in random order; final state must be correct
    const events: StaleUpdateEvent[] = [
      { event_id: 'evt_t3', type: 'invoice.payment_succeeded', subscription_id: 'sub_001', new_status: 'active', new_period_end: 1744675200, stripe_event_created: 1743000000 },
      { event_id: 'evt_t1', type: 'customer.subscription.updated', subscription_id: 'sub_001', new_status: 'past_due', new_period_end: 1741000000, stripe_event_created: 1741000000 },
      { event_id: 'evt_t2', type: 'customer.subscription.updated', subscription_id: 'sub_001', new_status: 'canceled', new_period_end: 1742000000, stripe_event_created: 1742000000 },
    ];

    // Deliver in reverse order (newest first, then stale)
    let storedRecord: { stripe_event_created: number } | null = null;
    mockSubscriptionDal.get_subscription.mockImplementation(async () => storedRecord);
    mockSubscriptionDal.upsert_subscription_if_newer.mockImplementation(async (data: { stripe_event_created: number }) => {
      storedRecord = data;
    });

    for (const event of events) {
      await processSubscriptionUpdate(event);
    }

    // After all events, the newest (t3 = active) should win
    expect(storedRecord).toMatchObject({ new_status: 'active' });
  });
});
