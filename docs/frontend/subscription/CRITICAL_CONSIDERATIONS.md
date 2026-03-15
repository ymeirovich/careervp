# Subscription Service Implementation — Critical Considerations You Might Be Missing

This document identifies important aspects of the subscription service that are NOT explicitly tested but are critical to success.

---

## 1. Transaction Safety & Idempotency

### The Problem You Haven't Explicitly Tested:

```
Scenario: User clicks "Upgrade" button twice rapidly

Webhook arrives: checkout.session.completed
Lambda processes: subscription created, usage set to 9999
Lambda returns: 200 OK

User clicks again before redirect
Webhook arrives AGAIN: checkout.session.completed (duplicate)
Lambda processes AGAIN: subscription created with upsert...

Result: No duplicate subscription, but what if intermediate state is observed?
```

### What Tests Do:
✓ Webhook idempotency regression test (F-SUB-011-R)

### What Tests Don't Do:
✗ Concurrent requests to /billing/checkout
✗ Race conditions between webhook and API calls
✗ Transaction isolation levels

### You Need to Consider:

```python
# WRONG - Race condition possible:
def handle_checkout_post(user_id):
    if check_subscription_active(user_id):  # Check
        raise 409
    # <-- Race condition window: user can upgrade twice
    return create_checkout_session(user_id)  # Action

# RIGHT - Atomic or scoped correctly:
def handle_checkout_post(user_id):
    # One of these approaches:
    # 1. DynamoDB conditional update: fails if subscription exists
    # 2. Pessimistic lock with dynamodb.update_item(ConditionExpression)
    # 3. Unique constraint on user_id in subscriptions table
    return create_checkout_session_safely(user_id)
```

### What to Verify:
- [ ] DynamoDB has condition expressions for critical updates
- [ ] No window between check and action
- [ ] Concurrent requests to same endpoint don't create duplicates
- [ ] Plan changes are atomic

---

## 2. Backward Compatibility & Data Migration

### The Problem:

You're adding subscriptions to an existing system with 1000s of trial users.

```
Day 1 (Before): Users have Usage records with remaining=3
Day 2 (Deploy): Users now have Subscription records

What happens to old trial users without Subscription records?
  - Tests assume Subscription is queried
  - If missing, does check_trial_and_quota() crash or degrade?
  - Do existing applications stop working?
```

### What Tests Do:
✓ Tests assume User/Usage/Subscription all exist correctly

### What Tests Don't Do:
✗ Missing Subscription record (old trial user)
✗ Missing Usage record (corrupted data)
✗ Partial migrations (half upgraded, half not)

### You Need to Do:

```python
# DEFENSIVE - Handle missing records:
def check_trial_and_quota(user_id: str) -> None:
    # Safe: handles missing Subscription gracefully
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    if sub and sub.is_active:
        return

    # Must handle missing User/Usage from old data
    user = users_dal.get_user(user_id)  # What if doesn't exist?
    if not user:
        raise ApiError(500, "user_not_found", "User record missing")

    usage = usage_dal.get_usage(user_id)  # What if doesn't exist?
    if not usage:
        # Create on-the-fly? Or fail?
        raise ApiError(500, "usage_not_found", "Usage record missing")
```

### What to Verify:
- [ ] Graceful handling if Subscription record missing (trial user)
- [ ] Graceful handling if Usage record missing (corrupted data)
- [ ] Data migration script exists (if needed)
- [ ] Rollback procedure defined (in case of bad migration)

---

## 3. Eventual Consistency & Timing Windows

### The Problem:

```
User completes Stripe checkout at 10:00:00
Webhook delivered at 10:00:05 (5 second delay, normal)
User redirected to /billing/success at 10:00:01

GET /users/me/subscription at 10:00:01
Returns: has_active_subscription = false (webhook not processed yet!)

User sees "Upgrade failed" even though it will succeed in 4 seconds
```

### What Tests Do:
✓ Tests assume webhook is processed immediately (mocked)

### What Tests Don't Do:
✗ Simulates real webhook delay (5-30 seconds typical)
✗ Tests what UI shows before webhook arrives

### You Need to Handle:

```typescript
// Frontend polling after checkout completion:
useEffect(() => {
  const pollSubscriptionStatus = setInterval(async () => {
    const response = await fetch('/users/me/subscription');
    if (response.subscription?.status === 'active') {
      setUpgraded(true);
      clearInterval(pollSubscriptionStatus);
    }
  }, 1000); // Poll every second

  setTimeout(() => clearInterval(pollSubscriptionStatus), 60000); // Timeout after 60s
}, [checkoutSessionId]);

// Show "Processing..." message, not "Failed"
```

