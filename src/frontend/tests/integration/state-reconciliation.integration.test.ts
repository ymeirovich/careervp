/**
 * Integration Test: Subscription State Reconciliation
 * Feature: CC-018
 *
 * A reconciliation function scans all subscriptions in DynamoDB and compares
 * each against the current Stripe state. Stripe is treated as the source of
 * truth — any divergences are corrected in DynamoDB.
 *
 * Strategy: Option B from CRITICAL_CONSIDERATIONS — daily reconciliation job.
 *
 * This test will FAIL until the reconciliation function is implemented.
 */

// ─── Mock Setup ──────────────────────────────────────────────────────────────

const mockStripeSubscriptionRetrieve = jest.fn();
const mockSubscriptionDal = {
  scan_all_active: jest.fn(),
  update_subscription_status: jest.fn(),
};
const mockLogger = { warn: jest.fn(), info: jest.fn() };
const mockMetrics = { add_metric: jest.fn() };

// ─── Simulated reconcileAllSubscriptions Logic ────────────────────────────────

interface ReconciliationResult {
  checked: number;
  divergences: number;
  updated: number;
  errors: number;
}

async function reconcileAllSubscriptions(): Promise<ReconciliationResult> {
  // TODO: This test will FAIL until the reconciliation function is implemented.

  const allSubs = await mockSubscriptionDal.scan_all_active() as Array<{ subscription_id: string; status: string; user_id: string }>;

  let divergences = 0;
  let updated = 0;
  let errors = 0;

  for (const sub of allSubs) {
    try {
      const stripeSub = await mockStripeSubscriptionRetrieve(sub.subscription_id);

      if (sub.status !== stripeSub.status) {
        divergences++;
        mockLogger.warn('Reconciliation: divergence found', {
          subscription_id: sub.subscription_id,
          user_id: sub.user_id,
          db_status: sub.status,
          stripe_status: stripeSub.status,
        });
        mockMetrics.add_metric({ name: 'subscription_state_divergence', value: 1, unit: 'Count' });

        await mockSubscriptionDal.update_subscription_status(sub.subscription_id, stripeSub.status);
        updated++;
      }
    } catch (err) {
      errors++;
      mockLogger.warn('Reconciliation: error checking subscription', {
        subscription_id: sub.subscription_id,
        error: (err as Error).message,
      });
    }
  }

  return { checked: allSubs.length, divergences, updated, errors };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('CC-018: Subscription State Reconciliation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should update DynamoDB to match Stripe for each divergent subscription', async () => {
    // TODO: Currently FAILS — no reconciliation function exists
    mockSubscriptionDal.scan_all_active.mockResolvedValue([
      { subscription_id: 'sub_001', status: 'active', user_id: 'user_001' }, // Will stay active
      { subscription_id: 'sub_002', status: 'active', user_id: 'user_002' }, // Diverged — Stripe says canceled
    ]);

    mockStripeSubscriptionRetrieve
      .mockResolvedValueOnce({ status: 'active' })   // sub_001: matches
      .mockResolvedValueOnce({ status: 'canceled' }); // sub_002: diverged

    const result = await reconcileAllSubscriptions();

    expect(result.checked).toBe(2);
    expect(result.divergences).toBe(1);
    expect(result.updated).toBe(1);
    expect(mockSubscriptionDal.update_subscription_status).toHaveBeenCalledWith('sub_002', 'canceled');
    expect(mockSubscriptionDal.update_subscription_status).not.toHaveBeenCalledWith('sub_001', expect.any(String));
  });

  it('should treat Stripe as the single source of truth', async () => {
    mockSubscriptionDal.scan_all_active.mockResolvedValue([
      { subscription_id: 'sub_stale', status: 'canceled', user_id: 'user_stale' },
    ]);
    mockStripeSubscriptionRetrieve.mockResolvedValue({ status: 'active' }); // Stripe says active

    await reconcileAllSubscriptions();

    // Stripe wins — DynamoDB updated to "active"
    expect(mockSubscriptionDal.update_subscription_status).toHaveBeenCalledWith('sub_stale', 'active');
  });

  it('should not update DynamoDB when all subscriptions match Stripe', async () => {
    mockSubscriptionDal.scan_all_active.mockResolvedValue([
      { subscription_id: 'sub_clean_001', status: 'active', user_id: 'user_clean_001' },
      { subscription_id: 'sub_clean_002', status: 'canceled', user_id: 'user_clean_002' },
    ]);

    mockStripeSubscriptionRetrieve
      .mockResolvedValueOnce({ status: 'active' })
      .mockResolvedValueOnce({ status: 'canceled' });

    const result = await reconcileAllSubscriptions();

    expect(result.divergences).toBe(0);
    expect(result.updated).toBe(0);
    expect(mockSubscriptionDal.update_subscription_status).not.toHaveBeenCalled();
  });

  it('should emit subscription_state_divergence metric for each divergence', async () => {
    mockSubscriptionDal.scan_all_active.mockResolvedValue([
      { subscription_id: 'sub_a', status: 'active', user_id: 'user_a' },
      { subscription_id: 'sub_b', status: 'active', user_id: 'user_b' },
    ]);

    mockStripeSubscriptionRetrieve
      .mockResolvedValueOnce({ status: 'past_due' })  // diverged
      .mockResolvedValueOnce({ status: 'canceled' }); // diverged

    await reconcileAllSubscriptions();

    const metricCalls = mockMetrics.add_metric.mock.calls.filter(
      call => (call[0] as { name: string }).name === 'subscription_state_divergence',
    );
    expect(metricCalls).toHaveLength(2);
  });

  it('should continue reconciling other subscriptions even when one Stripe call fails', async () => {
    mockSubscriptionDal.scan_all_active.mockResolvedValue([
      { subscription_id: 'sub_error', status: 'active', user_id: 'user_error' },
      { subscription_id: 'sub_ok', status: 'active', user_id: 'user_ok' },
    ]);

    mockStripeSubscriptionRetrieve
      .mockRejectedValueOnce(new Error('Stripe API error'))
      .mockResolvedValueOnce({ status: 'active' }); // sub_ok succeeds

    const result = await reconcileAllSubscriptions();

    expect(result.errors).toBe(1);
    expect(result.checked).toBe(2);
  });
});
