# Critical Considerations Test Implementation Plan

**Purpose:** Create test artifacts for the 12 critical areas identified in CRITICAL_CONSIDERATIONS.md that are not covered by the existing 129 tests.

**Status:** Planning phase - define what tests are needed before implementation

---

## Overview

The existing test suite (SUBSCRIPTION_FEATURE_TEST_PROMPT.md) tests the **happy path and basic errors**:
- ✅ Correct inputs → correct outputs
- ✅ Invalid inputs → correct error codes
- ✅ Basic mocking of dependencies

The critical tests we need to add test **edge cases and system properties**:
- ⚠️ Concurrent requests → no duplicates
- ⚠️ Partial failures → graceful recovery
- ⚠️ State divergence → detection and resolution
- ⚠️ Performance under load → latency acceptable
- ⚠️ Observability → metrics tracked
- ⚠️ Security hardening → secret rotation works

---

## Test Classification

### Category A: Automatable Unit/Integration Tests ✅
These can be run in CI/CD, provide clear pass/fail results.

| Consideration | Test Type | Automation | Count |
|---------------|-----------|-----------|-------|
| Transaction Safety | Integration | ✅ Yes | 3 |
| Backward Compatibility | Unit | ✅ Yes | 3 |
| Stripe API Errors | Integration | ✅ Yes | 4 |
| Webhook Out-of-Order | Unit | ✅ Yes | 2 |
| Data Consistency | Integration | ✅ Yes | 3 |
| State Divergence | Integration | ✅ Yes | 3 |
| Lifecycle Edge Cases | Integration | ✅ Yes | 2 |

**Subtotal: 20 automatable tests**

### Category B: Performance & Load Tests ⚙️
Require special setup, take longer to run.

| Consideration | Test Type | Automation | Count |
|---------------|-----------|-----------|-------|
| Performance | Load Test | ⚠️ Optional | 2 |
| Observability | Metrics Validation | ⚠️ Semi | 3 |

**Subtotal: 5 performance tests**

### Category C: Security & Operational Tests 🔒
Require manual validation, deployment context, or external tools.

| Consideration | Test Type | Automation | Count |
|---------------|-----------|-----------|-------|
| Security | Manual/Script | ❌ Manual | 3 |
| Staging Validation | Deployment | ❌ Manual | 4 |

**Subtotal: 7 manual/operational tests**

---

## Detailed Test Definitions

### A1: Transaction Safety & Idempotency (3 tests)

#### Test: CC-001 — Concurrent Checkout Prevention
**File:** `integration/concurrent-checkout.integration.test.ts`
**Type:** Integration (concurrent requests)

**What it tests:**
Two users simultaneously POST /billing/checkout with same user_id (attacker simulation or race condition).

**Preconditions:**
```json
{
  "user_id": "race-user-001",
  "subscription_status": null,
  "stripe_customer_id": null
}
```

**Steps:**
1. Send 2 concurrent POST /billing/checkout requests (same user_id)
2. Both requests complete
3. Verify Stripe Customer created exactly once (not twice)
4. Verify checkout session created for both (or one succeeds, one fails)
5. Verify no duplicate subscription records created

**Expected Result:**
- If first request wins: Second request gets 409 (customer exists)
- If concurrent: Only one customer created (Stripe deduplicates)
- Zero duplicate subscriptions

**Code Example Needed:**
```python
# concurrent_checkout_handler.py
async def handle_concurrent_checkout():
    # Should use DynamoDB conditional expression to prevent race
    response = subscriptions_dal.create_checkout_session(
        user_id,
        condition_expression="attribute_not_exists(active_checkout_at)"
    )
```

**Payload:** `concurrent-checkout-race.json`

---

#### Test: CC-002 — Race Between Check and Create
**File:** `integration/race-condition-check-create.integration.test.ts`

**What it tests:**
Time window between checking subscription exists and creating checkout session.

**Scenario:**
```
T0: Check: is_subscription_active(user) → false
T1: [RACE WINDOW] Another request creates subscription
T2: Create: checkout session created (overwrites subscription!)
```