### What to Verify:
- [ ] Frontend polls subscription status after redirect
- [ ] Handles case where webhook hasn't arrived yet
- [ ] Timeout if webhook doesn't arrive within 60 seconds
- [ ] Error messaging distinguishes between "processing" and "failed"

---

## 4. Stripe API Errors & Resilience

### The Problem:

```
Scenario: Stripe API down (happens 1-2x per year)

Lambda calls: stripe.checkout.Session.create()
Stripe returns: 503 Service Unavailable

Lambda response: 500 Internal Server Error (correct)
User sees: "Something went wrong"
User tries again in 10 seconds

Result: Two checkout sessions created for same user!
  - No subscription duplicate (409 blocks it)
  - But two sessions both active (user confusion)
```

### What Tests Do:
✓ Success path tested
✓ Normal errors tested (invalid plan, existing subscription)

### What Tests Don't Do:
✗ Stripe API errors (5xx)
✗ Timeouts
✗ Transient failures with retry logic
✗ Idempotency keys for replay safety

### You Need to Consider:

```python
import stripe
from stripe.error import StripeError

def handle_checkout_post(event, context):
    # Add idempotency key to Stripe calls
    idempotency_key = f"checkout_{user_id}_{request_id}"

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[...],
            mode='subscription',
            idempotency_key=idempotency_key,  # <-- Critical!
            success_url=body['success_url'],
            cancel_url=body['cancel_url'],
        )
        return {'statusCode': 200, 'body': json.dumps({'checkout_url': session.url})}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        # Stripe will deduplicate if called again with same idempotency_key
        return {'statusCode': 503, 'body': json.dumps({'error': 'payment_provider_error'})}
```

### What to Verify:
- [ ] Stripe calls include idempotency_key
- [ ] Timeouts set appropriately (10s max)
- [ ] Stripe errors logged with enough context for debugging
- [ ] User gets 503 (retry later) not 500 (internal error) for provider errors

---

## 5. Webhook Delivery Guarantees

### The Problem:

```
Stripe guarantees: "We will retry for 3 days with exponential backoff"
Stripe does NOT guarantee: "Delivered exactly once per account"

Reality: Webhooks can be delivered:
  - Multiple times (network retry, timeout)
  - Out of order (plan change before payment confirmed)
  - Slowly (30+ seconds after event)
  - Never (webhook endpoint misconfigured, silently dropped)
```

### What Tests Do:
✓ Idempotency test (same event twice)
✓ Signature verification

### What Tests Don't Do:
✗ Out-of-order webhooks
✗ Webhook delivery failure scenarios
✗ Monitoring for missing webhooks
✗ Long delays between event and delivery

### You Need to Consider:

```python
# Track webhook processing
def handle_webhook_post(event, context):
    webhook_event = stripe.Webhook.construct_event(body, sig_header, secret)

    # Log immediately
    logger.info(f"Webhook received: {webhook_event['type']} id={webhook_event['id']}")

    # Store event ID to detect duplicates
    if webhook_handlers.is_duplicate(webhook_event['id']):
        logger.warn(f"Duplicate webhook: {webhook_event['id']}")
        return {'statusCode': 200}  # Return 200 even if duplicate

    webhook_handlers.mark_processed(webhook_event['id'])

    # Process idempotently
    handler(webhook_event)
    return {'statusCode': 200}
```

### Monitoring to Add:
- [ ] CloudWatch metric: Webhooks received per event type
- [ ] CloudWatch metric: Time between Stripe event and webhook delivery
- [ ] CloudWatch alarm: No checkout.session.completed for 1 hour
- [ ] Scheduled task: Scan for Stripe events not yet delivered (Stripe event API)

---

## 6. Data Consistency Across Boundaries

### The Problem:

```
You have 3 tables:
  1. careervp-users-{stage}
  2. careervp-usage-{stage}
  3. careervp-subscriptions-{stage}

Scenario: Create subscription fails AFTER creating customer in Stripe

Lambda:
  1. stripe.Customer.create() ✓
  2. users_dal.update_stripe_customer_id() ✓
  3. stripe.checkout.Session.create() ✓
  4. subscriptions_dal.create_subscription() ✗ (DynamoDB down)

Result: Stripe has customer, User has customer_id, but no Subscription record!
Next request:
  - Checkout blocked by "customer already has..." message? (no subscription)
  - Or checkout succeeds again? (no subscription found)
```

### What Tests Do:
✓ Happy path (all succeed)
✓ Individual call failures caught

### What Tests Don't Do:
✗ Partial failures mid-flow
✗ Rollback procedures
✗ Stripe state vs DynamoDB state mismatch

### You Need to Handle:

```python
def handle_checkout_post(event, context):
    try:
        # Get or create Stripe customer
        customer_id = get_or_create_stripe_customer(user_id)

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            # ...
        )

        # Store checkout URL in cache (in case of later failure)
        cache.set(f"checkout_{user_id}_{session.id}", session.url, ttl=30m)

        return {'statusCode': 200, 'body': json.dumps({'checkout_url': session.url})}

    except Exception as e:
        # Don't fail silently
        logger.error(f"Checkout creation failed: {e}")

        # Can we recover?
        if customer_id and stripe_session_exists(customer_id):
            # Stripe customer exists but not in DynamoDB
            # This is OK - next webhook will create subscription
            return {'statusCode': 200, 'body': json.dumps({'checkout_url': cached_url})}
        else:
            # Unknown state
            raise
```

### What to Verify:
- [ ] Customer creation independent of checkout session creation
- [ ] Subscription creation independent of checkout session
- [ ] Can recover from partial failures
- [ ] CloudWatch logs show exact point of failure

---

## 7. Stripe State vs Application State Divergence

### The Problem:

```
Stripe reports: Subscription active, current_period_end = 2026-04-15
Application reports: Subscription canceled

Who is right? It depends when you last synced!

User should be blocked from creating jobs, but if your cached state
says "canceled" and Stripe says "active", who wins?
```

### What Tests Do:
✓ Assume application state matches Stripe (via webhook)

### What Tests Don't Do:
✗ Stale cache scenarios
✗ Webhook delivery gaps
✗ Manual Stripe changes (via dashboard or API)

### You Need to Consider:

```python
# Option 1: Trust Stripe as source of truth
# Call stripe.Subscription.retrieve(sub_id) on every quota check
# Pro: Always correct; Con: Slower, higher Stripe API costs

# Option 2: Trust webhooks, reconcile periodically
# Cache from webhook, but reconcile once per day
def reconcile_subscription_state():
    subscriptions = subscriptions_dal.query_all()
    for sub in subscriptions:
        stripe_sub = stripe.Subscription.retrieve(sub.subscription_id)
        if sub.status != stripe_sub.status:
            logger.warn(f"State divergence detected: {sub.subscription_id}")
            sub.status = stripe_sub.status
            subscriptions_dal.update_subscription(sub)

# Option 3: Trust webhooks, but add timeout
# If no webhook in 30 days, block access (force reconciliation)
if subscription.updated_at < now() - 30.days:
    # Force re-query Stripe
    stripe_sub = stripe.Subscription.retrieve(sub.subscription_id)
    if stripe_sub.status != sub.status:
        raise ApiError(409, "subscription_state_stale", "Please refresh your session")
```

### What to Verify:
- [ ] Document your strategy: Trust Stripe? Cache? Reconcile?
- [ ] If caching, document reconciliation strategy
- [ ] If trusting webhooks, monitor for gaps (CloudWatch)
- [ ] Add comments in code explaining choice

---

## 8. Customer & Subscription Lifecycle Edge Cases

### The Problem:

Stripe Customer has 3 lifecycle states:
1. **New Customer:** Created but no subscription yet
2. **Active Subscription:** Has active subscription
3. **Inactive/Deleted:** Subscription ended, customer still exists

Your system only tests states 1→2. What about 2→3?

```
Scenario: User cancels subscription in Stripe dashboard

Stripe webhook: customer.subscription.deleted
Lambda sets: subscription.status = canceled

User tries to upgrade again:
  - Does /billing/checkout work?
  - Does check_trial_and_quota() block them?
  - Can they restart trial? (No, trial already used)
```

### What Tests Do:
✓ Upgrade (new customer)
✓ Cancellation received
✓ Blocks access when canceled

### What Tests Don't Do:
✗ Re-subscribe after cancellation
✗ Manual refund in Stripe
✗ Trial restart after subscription ends
✗ Multiple subscriptions over time (churn scenario)

### You Need to Consider:

```python
def handle_checkout_post(event, context):
    # Old logic: Prevent duplicate subscription
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    if sub and sub.status == SubscriptionStatus.ACTIVE:
        raise 409

    # NEW: Allow re-subscribe if previous was canceled
    if sub and sub.status in [SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED]:
        # User can re-subscribe
        # Create new subscription record (don't update old)
        pass

    return create_checkout_session(user_id)
```

### What to Verify:
- [ ] Can re-subscribe after cancellation
- [ ] Re-subscription creates new subscription_id (doesn't reuse old)
- [ ] Trial is NOT reset (trial is per-user, lifetime)
- [ ] Churn metrics tracked (customers who unsubscribed then resubscribed)

---

## 9. Performance & Cost Optimization

### The Problem:

Your spec says:

> Lambda `careervp-billing-{stage}` calls `stripe.Subscription.retrieve(subscription_id)` to get full subscription object.

This is correct, but:
- Every checkout.session.completed webhook calls this (adds 200ms latency)
- Stripe API has rate limits (100 RPS for test keys, 1000 RPS for live)
- Cost: Each Stripe API call costs request units

### What Tests Do:
✓ Correct behavior (calls Stripe)

### What Tests Don't Do:
✗ Performance under load (100 concurrent checkouts)
✗ Stripe rate limit handling
✗ Cost calculation

### You Need to Consider:

```python
# Option 1: Pre-cache from Stripe
# Stripe returns full subscription object in checkout.session.completed
# Use it directly, don't call Subscription.retrieve()

def handle_checkout_session_completed(session_data):
    # Get subscription ID from session
    subscription_id = session_data['subscription']

    # DON'T call: stripe.Subscription.retrieve(subscription_id)
    # Instead, request full subscription in checkout creation:

def handle_checkout_post(event, context):
    session = stripe.checkout.Session.create(
        ...,
        expand=['subscription'],  # <-- Get full subscription in response
    )
    # Now session.subscription has full object

# Option 2: Cache with TTL
subscriptions_cache = {}  # Simple in-memory cache

def get_subscription_with_cache(subscription_id):
    if subscription_id in subscriptions_cache:
        cached = subscriptions_cache[subscription_id]
        if cached['expires_at'] > now():
            return cached['data']

    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    subscriptions_cache[subscription_id] = {
        'data': stripe_sub,
        'expires_at': now() + 5.minutes
    }
    return stripe_sub
```

### What to Verify:
- [ ] No unnecessary Stripe API calls (expand fields instead)
- [ ] Load test with 100 concurrent checkouts
- [ ] Monitor Stripe API quota usage
- [ ] Document performance characteristics (p50, p99 latency)

---

## 10. Observability & Debugging

### The Problem:

Six months from now, you get a bug report:

> "Some users can't upgrade. They see error 500."

Where do you look?
- CloudWatch logs are verbose, hard to search
- DynamoDB shows no failed items
- Stripe logs show successful sessions

### What Tests Do:
✓ Log errors on failure

### What Tests Don't Do:
✗ Structured logging
✗ Correlation IDs
✗ Business metrics
✗ Alerting on key thresholds

### You Need to Add:

```python
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger()
tracer = Tracer()
metrics = Metrics()

@tracer.capture_lambda_handler
def handle_checkout_post(event, context):
    user_id = get_user_id_from_event(event)
    request_id = event.get('requestContext', {}).get('requestId', 'unknown')

    # Structured logging with context
    logger.info(
        "Checkout initiated",
        extra={
            'user_id': user_id,
            'request_id': request_id,
            'plan': event['body']['plan'],
        }
    )

    try:
        metrics.add_metric('checkout_attempt', 1, 'Count')
        # ... implementation
        metrics.add_metric('checkout_success', 1, 'Count')
    except Exception as e:
        metrics.add_metric('checkout_failure', 1, 'Count')
        logger.exception("Checkout failed", extra={'user_id': user_id})
        raise

# CloudWatch Insights query:
# fields @timestamp, user_id, request_id, @message
# | filter plan="monthly"
# | stats count() by user_id
```

### What to Verify:
- [ ] All key operations logged (checkout, subscription created, access denied)
- [ ] Logs include request ID for correlation
- [ ] Business metrics tracked (checkouts, subscriptions, access denials)
- [ ] Alarms configured for error rates
- [ ] Dashboard shows key metrics

---

## 11. Security: Beyond Signature Verification

### The Problem:

Your spec verifies Stripe webhook signatures ✓

But:

```
Scenario 1: Webhook signature key rotated
  - Old key in code, Stripe sends with new key
  - Signature verification fails
  - Webhooks silently dropped
  - No alert!

Scenario 2: Webhook endpoint publicly known
  - Anyone can call POST /billing/webhook
  - Signature verification catches invalid signatures ✓
  - But attackers can brute-force signatures (weak if key exposed)

Scenario 3: Man-in-the-middle attack
  - HTTPS protects in-flight data
  - But API Gateway SSL/TLS misconfiguration could expose
```

### What Tests Do:
✓ Signature verification required
✓ Invalid signature returns 400

### What Tests Don't Do:
✗ Webhook secret rotation
✗ Key management practices
✗ Network security (TLS, cert pinning)
✗ Rate limiting on webhook endpoint

### You Need to Verify:
- [ ] Webhook secret is in AWS Secrets Manager (not Parameter Store)
- [ ] Secret rotation procedure documented
- [ ] API Gateway enforces HTTPS (not HTTP)
- [ ] Rate limiting on /billing/webhook (e.g., 100 req/sec per IP)
- [ ] No public access logs expose webhook paths
- [ ] Webhook endpoint is not in any public documentation

---

## 12. Testing in Staging Before Production

### The Problem:

Your tests are complete and pass. You deploy to production.

```
Real Stripe Account: stripe_sk_live_...
Real AWS Account: prod region

New subscriber checks out: Succeeds
Webhook arrives: Stripe sends to https://api.careervp.com/billing/webhook
Lambda invokes: Production database updated

...but webhook signing secret in Lambda is from DEV account!
Signature verification fails
Webhook silently dropped
Subscription never activated!
```

### What Tests Do:
✓ Test with test mode keys

### What Tests Don't Do:
✗ Staging environment validation
✗ Production key rotation verification
✗ Canary deployment testing
✗ Rollback procedure testing

### You Need to Do:

```
Deployment Checklist:
  [ ] Deploy to staging first
  [ ] Run integration tests in staging (not mocked)
  [ ] Run smoke tests with Stripe test account
  [ ] Verify /billing/webhook accessible from Stripe IP range
  [ ] Verify webhook signing secret in SSM Parameter Store
  [ ] Create 1 test subscription in staging, verify webhook delivered
  [ ] Canary deploy to production (10% traffic)
  [ ] Monitor error rates and latency (30 minutes)
  [ ] Roll out to 100% if no errors
  [ ] Monitor production for 1 hour post-deployment
  [ ] Have rollback plan ready (previous Lambda version)
```

### What to Verify:
- [ ] Staging environment is separate from production
- [ ] Secrets in staging are DIFFERENT from production
- [ ] Deployment procedure includes staging validation
- [ ] Rollback procedure documented and tested
- [ ] Canary deployment configured in CI/CD

---

## Summary: Critical Considerations Checklist

Before declaring the feature "production ready," verify:

### Data & Transactions
- [ ] Race conditions prevented (concurrent updates)
- [ ] Backward compatibility maintained (old data doesn't break)
- [ ] Partial failure recovery understood
- [ ] Stripe state vs app state divergence handled

### Resilience & Errors
- [ ] Stripe API errors don't duplicate subscriptions
- [ ] Idempotency keys used for Stripe calls
- [ ] Webhook delivery gaps detected
- [ ] Timeouts configured appropriately

### Performance
- [ ] No unnecessary Stripe API calls
- [ ] Load tested (100+ concurrent checkouts)
- [ ] Lambda cold start <3 seconds
- [ ] DynamoDB queries <100ms p99

### Observability
- [ ] Structured logging with correlation IDs
- [ ] Business metrics tracked
- [ ] Alarms configured for error rates
- [ ] Dashboard shows subscription health

### Security
- [ ] Webhook secrets in Secrets Manager
- [ ] HTTPS enforced
- [ ] Rate limiting on public endpoints
- [ ] Keys rotated securely

### Deployment & Operations
- [ ] Staging environment validated
- [ ] Canary deployment procedure
- [ ] Rollback procedure tested
- [ ] On-call runbook created

### Testing
- [ ] All 129 tests passing
- [ ] >80% code coverage
- [ ] Smoke tests in staging
- [ ] E2E tests with real Stripe test account

---

These 12 considerations are critical to a successful, maintainable subscription service. Don't skip them.