**Steps:**
1. Create 2 concurrent checkout requests
2. First request starts checking subscription
3. Second request creates subscription in middle
4. First request continues and tries to create checkout
5. Verify 409 Conflict (not overwrite)

**Expected Result:**
- Atomic check-then-act using DynamoDB conditional expressions
- No overwrite of existing subscription
- Second request gets 409

**Payload:** `race-window.json`

---

#### Test: CC-003 — Idempotency Key Prevents Duplicates
**File:** `integration/stripe-idempotency.integration.test.ts`

**What it tests:**
Stripe idempotency key prevents duplicate customers/sessions on network retry.

**Steps:**
1. POST /billing/checkout with idempotency_key
2. Stripe returns 200 with session_id=ABC123
3. Network timeout (client doesn't receive response)
4. Client retries with same idempotency_key
5. Stripe returns 200 with same session_id=ABC123
6. Verify no new customer created
7. Verify no new session created

**Expected Result:**
- Same checkout URL returned on retry
- No duplicate Stripe objects

**Code Example Needed:**
```python
# Must include idempotency_key in Stripe call:
stripe.checkout.Session.create(
    customer=customer_id,
    line_items=[...],
    idempotency_key=f"checkout_{user_id}_{request_id}",
)
```

**Payload:** `idempotency-retry.json`

---

### A2: Backward Compatibility (3 tests)

#### Test: CC-004 — Missing Subscription Record (Old Trial User)
**File:** `unit/backward-compat-missing-subscription.test.ts`

**What it tests:**
User has User + Usage records but no Subscription record (old trial user).

**Preconditions:**
```json
{
  "user": { "user_id": "old-trial-001", "created_at": "2026-02-01T00:00:00Z" },
  "usage": { "user_id": "old-trial-001", "remaining": 2 },
  "subscription": null
}
```

**Steps:**
1. Call check_trial_and_quota("old-trial-001")
2. Verify it handles missing subscription gracefully
3. Should check trial + quota instead of crashing

**Expected Result:**
- Function doesn't crash
- Returns correct result based on trial/quota state
- Logs warning that Subscription record missing

**Code Example Needed:**
```python
def check_trial_and_quota(user_id: str) -> None:
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    # sub might be None for old data

    if sub and sub.is_active:
        return  # Active subscription grants access

    # If no subscription, check trial + quota
    # (Don't assume subscription always exists)
    user = users_dal.get_user(user_id)
    if not user:
        logger.error(f"User record missing: {user_id}")
        raise ApiError(500, "user_not_found", "User record missing")
```

**Payload:** `backward-compat-old-trial.json`

---

#### Test: CC-005 — Missing Usage Record (Data Corruption)
**File:** `unit/backward-compat-missing-usage.test.ts`

**What it tests:**
User exists but Usage record is missing or corrupted.

**Preconditions:**
```json
{
  "user": { "user_id": "corrupted-001", "created_at": "2026-03-01T00:00:00Z" },
  "usage": null
}
```

**Steps:**
1. Call check_trial_and_quota("corrupted-001")
2. Verify graceful handling (not crash)
3. Should either create usage record or return error

**Expected Result:**
- Returns 500 "usage_not_found" (not crash)
- Logs error with user_id for investigation
- Data recovery script can be run manually

**Payload:** `backward-compat-missing-usage.json`

---

#### Test: CC-006 — Graceful Degradation on Partial Data
**File:** `unit/backward-compat-partial-data.test.ts`

**What it tests:**
Multiple pieces of data missing - system still functions.

**Preconditions:**
```json
{
  "user": null,
  "usage": { "user_id": "orphan-001", "remaining": 0 },
  "subscription": null
}
```

**Steps:**
1. Multiple lookups fail
2. Verify graceful degradation order
3. Verify user sees meaningful error, not 500 crash

**Expected Result:**
- Clear error message
- Logs show exactly what's missing
- Admin can investigate from logs

---

### A3: Stripe API Errors (4 tests)

#### Test: CC-007 — Stripe 503 on Session Create
**File:** `integration/stripe-error-503-session.integration.test.ts`

**What it tests:**
Stripe API returns 503 during checkout.session.create().

**Setup:**
Mock Stripe to return 503 Service Unavailable

**Steps:**
1. POST /billing/checkout
2. Stripe.checkout.Session.create() throws 503
3. Verify Lambda returns 503 (not 500)
4. Verify no subscription created
5. Verify customer still exists (don't lose it)
6. User can retry (idempotency key)

**Expected Result:**
- Returns 503 "payment_provider_unavailable"
- No side effects (no partial state)
- User sees "try again in a minute" message

**Payload:** `stripe-503-error.json`

---

#### Test: CC-008 — Stripe 503 on Customer Create
**File:** `integration/stripe-error-503-customer.integration.test.ts`

**Steps:**
1. POST /billing/checkout
2. stripe.Customer.create() throws 503
3. Verify returns 503
4. Verify no user update with customer_id
5. User can retry

**Expected Result:**
- 503 error, no partial state
- Stripe customer not created
- Next retry creates fresh customer (idempotent)

---

#### Test: CC-009 — Timeout on Stripe API Call
**File:** `integration/stripe-timeout.integration.test.ts`

**What it tests:**
Stripe API call takes >10 seconds (timeout).

**Setup:**
Mock Stripe to delay 15 seconds

**Steps:**
1. POST /billing/checkout
2. Lambda has 30s timeout, Stripe call times out at 10s
3. Verify Lambda returns 503 (not 504 Gateway Timeout)
4. Verify no state corruption
5. User can retry

**Expected Result:**
- 503 "payment_provider_timeout"
- No partial state
- Idempotency prevents duplicates on retry

---

#### Test: CC-010 — Stripe Rate Limit (429)
**File:** `integration/stripe-rate-limit-429.integration.test.ts`

**What it tests:**
Stripe returns 429 Too Many Requests.

**Steps:**
1. Mock 429 response
2. Verify Lambda handles gracefully
3. Verify exponential backoff (if implemented)
4. Verify user sees "try again later"

**Expected Result:**
- 503 "please_retry_later"
- Metrics show rate limit hit
- Admin can see in CloudWatch

---

### A4: Webhook Out-of-Order Delivery (2 tests)

#### Test: CC-011 — Out-of-Order Webhook Events
**File:** `unit/webhook-out-of-order.test.ts`

**What it tests:**
Webhooks received in wrong order.

**Scenario:**
```
Event 1 (T=100): customer.subscription.updated (plan=quarterly)
Event 2 (T=95): checkout.session.completed (plan=monthly)

Delivered as: Event 2 first, then Event 1
```

**Steps:**
1. Process webhook 2 first: subscription created with plan=monthly
2. Process webhook 1 second: subscription updated to quarterly
3. Verify final state: plan=quarterly (correct)

**Expected Result:**
- Final state correct regardless of order
- No assumption about event ordering
- Both idempotent

**Payload:** `webhook-out-of-order-events.json`

---

#### Test: CC-012 — Stale Data in Out-of-Order Webhook
**File:** `unit/webhook-stale-data-out-of-order.test.ts`

**Scenario:**
```
Event 1: subscription.updated with stale data (old billing period)
Event 2: invoice.payment_succeeded with new data

Process Event 1 first with stale data, then Event 2 with new data
```

**Steps:**
1. Process out-of-order events with inconsistent data
2. Verify system converges to correct state
3. Verify no corruption from stale data

**Expected Result:**
- Latest event wins
- Or: Check timestamps and only apply if newer
- No state corruption

---

### A5: Data Consistency Across Boundaries (3 tests)

#### Test: CC-013 — Partial Failure: Customer Created, Subscription Fails
**File:** `integration/partial-failure-customer-created.integration.test.ts`

**Scenario:**
```
1. stripe.Customer.create() → ✅ success (cus_ABC123)
2. users_dal.update_stripe_customer_id() → ✅ success
3. stripe.checkout.Session.create() → ✅ success
4. subscriptions_dal.create_subscription() → ❌ FAILS (DynamoDB down)
```

**Steps:**
1. Mock subscriptions_dal to fail
2. POST /billing/checkout
3. Verify Stripe customer created
4. Verify user record has customer_id
5. Verify no subscription record
6. Verify Lambda returns error (don't hide it)
7. Next attempt can recover

**Expected Result:**
- Known inconsistent state (customer_id but no subscription)
- Webhook will fix it when it arrives
- Logged with enough context to debug
- User retries checkout, succeeds

**Payload:** `partial-failure-customer.json`

---

#### Test: CC-014 — Partial Failure: Subscription Created, Usage Fails
**File:** `integration/partial-failure-usage-fails.integration.test.ts`

**Scenario:**
```
Webhook: checkout.session.completed

1. subscriptions_dal.upsert_subscription() → ✅
2. usage_dal.set_unlimited_usage() → ❌ FAILS
```

**Steps:**
1. Process webhook
2. Mock usage_dal to fail
3. Verify subscription created
4. Verify usage NOT set to 9999
5. Verify Lambda logs error
6. Verify user can't create jobs (old usage limits still apply)
7. Manual fix: Set usage to 9999

**Expected Result:**
- Subscription created but user has old quota
- Error logged for manual intervention
- Monitoring alerts on this failure
- Manual remediation: update usage directly

---

#### Test: CC-015 — Rollback Strategy for Partial Failures
**File:** `integration/partial-failure-rollback.integration.test.ts`

**What it tests:**
Strategy for handling partial failures - rollback or forward?

**Scenarios:**
1. **Rollback:** Delete Stripe customer if DynamoDB fails
2. **Forward:** Leave inconsistency, webhook fixes it
3. **Hybrid:** Rollback if easy, forward if complex

**Steps:**
1. Test each strategy
2. Document which strategy is chosen
3. Verify it's documented in runbook

**Expected Result:**
- Chosen strategy is consistent
- Team knows recovery procedure
- Monitoring alerts on inconsistencies

---

### A6: Stripe State vs Application State Divergence (3 tests)

#### Test: CC-016 — Subscription Cache is Stale
**File:** `integration/subscription-cache-stale.integration.test.ts`

**What it tests:**
Application caches subscription status, but Stripe changed it.

**Scenario:**
```
T=100: subscription.status = "active" (cached, last_updated=T=100)
T=150: User cancels in Stripe dashboard (invoice.payment_failed)
T=160: Application checks (cache, returns "active" - STALE!)
T=170: Webhook arrives with status=past_due
```

**Steps:**
1. Cache subscription as "active"
2. Manually change in Stripe to "past_due"
3. Application checks without webhook yet
4. Verify cache is stale
5. Implement check: if cache >30 min old, query Stripe
6. Verify reconciliation happens

**Expected Result:**
- Detects stale state
- Forces re-query if cache too old
- Or: Always trust Stripe for this check

**Payload:** `subscription-cache-stale.json`

---

#### Test: CC-017 — State Divergence Detection
**File:** `integration/state-divergence-detection.integration.test.ts`

**What it tests:**
Detecting when Stripe and app disagree on state.

**Steps:**
1. Set DynamoDB: subscription.status = "canceled"
2. Set Stripe: subscription.status = "active"
3. Run reconciliation check
4. Verify divergence detected
5. Log warning with details

**Expected Result:**
- Divergence detected (metrics/logs)
- Operator alerted
- Can manually investigate

---

#### Test: CC-018 — Reconciliation Logic
**File:** `integration/state-reconciliation.integration.test.ts`

**What it tests:**
Automatic reconciliation between Stripe and app.

**Strategy:** (Choose one)
- **Option A:** Query Stripe on every check (slower)
- **Option B:** Daily reconciliation job
- **Option C:** Hybrid (cache, but reconcile if flag set)

**Steps:**
1. Implement reconciliation
2. Run against test data
3. Verify Stripe wins (source of truth)
4. Verify DynamoDB updated

**Expected Result:**
- Reconciliation succeeds
- State converges to Stripe state

---

### A7: Lifecycle Edge Cases (2 tests)

#### Test: CC-019 — Re-Subscribe After Cancellation
**File:** `integration/lifecycle-resubscribe-after-cancel.integration.test.ts`

**What it tests:**
User cancels subscription, then upgrades again.

**Steps:**
1. Create subscription (active)
2. Cancel subscription (status=canceled)
3. Attempt new checkout
4. Verify allowed (not blocked by old subscription)
5. Verify new subscription_id created (not reuse old)
6. Verify old subscription_id still marked canceled

**Expected Result:**
- New subscription created with new subscription_id
- Old subscription not reused
- User can have multiple subscription records (churn tracking)

**Payload:** `lifecycle-resubscribe.json`

---

#### Test: CC-020 — Trial Cannot Restart After Subscription
**File:** `unit/lifecycle-trial-no-restart.test.ts`

**What it tests:**
User subscribes, cancels, cannot restart trial.

**Steps:**
1. Trial user: created_at = 60 days ago
2. Upgrade to subscription
3. Cancel subscription
4. Attempt to create job
5. Verify trial expired (not reset)
6. Verify cannot create job (no trial, no subscription)

**Expected Result:**
- Trial is per-user, lifetime (not per-subscription)
- Cannot restart trial after subscription
- Must upgrade again

---

### B1: Performance Tests (2 tests)

#### Test: PERF-001 — Load Test: 100 Concurrent Checkouts
**File:** `perf/load-test-concurrent-checkouts.perf.test.ts`
**Type:** Performance test (run separately, not in CI)

**What it tests:**
System handles 100 concurrent checkout requests.

**Setup:**
```python
import locust

class CheckoutLoadTest(HttpUser):
    @task
    def checkout(self):
        self.client.post(
            "/billing/checkout",
            json={"plan": "monthly", ...},
            headers={"Authorization": f"Bearer {jwt}"}
        )
```

**Metrics to Collect:**
- P50, P95, P99 latency
- Errors (should be 0)
- Stripe API calls per second
- DynamoDB consumed capacity

**Expected Result:**
- P99 latency < 2 seconds
- Zero errors
- No Stripe rate limit (429)
- DynamoDB scales automatically

**Run Command:**
```bash
locust -f perf/load-test-concurrent-checkouts.perf.test.ts \
  --host=https://dev-api.careervp.com \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m
```

---

#### Test: PERF-002 — Subscription Query Performance
**File:** `perf/subscription-query-perf.perf.test.ts`

**What it tests:**
GET /users/me/subscription under load.

**Metrics:**
- Query latency
- DynamoDB reads
- Cache hit rate (if implemented)

**Expected Result:**
- P99 < 100ms (no query)
- Uses GSI (UserSubscriptionIndex)
- No full table scans

---

### B2: Observability Tests (3 tests)

#### Test: OBS-001 — Structured Logging with Correlation ID
**File:** `unit/observability-correlation-id.test.ts`

**What it tests:**
All logs include correlation_id for tracing.

**Steps:**
1. POST /billing/checkout
2. Lambda generates request_id
3. Capture logs from CloudWatch
4. Verify every log includes request_id
5. Verify can search by request_id

**Expected Result:**
```
[2026-03-15T10:30:45Z] request_id=abc123 user_id=user-001 event=checkout_started
[2026-03-15T10:30:46Z] request_id=abc123 user_id=user-001 event=customer_created customer_id=cus_123
[2026-03-15T10:30:47Z] request_id=abc123 user_id=user-001 event=checkout_success
```

**Payload:** `observability-correlation.json`

---

#### Test: OBS-002 — Business Metrics Tracked
**File:** `unit/observability-metrics.test.ts`

**What it tests:**
Key business metrics are tracked and emitted to CloudWatch.

**Metrics to Track:**
```
checkout_attempt: 1
checkout_success: 1
checkout_failure: 1
webhook_received: 1
subscription_activated: 1
access_denied: 1
access_granted: 1
```

**Steps:**
1. Execute operation
2. Verify metric emitted
3. Verify tags included (plan, status, error_code)

**Expected Result:**
```
PUT /cloudwatch/metrics
{
  "Namespace": "CareerVP/Subscription",
  "MetricData": [
    {
      "MetricName": "checkout_attempt",
      "Value": 1,
      "Unit": "Count",
      "Dimensions": [
        {"Name": "Plan", "Value": "monthly"}
      ]
    }
  ]
}
```

---

#### Test: OBS-003 — Alarms on Error Rate Spike
**File:** `ops/alarm-configuration.ops.test.ts`

**What it tests:**
CloudWatch alarms configured for key thresholds.

**Alarms Needed:**
```
- checkout_failure_rate > 5% for 5 minutes
- webhook_processing_error > 10 in 5 minutes
- subscription_state_divergence > 1 event
- lambda_duration_p99 > 2 seconds
- dynamodb_throttle > 0
```

**Steps:**
1. Verify alarms created in CloudWatch
2. Verify SNS topics configured
3. Verify on-call team notified

**Expected Result:**
- All critical alarms configured
- Team notified on alarm
- Runbook linked in alarm description

---

### C1: Security Tests (3 tests)

#### Test: SEC-001 — Webhook Secret Rotation
**File:** `ops/security-webhook-secret-rotation.ops.test.ts`
**Type:** Manual/Operational

**What it tests:**
Procedure for rotating webhook secret without downtime.

**Procedure:**
1. Create new webhook secret in Stripe dashboard
2. Add to SSM (secondary key)
3. Update Lambda to accept both keys
4. Deploy Lambda
5. Update Stripe to use new key
6. Remove old key from Lambda
7. Deploy

**Verification:**
- [ ] Webhook secret stored in Secrets Manager (not Parameter Store)
- [ ] Rotation procedure documented
- [ ] Can support 2 keys simultaneously
- [ ] Old key can be revoked

---

#### Test: SEC-002 — Rate Limiting on Webhook Endpoint
**File:** `unit/security-rate-limit-webhook.test.ts`

**What it tests:**
POST /billing/webhook is rate limited.

**Steps:**
1. Send 101 requests in 1 second (limit=100)
2. Verify 101st request returns 429
3. Verify signature verification happens before rate limit (valid request)

**Expected Result:**
- Rate limit: 100 requests/second per IP
- 429 with Retry-After header
- Logged in CloudWatch

**Configuration:**
```
POST /billing/webhook
  - Throttle: 100 requests/second
  - Burst: 200
  - By: IP address
```

---

#### Test: SEC-003 — No Secrets in Logs
**File:** `unit/security-no-secrets-in-logs.test.ts`

**What it tests:**
Stripe keys, webhook secrets, user PII are never logged.

**Steps:**
1. Execute workflow
2. Capture CloudWatch logs
3. Scan for:
   - `sk_` (secret key)
   - `whsec_` (webhook secret)
   - Plain passwords
   - Credit card numbers
4. Verify none found

**Expected Result:**
- Zero secrets in logs
- Secrets only in Secrets Manager
- Error messages don't leak details

---

### C2: Staging Validation Tests (4 tests)

#### Test: STAGE-001 — Staging Uses Different Secrets
**File:** `ops/staging-validation-different-secrets.ops.test.ts`
**Type:** Manual/Operational

**What it tests:**
Staging environment uses different Stripe account from production.

**Verification:**
- [ ] Staging Stripe key starts with `sk_test_`
- [ ] Production Stripe key starts with `sk_live_`
- [ ] Webhook secret in staging is test account secret
- [ ] Webhook secret in production is live account secret
- [ ] Cannot accidentally hit live Stripe from staging

---

#### Test: STAGE-002 — Smoke Test in Staging
**File:** `ops/staging-smoke-test.ops.test.ts`

**What it tests:**
End-to-end flow in staging before production deployment.

**Procedure:**
1. Deploy to staging
2. Run smoke test:
   - Create test user
   - Checkout
   - Wait for webhook
   - Verify subscription active
   - Create job (should succeed)
3. Verify DynamoDB state
4. Verify CloudWatch logs

**Expected Result:**
- All smoke tests pass
- No errors in staging
- Data looks correct

---

#### Test: STAGE-003 — Canary Deployment Procedure
**File:** `ops/canary-deployment.ops.test.ts`

**What it tests:**
Canary deployment process (10% → 100% traffic).

**Procedure:**
1. Deploy to 10% of Lambda aliases
2. Monitor metrics for 15 minutes
3. Check error rate vs baseline
4. Check latency p99 vs baseline
5. If OK, roll out to 100%
6. If error, rollback

**Rollout Strategy:**
```yaml
DeploymentConfig:
  Type: Canary
  Canary:
    Percent: 10
    Interval: 5  # minutes
```

---

#### Test: STAGE-004 — Rollback Procedure
**File:** `ops/rollback-procedure.ops.test.ts`

**What it tests:**
Ability to quickly rollback to previous Lambda version.

**Procedure:**
1. Update Lambda alias to point to previous version
2. Verify traffic switches
3. Verify metrics normalize
4. Document what went wrong

**Verification:**
- [ ] Rollback procedure documented
- [ ] Can rollback in <5 minutes
- [ ] Previous version tested before rollback
- [ ] Data state recoverable

---

## Implementation Priority

### Phase 1: Critical (Do First) - Week 1
Priority: Fix before any user sees subscription feature

```
A1-001: Concurrent checkout prevention
A1-002: Race condition between check and create
A2-004: Missing subscription record handling
A3-007: Stripe 503 error handling
A5-013: Partial failure recovery
A6-016: Cache stale detection
```

**Why:** Core transaction safety, prevents data corruption

---

### Phase 2: Important (Do Second) - Week 2
Priority: Hardening and edge cases

```
A1-003: Idempotency keys
A2-005: Missing usage record handling
A3-008: Stripe timeout handling
A4-011: Out-of-order webhooks
A7-019: Re-subscribe after cancel
```

**Why:** Resilience, prevents user-facing errors

---

### Phase 3: Desirable (Do Third) - Week 3
Priority: Performance and observability

```
A3-009: Stripe rate limit handling
B1-001: Load test 100 concurrent
B2-001: Structured logging
B2-002: Business metrics
SEC-002: Rate limiting on webhook
```

**Why:** Performance, monitoring, operations

---

### Phase 4: Nice to Have (Optional) - Ongoing
Priority: Security hardening, operational procedures

```
SEC-001: Webhook secret rotation
SEC-003: No secrets in logs
STAGE-001: Different secrets in staging
STAGE-004: Rollback procedure
```

**Why:** Long-term maintainability

---

## Test File Structure

New test directory structure:

```
src/frontend/tests/
├── unit/
│   ├── [existing 13 files]
│   ├── backward-compat-missing-subscription.test.ts (CC-004)
│   ├── backward-compat-missing-usage.test.ts (CC-005)
│   ├── backward-compat-partial-data.test.ts (CC-006)
│   ├── webhook-out-of-order.test.ts (CC-011)
│   ├── webhook-stale-data-out-of-order.test.ts (CC-012)
│   ├── lifecycle-trial-no-restart.test.ts (CC-020)
│   ├── observability-correlation-id.test.ts (OBS-001)
│   └── observability-metrics.test.ts (OBS-002)
│
├── integration/
│   ├── [existing 3 files]
│   ├── concurrent-checkout.integration.test.ts (CC-001)
│   ├── race-condition-check-create.integration.test.ts (CC-002)
│   ├── stripe-idempotency.integration.test.ts (CC-003)
│   ├── stripe-error-503-session.integration.test.ts (CC-007)
│   ├── stripe-error-503-customer.integration.test.ts (CC-008)
│   ├── stripe-timeout.integration.test.ts (CC-009)
│   ├── stripe-rate-limit-429.integration.test.ts (CC-010)
│   ├── partial-failure-customer-created.integration.test.ts (CC-013)
│   ├── partial-failure-usage-fails.integration.test.ts (CC-014)
│   ├── partial-failure-rollback.integration.test.ts (CC-015)
│   ├── subscription-cache-stale.integration.test.ts (CC-016)
│   ├── state-divergence-detection.integration.test.ts (CC-017)
│   ├── state-reconciliation.integration.test.ts (CC-018)
│   └── lifecycle-resubscribe-after-cancel.integration.test.ts (CC-019)
│
├── perf/
│   ├── load-test-concurrent-checkouts.perf.test.ts (PERF-001)
│   └── subscription-query-perf.perf.test.ts (PERF-002)
│
├── ops/
│   ├── alarm-configuration.ops.test.ts (OBS-003)
│   ├── security-webhook-secret-rotation.ops.test.ts (SEC-001)
│   ├── staging-validation-different-secrets.ops.test.ts (STAGE-001)
│   ├── staging-smoke-test.ops.test.ts (STAGE-002)
│   ├── canary-deployment.ops.test.ts (STAGE-003)
│   └── rollback-procedure.ops.test.ts (STAGE-004)
│
├── security/
│   ├── security-rate-limit-webhook.test.ts (SEC-002)
│   └── security-no-secrets-in-logs.test.ts (SEC-003)
│
├── payloads/
│   ├── [existing 22 files]
│   ├── concurrent-checkout-race.json
│   ├── race-window.json
│   ├── idempotency-retry.json
│   ├── backward-compat-old-trial.json
│   ├── backward-compat-missing-usage.json
│   ├── backward-compat-partial-data.json
│   ├── stripe-503-error.json
│   ├── partial-failure-customer.json
│   ├── subscription-cache-stale.json
│   ├── webhook-out-of-order-events.json
│   ├── lifecycle-resubscribe.json
│   └── observability-correlation.json
└── [existing setup.ts, jest.config.ts, etc.]
```

**New Test Count:**
- Unit: +8 tests
- Integration: +14 tests
- Perf: 2 tests
- Ops: 4 tests (manual)
- Security: 2 tests
- **Total: +30 tests**

**New Payloads:**
- +12 new JSON fixtures

---

## Implementation Steps

### Step 1: Create Test Structure
Create all test files as EMPTY TESTS (will fail initially)

```typescript
describe('CC-001: Concurrent Checkout Prevention', () => {
  it('should prevent duplicate customers on concurrent checkout', async () => {
    // TODO: Implement test
    expect(true).toBe(false);  // Placeholder, will fail
  });
});
```

**Why:** Placeholder forces developer to implement tests before feature code

---

### Step 2: Define Payloads
Create all JSON payloads with realistic test data

---

### Step 3: Implement Tests
Implement each test to verify specific behavior

**Run command:**
```bash
npm run test:critical
```

**Expected:** All 30+ tests FAIL initially (feature not hardened yet)

---

### Step 4: Implement Hardening
Implement feature code to make tests pass

**Priority:** Phase 1 tests first (transaction safety)

---

### Step 5: Run Test Suite
Verify all tests pass

**Final check:**
```bash
npm run test:unit          # Original 26 + new 14 = 40
npm run test:integration   # Original 3 + new 14 = 17
npm run test:coverage      # >80% coverage
npm test:critical          # New critical tests (30+)
```

---

## Success Criteria

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Test Pass Rate | 100% | All tests green |
| Coverage | >85% | npm run test:coverage |
| Critical Issues Fixed | 100% | CRITICAL_CONSIDERATIONS addressed |
| Performance | <2s p99 | PERF tests pass |
| Observability | Complete | OBS tests pass |
| Security | Hardened | SEC tests pass |

---

## Proceeding to Implementation

Once this plan is approved:

1. **Week 1:** Create test skeletons + payloads (agent job)
2. **Week 1:** Implement Phase 1 tests (critical)
3. **Week 2:** Implement feature hardening (dev job)
4. **Week 2:** Verify Phase 1 tests pass
5. **Week 3:** Implement Phase 2-3 tests
6. **Week 4:** Full system validation
7. **Week 4:** Production deployment

---

## Questions Before Implementation?

- Which test categories should be automated vs manual?
- Should performance tests run in CI or separately?
- Which Phase 1 tests are most important?
- Should we skip any test categories (ops, security)?

