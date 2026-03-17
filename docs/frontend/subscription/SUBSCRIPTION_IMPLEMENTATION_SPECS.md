# Subscription Service Implementation Specifications

**Purpose:** Implementation specifications that map to the test suite in `SUBSCRIPTION_FEATURE_TEST_PROMPT.md`. Each specification guarantees unit, integration, E2E, and regression tests will pass.

**Output audience:** Backend developers implementing subscription features, code generation agents.

**Prerequisite:** All tests in `src/frontend/tests/` must pass AND all Python tests in `src/backend/tests/unit/test_subscription_repository.py`, `test_billing_service.py`, `test_webhook_service.py`, `test_quota_service.py` must pass.

**Constraints:**
- No breaking changes to existing CareerVP APIs.
- `DB_SINGLE_TABLE` rule: all new records go into the **existing users table** (`TABLE_NAME` env var). No new DynamoDB tables.
- All code must comply with `docs/best_practices/yaml/`.
- Payment processor is **not yet determined**. Use `PaymentProviderInterface` (`src/backend/careervp/payment_providers/interface.py`). Never reference Stripe directly in business logic or tests.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Model — Single Table Design](#data-model--single-table-design)
3. [Payment Provider Abstraction](#payment-provider-abstraction)
4. [Implementation Groups](#implementation-groups)
   - [Group 1: Trial & Quota Foundation (S-001)](#group-1-trial--quota-foundation-s-001)
   - [Group 2: Checkout Flow (S-002)](#group-2-checkout-flow-s-002)
   - [Group 3: Subscription Lifecycle (S-003)](#group-3-subscription-lifecycle-s-003)
   - [Group 4: Webhooks & Billing Events (S-004)](#group-4-webhooks--billing-events-s-004)
   - [Group 5: Portal & Access Control (S-005)](#group-5-portal--access-control-s-005)
5. [Infrastructure (S-006)](#infrastructure-s-006)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Error Handling & Status Codes](#error-handling--status-codes)
8. [Regression Prevention Checklist](#regression-prevention-checklist)

---

## Architecture Overview

### Request-Response Pipeline

```
Client HTTP Request
    ↓
API Gateway (CORS, raw body passthrough for webhooks — see S-006.1)
    ↓
Cognito Authorizer (validates JWT; skipped for webhooks)
    ↓
Lambda Handler (careervp-billing-lambda-{env})
    ↓
BillingService / WebhookService / QuotaService (logic layer)
    ↓
SubscriptionRepository + UserRepository (DAL layer)
    ↓
DynamoDB — users table (single table, existing)  ←── NO NEW TABLES
    ↓
Response Builder (CORS, error formatting)
    ↓
Client HTTP Response
```

### Handler Factory Pattern

```python
# src/backend/careervp/handlers/billing_handler.py

def _get_billing_service() -> BillingService:
    """Cold-start factory. Swap PlaceholderPaymentProvider for real provider."""
    return BillingService(
        subscription_repo=SubscriptionRepository(),
        user_repo=UserRepository(),
        # TODO: replace PlaceholderPaymentProvider with real provider
        payment_provider=PlaceholderPaymentProvider(),
    )
```

---

## Data Model — Single Table Design

All subscription data lives in the **existing users table** (`TABLE_NAME` env var).
This complies with `DB_SINGLE_TABLE` and adds zero new infrastructure.

### Sort Key Patterns (users table)

| Sort Key               | Contents                                   | Existing?       |
|------------------------|--------------------------------------------|-----------------|
| `PROFILE`              | user_id, email, name, customer_id          | Yes (extended)  |
| `TRIAL`                | application_count, trial_active, created_at | Yes            |
| `SUBSCRIPTION#CURRENT` | full subscription state                    | **New**         |
| `USAGE`                | remaining credits (9999 = unlimited)       | **New**         |

### customer_id Field

Stored on the `PROFILE` row (`pk=USER#{user_id}`, `sk=PROFILE`), in the `customer_id` attribute.
This replaces the old `stripe_customer_id` field name.

### SUBSCRIPTION#CURRENT Item Schema

```python
{
    "pk": "USER#{user_id}",          # DB_PK_NAMING
    "sk": "SUBSCRIPTION#CURRENT",    # DB_SK_PREFIX_PATTERN
    "user_id": str,                  # redundant but useful for GSI projections
    "subscription_id": str,          # payment provider subscription ID
    "customer_id": str,              # payment provider customer ID
    "status": str,                   # "active" | "past_due" | "canceled" | "expired"
    "plan": str,                     # "monthly" | "quarterly"
    "stripe_price_id": str,          # provider price/product ID (keep field name for compatibility)
    "current_period_start": str,     # ISO 8601
    "current_period_end": str,       # ISO 8601
    "cancel_at_period_end": bool,
    "trial_end": str | None,         # ISO 8601 or null
    "canceled_at": str | None,       # ISO 8601 or null
    "payment_failed_count": int,     # 0 normally; increments on invoice.payment_failed
    "stripe_event_created": int,     # unix timestamp of last webhook event applied (for ordering)
    "created_at": str,               # ISO 8601
    "updated_at": str,               # ISO 8601
}
```

### USAGE Item Schema

```python
{
    "pk": "USER#{user_id}",
    "sk": "USAGE",
    "user_id": str,
    "remaining": int,      # trial credits; 9999 = unlimited (subscribed)
    "updated_at": str,
}
```

### Payment Event Deduplication (idempotency table)

Webhook deduplication uses the **existing idempotency table** (`IDEMPOTENCY_TABLE_NAME`):

```python
{
    "pk": "PAYMENT_EVENT#{event_id}",
    "sk": "EVENT_TYPE#{event_type}",
    "event_id": str,
    "event_type": str,
    "created_at": str,
    "expiration": int,  # TTL — 7 days
}
```

### Checkout Lock (idempotency table — FIX: Issue 1)

Concurrent checkout prevention uses the **same idempotency table** so TTL is already active:

```python
{
    "pk": "CHECKOUT_LOCK#{user_id}",
    "sk": "LOCK",
    "user_id": str,
    "created_at": str,
    "expiration": int,  # TTL — 1 hour (CHECKOUT_LOCK_TTL_SECONDS = 3600)
}
```

**Why the idempotency table:** The users table does not have TTL configured on any attribute.
The idempotency table has `time_to_live_attribute="expiration"` in CDK (`api_db_construct.py:137`).
Storing checkout locks there gives automatic cleanup with no schema changes.

---

## Payment Provider Abstraction

**Never** import Stripe (or any payment SDK) in business logic or tests.
All payment operations go through `PaymentProviderInterface`.

### Interface Location

```
src/backend/careervp/payment_providers/
├── __init__.py            # exports
├── interface.py           # PaymentProviderInterface Protocol + DTOs
└── placeholder.py         # PlaceholderPaymentProvider (dev/test stub)
```

### How to Add a Real Provider

1. Create `src/backend/careervp/payment_providers/stripe_provider.py`
2. Implement `PaymentProviderInterface` — translate each method to Stripe SDK calls
3. Set `PAYMENT_PROVIDER=stripe` env var
4. In `billing_handler.py` factory, swap `PlaceholderPaymentProvider()` for `StripePaymentProvider()`

### Test Mocking Pattern

```python
# Python test pattern — always mock the interface, not the SDK
payment_provider = MagicMock(spec=PaymentProviderInterface)
payment_provider.create_customer.return_value = CustomerRecord(
    customer_id='cus_test001', email='test@example.com'
)
payment_provider.create_checkout_session.return_value = CheckoutSession(
    session_id='cs_test001',
    checkout_url='https://checkout.example.com/pay/cs_test001',
    customer_id='cus_test001',
)
```

```typescript
// TypeScript test pattern
const mockPaymentProvider = {
  createCustomer: jest.fn(),
  createCheckoutSession: jest.fn(),
  createPortalSession: jest.fn(),
  constructWebhookEvent: jest.fn(),
  retrieveSubscription: jest.fn(),
  getPriceMap: jest.fn(),
};
```

---

## Implementation Groups

### Group 1: Trial & Quota Foundation (S-001)

**Maps to Tests:** F-SUB-001, F-SUB-002, F-SUB-003
**Unit Tests:** `src/frontend/tests/unit/trial.test.ts`, `src/backend/tests/unit/test_quota_service.py`

#### S-001.1: QuotaService

**File:** `src/backend/careervp/logic/quota_service.py`

```python
class QuotaService:
    BLOCKED_STATUSES = frozenset({'past_due', 'canceled', 'expired'})

    def __init__(self, subscription_repo: SubscriptionRepository, trial_service: TrialService):
        self._sub_repo = subscription_repo
        self._trial = trial_service

    def check_access(self, user_id: str) -> None:
        """Raise QuotaError if user cannot create a new application.

        Call this at the top of POST /jobs and POST /gap-analyses.
        """
        sub_result = self._sub_repo.get_subscription(user_id)
        sub = sub_result.data if sub_result.success else None

        if sub:
            status = sub.get('status', '')
            if status == 'active':
                return  # Active subscriber — unlimited access
            if status in self.BLOCKED_STATUSES:
                raise QuotaError(403, 'subscription_required',
                    'Your subscription is inactive. Please update your payment method.')

        # No subscription or non-blocked status → trial enforcement
        usage = self._trial.get_usage(user_id)
        if not usage.get('trial_active', False):
            raise QuotaError(403, 'trial_expired', 'Your trial has ended. Please subscribe.')
        if usage.get('credits_remaining', 0) <= 0:
            raise QuotaError(403, 'trial_exhausted',
                'You have used all trial applications. Please subscribe.')
```

**Invocation:** At the top of `POST /jobs` and `POST /gap-analyses` handler.

**DynamoDB access:** Single `get_item(pk=USER#{user_id}, sk=SUBSCRIPTION#CURRENT)`.

---

### Group 2: Checkout Flow (S-002)

**Maps to Tests:** F-SUB-004, F-SUB-005, F-SUB-006, CC-001
**Unit Tests:** `src/frontend/tests/unit/checkout.test.ts`, `src/backend/tests/unit/test_billing_service.py`
**Integration Tests:** `src/frontend/tests/integration/concurrent-checkout.integration.test.ts`

#### S-002.1: POST /billing/checkout

**File:** `src/backend/careervp/handlers/billing_handler.py`

**Request Body:**
```json
{
  "plan": "monthly" | "quarterly",
  "success_url": "https://app.careervp.com/billing/success",
  "cancel_url": "https://app.careervp.com/billing/cancel"
}
```

**Response (200):**
```json
{ "checkout_url": "https://..." }
```

**Implementation:**
```python
def handle_checkout(self, user_id: str, plan: str, success_url: str, cancel_url: str) -> dict:
    if plan not in ('monthly', 'quarterly'):
        return {'status_code': 400, 'error': f"Invalid plan '{plan}'"}
    if not success_url or not cancel_url:
        return {'status_code': 400, 'error': 'success_url and cancel_url are required'}

    # F-SUB-006: block active subscribers
    sub_result = self._sub_repo.get_subscription(user_id)
    sub = sub_result.data if sub_result.success else None
    if sub and sub.get('status') == 'active':
        return {'status_code': 409, 'error': 'User already has an active subscription'}

    # F-SUB-005: reuse existing customer
    customer_id = self._sub_repo.get_customer_id(user_id)
    if not customer_id:
        # CC-001: atomic lock prevents concurrent duplicate customer creation
        try:
            self._sub_repo.create_checkout_intent(user_id)
        except ClientError:
            return {'status_code': 409, 'error': 'checkout_in_progress',
                    'message': 'Another checkout is in progress. Please try again shortly.'}

        try:
            user = self._user_repo.get_user(user_id)
            customer = self._payment_provider.create_customer(
                email=user.email if user else '',
                metadata={'user_id': user_id},
            )
            customer_id = customer.customer_id
            self._sub_repo.update_customer_id(user_id, customer_id)
        finally:
            # ALWAYS release the lock — TTL is the last-resort safety net only
            self._sub_repo.release_checkout_intent(user_id)

    price_map = self._payment_provider.get_price_map()
    session = self._payment_provider.create_checkout_session(
        customer_id=customer_id,
        price_id=price_map[plan],
        plan=plan,
        user_id=user_id,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {'status_code': 200, 'checkout_url': session.checkout_url}
```

#### S-002.2: Checkout Lock Lifecycle (FIX: Issue 1)

**Problem:** Without cleanup, `create_checkout_intent` writes a lock record
(`CHECKOUT_LOCK#{user_id}`) that persists forever.  A canceled user who tries
to re-subscribe gets `ConditionalCheckFailedException` on every attempt.

**Solution:** Three-layer cleanup:

| Layer | Mechanism | When it fires |
|-------|-----------|---------------|
| 1 (fast path) | `finally: release_checkout_intent(user_id)` | Every handler exit |
| 2 (TTL) | `expiration = now + 3600` on idempotency table | Up to 48 h after Lambda crash |
| 3 (idempotency table) | Stored in idempotency table which has TTL enabled | Same as layer 2 |

**Why the idempotency table (not the users table):**
The users table (`api_db_construct.py:_build_users_table`) has no TTL attribute.
The idempotency table has `time_to_live_attribute="expiration"` already in CDK.
Storing the lock there requires no infrastructure changes.

**DAL methods already in `SubscriptionRepository`:**
- `create_checkout_intent(user_id, ttl_seconds=3600)` — conditional put, raises `ClientError` on conflict
- `release_checkout_intent(user_id)` — delete_item, safe to call when lock is absent

**DynamoDB writes:** `put_item` / `delete_item` on idempotency table at
`pk=CHECKOUT_LOCK#{user_id}`, `sk=LOCK`.

---

### Group 3: Subscription Lifecycle (S-003)

**Maps to Tests:** F-SUB-008, F-SUB-015
**Unit Tests:** `src/frontend/tests/unit/subscription-status.test.ts`, `src/backend/tests/unit/test_billing_service.py`

#### S-003.1: GET /users/me/subscription

**Response (200) — Active:**
```json
{
  "subscription": {
    "subscription_id": "sub_xxx",
    "customer_id": "cus_xxx",
    "status": "active",
    "plan": "monthly",
    "current_period_end": "2026-04-14T00:00:00Z",
    "cancel_at_period_end": false,
    "trial_end": null
  },
  "has_active_subscription": true
}
```

**Response (200) — No subscription:**
```json
{ "subscription": null, "has_active_subscription": false }
```

**DynamoDB access:** Single `get_item(pk=USER#{user_id}, sk=SUBSCRIPTION#CURRENT)`.

---

### Group 4: Webhooks & Billing Events (S-004)

**Maps to Tests:** F-SUB-009, F-SUB-010, F-SUB-011, F-SUB-012, F-SUB-013, F-SUB-014, F-SUB-016
**Unit Tests:** `src/frontend/tests/unit/webhook-*.test.ts`, `src/backend/tests/unit/test_webhook_service.py`

#### S-004.1: POST /billing/webhook

**Critical implementation requirements:**

1. **Raw body passthrough (FIX: Issue 2) — explicit CDK requirement:**

   API Gateway REST API (v1) reformats the body by default. Without the fix below,
   `construct_webhook_event` will always fail signature verification in production
   (no obvious error — just `400 Invalid signature` on every real webhook).

   **CDK `api_construct.py` — `_build_api_gw()` must include:**
   ```python
   self.rest_api = aws_apigateway.RestApi(
       self,
       ...,
       binary_media_types=["application/json", "*/*"],
       # ^ Forces API Gateway to base64-encode the body instead of re-encoding it
   )
   ```

   **Lambda webhook handler — body extraction:**
   ```python
   import base64

   def _extract_raw_body(event: dict) -> bytes:
       """Return the raw request body bytes regardless of API Gateway encoding."""
       body = event.get("body") or ""
       if event.get("isBase64Encoded", False):
           return base64.b64decode(body)
       return body.encode("utf-8") if isinstance(body, str) else body

   # In handle_webhook_post:
   payload_bytes = _extract_raw_body(event)
   sig_header = event["headers"].get("Payment-Provider-Signature", "")
   ```

   > **Warning:** Do NOT add `binary_media_types` to only the webhook route —
   > CDK's `binary_media_types` is a property of the `RestApi` construct, not
   > individual routes. Adding it globally is the correct approach; other
   > routes are unaffected because their handlers don't call
   > `base64.b64decode`.

2. **Signature verification:**
   ```python
   try:
       event = payment_provider.construct_webhook_event(payload_bytes, sig_header, webhook_secret)
   except PaymentProviderError:
       return {'status_code': 400, 'body': {'error': 'invalid_signature'}}
   ```

3. **Dual-secret verification (FIX: Issue 4) — zero-downtime secret rotation:**

   A single SSM slot cannot support secret rotation without a gap.  Store two
   parameters and try both:

   ```python
   # SSM parameters (from infra/careervp/constants.py):
   # WEBHOOK_SECRET_SSM_PARAM          = /careervp/{env}/payment-provider-webhook-secret
   # WEBHOOK_SECRET_PREVIOUS_SSM_PARAM = /careervp/{env}/payment-provider-webhook-secret-previous

   def _verify_webhook(
       self,
       payload_bytes: bytes,
       sig_header: str,
       primary_secret: str,
       previous_secret: str | None,
   ) -> WebhookEvent:
       """Try primary secret first, fall back to previous during rotation window."""
       secrets = [s for s in (primary_secret, previous_secret) if s]
       for secret in secrets:
           try:
               return self._payment_provider.construct_webhook_event(
                   payload_bytes, sig_header, secret
               )
           except PaymentProviderError:
               continue
       raise PaymentProviderError('Invalid signature — neither secret matched')
   ```

   **Rotation procedure:**
   1. Generate new secret in payment provider dashboard
   2. Write new secret to `payment-provider-webhook-secret-previous` (copies current primary)
   3. Write new secret to `payment-provider-webhook-secret` (becomes new primary)
   4. Verify webhooks are arriving with the new secret
   5. Clear `payment-provider-webhook-secret-previous` after 24 h

   Both SSM parameters are read at Lambda cold-start. If the `previous` parameter
   does not exist (normal steady-state), `boto3` raises `ParameterNotFound` — catch
   it and set `previous_secret = None`.

   **CDK — read both secrets at cold-start:**
   ```python
   # In billing Lambda environment vars:
   environment={
       constants.WEBHOOK_SECRET_ENV_VAR: ssm.StringParameter.value_for_string_parameter(
           self, constants.WEBHOOK_SECRET_SSM_PARAM
       ),
       constants.WEBHOOK_SECRET_PREVIOUS_ENV_VAR: ssm.StringParameter.value_for_string_parameter(
           self, constants.WEBHOOK_SECRET_PREVIOUS_SSM_PARAM
       ),
       ...
   }
   ```

   > For the `previous` parameter, create a placeholder SSM value (`"none"`) in
   > the account at deploy time so `value_for_string_parameter` does not fail on
   > first deploy.  The Lambda handler ignores the value `"none"`.

4. **Idempotency guard with partial-failure retry (FIX: Issue 5):**

   **Problem:** If `record_payment_event` is called first and then `set_unlimited_usage`
   fails, the idempotency key blocks every future retry.  The user gets an active
   subscription but no credits — silent data inconsistency.

   **Fix — commit-after-work pattern:**
   ```python
   async def _handle_checkout_completed(self, event: WebhookEvent) -> None:
       session = event.data
       user_id  = session['metadata']['user_id']
       sub_id   = session['subscription']

       # Step 1: Claim idempotency slot (first delivery wins)
       is_new = self._sub_repo.record_payment_event(event.event_id, event.event_type)
       if not is_new:
           return  # Duplicate — already processed

       try:
           # Step 2: Do all work
           provider_sub = self._payment_provider.retrieve_subscription(sub_id)
           self._sub_repo.upsert_subscription(user_id, {...})
           self._sub_repo.set_unlimited_usage(user_id)   # ← must succeed
       except Exception:
           # Step 3a: ROLLBACK idempotency key so the provider can retry
           self._sub_repo.delete_payment_event(event.event_id, event.event_type)
           raise   # Return 5xx → provider retries the webhook

       # Step 3b: All work succeeded — idempotency key stays (blocks duplicates)
   ```

   **Why this is safe:** The payment provider retries webhooks on 5xx responses.
   Deleting the idempotency key allows the next delivery to reprocess from scratch.
   The `upsert_subscription` call is idempotent (`put_item`), so re-running it
   on retry causes no harm.

   **DAL method already in `SubscriptionRepository`:**
   - `delete_payment_event(event_id, event_type)` — deletes from idempotency table

5. **Event routing:**

   | Event Type | Handler | DynamoDB Write |
   |------------|---------|----------------|
   | `checkout.session.completed` | `_handle_checkout_completed` | `put_item(sk=SUBSCRIPTION#CURRENT)` + `put_item(sk=USAGE, remaining=9999)` |
   | `customer.subscription.updated` | `_handle_subscription_updated` | `update_item(sk=SUBSCRIPTION#CURRENT)` |
   | `customer.subscription.deleted` | `_handle_subscription_deleted` | `update_item(status='canceled')` |
   | `invoice.payment_succeeded` | `_handle_invoice_succeeded` | `update_item(payment_failed_count=0, status='active')` |
   | `invoice.payment_failed` | `_handle_invoice_failed` | increment `payment_failed_count`, `update_item(status='past_due')` |

6. **Stale event guard** (F-SUB-out-of-order):
   ```python
   # Only apply subscription.updated if event is newer than stored record
   existing = self._sub_repo.get_subscription(user_id)
   if existing.data:
       if existing.data.get('stripe_event_created', 0) > event.created:
           return  # Reject stale event
   ```

7. **Period date conversion:** All Unix timestamps from provider must be stored as ISO 8601 strings.

#### S-004.2: Webhook Signature Secret

SSM parameters (see `infra/careervp/constants.py`):

| Constant | SSM Path | Purpose |
|----------|----------|---------|
| `WEBHOOK_SECRET_SSM_PARAM` | `/careervp/{env}/payment-provider-webhook-secret` | Active signing secret |
| `WEBHOOK_SECRET_PREVIOUS_SSM_PARAM` | `/careervp/{env}/payment-provider-webhook-secret-previous` | Previous secret during rotation window |

Read both at cold-start using `ssm_utils.get_parameter()`. If `previous` returns `ParameterNotFound`, set `previous_secret = None`.

---

### Group 5: Portal & Access Control (S-005)

**Maps to Tests:** F-SUB-007, F-SUB-017
**Unit Tests:** `src/frontend/tests/unit/portal.test.ts`, `src/frontend/tests/unit/quota-enforcement.test.ts`, `src/backend/tests/unit/test_billing_service.py`, `src/backend/tests/unit/test_quota_service.py`

#### S-005.1: POST /billing/portal

**Request Body:** `{ "return_url": "https://..." }`

**Response (200):** `{ "portal_url": "https://..." }`

**Error:** 404 when user has no `customer_id` in their PROFILE row.

**Implementation:**
```python
def handle_portal(self, user_id: str, return_url: str) -> dict:
    customer_id = self._sub_repo.get_customer_id(user_id)
    if not customer_id:
        return {'status_code': 404, 'error': 'No billing account found'}
    portal = self._payment_provider.create_portal_session(
        customer_id=customer_id, return_url=return_url
    )
    return {'status_code': 200, 'portal_url': portal.portal_url}
```

#### S-005.2: Quota Enforcement at POST /jobs

Access control check order (F-SUB-017):
1. `get_item(pk=USER#{user_id}, sk=SUBSCRIPTION#CURRENT)`
2. If `status == 'active'` → allow (unlimited)
3. If `status in {past_due, canceled, expired}` → `403 subscription_required`
4. If no subscription → check trial (`TRIAL` row and `USAGE` row)
5. If trial expired or credits exhausted → `403 trial_expired/trial_exhausted`

---

## Infrastructure (S-006)

### S-006.1: API Gateway Raw Body Passthrough (FIX: Issue 2)

**File:** `infra/careervp/api_construct.py` — `_build_api_gw()`

This is a **known API Gateway footgun**.  Without the fix, webhook signature
verification silently fails in production even though it passes in local tests
(local tests pass raw bytes directly; API Gateway re-encodes the body).

**Required CDK change:**
```python
def _build_api_gw(self) -> aws_apigateway.RestApi:
    return aws_apigateway.RestApi(
        self,
        f"{self.id_}{constants.APIGATEWAY}",
        rest_api_name=self.naming.lambda_name(constants.APIGATEWAY),
        # ↓ REQUIRED for webhook raw body passthrough
        binary_media_types=["application/json", "*/*"],
        deploy_options=aws_apigateway.StageOptions(
            stage_name=self.naming.environment,
            throttling_burst_limit=500,
            throttling_rate_limit=1000,
        ),
        ...
    )
```

**Lambda handler — always decode body this way:**
```python
import base64

def _extract_raw_body(event: dict) -> bytes:
    body = event.get("body") or ""
    if event.get("isBase64Encoded", False):
        return base64.b64decode(body)
    return body.encode("utf-8") if isinstance(body, str) else body
```

**Verification test:**
`src/frontend/tests/integration/webhook-rawbody.integration.test.ts` (F-SUB-009-INT)
confirms raw body is passed correctly end-to-end.

### S-006.2: Billing Lambda CDK Construct

**File:** `infra/careervp/api_construct.py`

```python
from aws_cdk import aws_sqs as sqs, aws_cloudwatch as cw, aws_cloudwatch_actions as cw_actions

# 1. DLQ for partial-failure dead-letter handling (see S-006.4)
billing_webhook_dlq = sqs.Queue(
    self,
    f"{id_}BillingWebhookDlq",
    queue_name=self.naming.dlq_name(constants.BILLING_WEBHOOK_DLQ),
    retention_period=Duration.days(14),
    encryption=sqs.QueueEncryption.KMS_MANAGED,
)

# 2. Billing Lambda
billing_lambda = _lambda.Function(
    self,
    f"{id_}BillingLambda",
    function_name=self.naming.lambda_name(constants.BILLING_LAMBDA),
    runtime=_lambda.Runtime.PYTHON_3_12,
    handler="careervp.handlers.billing_handler.handler",
    code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
    environment={
        "TABLE_NAME": self.api_db.db.table_name,
        "IDEMPOTENCY_TABLE_NAME": self.api_db.idempotency_db.table_name,
        constants.WEBHOOK_SECRET_ENV_VAR: ssm.StringParameter.value_for_string_parameter(
            self, constants.WEBHOOK_SECRET_SSM_PARAM
        ),
        constants.WEBHOOK_SECRET_PREVIOUS_ENV_VAR: ssm.StringParameter.value_for_string_parameter(
            self, constants.WEBHOOK_SECRET_PREVIOUS_SSM_PARAM
        ),
        "PAYMENT_PROVIDER": "placeholder",    # replace with real value in prod
        "PRICE_ID_MONTHLY": ssm.StringParameter.value_for_string_parameter(
            self, f"/careervp/{ENVIRONMENT}/price-id-monthly"
        ),
        "PRICE_ID_QUARTERLY": ssm.StringParameter.value_for_string_parameter(
            self, f"/careervp/{ENVIRONMENT}/price-id-quarterly"
        ),
    },
    timeout=Duration.seconds(30),
    memory_size=256,
)

# 3. Grant table permissions
self.api_db.db.grant_read_write_data(billing_lambda)
self.api_db.idempotency_db.grant_read_write_data(billing_lambda)
```

### S-006.3: Reconciliation Schedule (FIX: Issue 3)

**Problem:** `reconcileAllSubscriptions()` is tested but never triggered.
Without a trigger the reconciliation logic is dead code.

**Solution:** EventBridge nightly cron + dedicated Lambda.

**File:** `infra/careervp/api_construct.py`

```python
from aws_cdk import aws_events as events, aws_events_targets as targets

# Reconciliation Lambda (lightweight — only needs DynamoDB + payment provider access)
billing_reconcile_lambda = _lambda.Function(
    self,
    f"{id_}BillingReconcileLambda",
    function_name=self.naming.lambda_name(constants.BILLING_RECONCILE_LAMBDA),
    runtime=_lambda.Runtime.PYTHON_3_12,
    handler="careervp.handlers.billing_reconcile_handler.handler",
    code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
    environment={
        "TABLE_NAME": self.api_db.db.table_name,
        "PAYMENT_PROVIDER": "placeholder",
        constants.WEBHOOK_SECRET_ENV_VAR: ssm.StringParameter.value_for_string_parameter(
            self, constants.WEBHOOK_SECRET_SSM_PARAM
        ),
    },
    timeout=Duration.minutes(5),   # allow time to scan all subscriptions
    memory_size=256,
)
self.api_db.db.grant_read_write_data(billing_reconcile_lambda)

# Nightly cron at 02:00 UTC
reconcile_rule = events.Rule(
    self,
    f"{id_}BillingReconcileSchedule",
    schedule=events.Schedule.cron(hour="2", minute="0"),
    description="Nightly subscription state reconciliation — provider is source of truth",
)
reconcile_rule.add_target(
    targets.LambdaFunction(
        billing_reconcile_lambda,
        event=events.RuleTargetInput.from_object({
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {"action": "reconcile_subscriptions"},
        }),
    )
)
```

**Reconciliation handler contract:**
```python
# src/backend/careervp/handlers/billing_reconcile_handler.py
def handler(event: dict, context: Any) -> dict:
    """Triggered by EventBridge nightly. Scans all active subscriptions and
    syncs status from payment provider.  Provider wins on divergence."""
    if event.get("detail", {}).get("action") != "reconcile_subscriptions":
        return {"status": "ignored"}   # guard against accidental invocations
    result = ReconciliationService(...).reconcile_all()
    logger.info("reconcile_complete", **result)
    return result
```

**`SubscriptionRepository` must implement `scan_active_subscriptions()`:**
```python
def scan_active_subscriptions(self) -> list[dict[str, Any]]:
    """Paginated scan for all SUBSCRIPTION#CURRENT items with status='active'.
    Uses FilterExpression — only called from the nightly job, not hot paths.
    """
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {
        "FilterExpression": (
            Attr('sk').eq(SUBSCRIPTION_SK) & Attr('status').eq('active')
        ),
    }
    while True:
        response = self._table.scan(**kwargs)
        items.extend(response.get('Items', []))
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        kwargs['ExclusiveStartKey'] = last_key
    return items
```

### S-006.4: Partial-Failure DLQ + Alarm (FIX: Issue 5)

**Problem:** If `set_unlimited_usage` fails during webhook processing, the user
has an active subscription but zero credits.  The naive fix (log and return 500)
leaves the user broken because the idempotency key blocks all retries.

**Two-part fix:**

**Part A — Commit-after-work pattern (see S-004.1 item 4):**
Delete the idempotency key on failure so the payment provider can retry.

**Part B — CloudWatch alarm on failed webhook invocations:**

```python
from aws_cdk import aws_cloudwatch as cw

billing_error_alarm = cw.Alarm(
    self,
    f"{id_}BillingWebhookErrorAlarm",
    metric=billing_lambda.metric_errors(
        period=Duration.minutes(5),
        statistic="Sum",
    ),
    threshold=1,
    evaluation_periods=1,
    alarm_description=(
        "Billing webhook Lambda errors — check for partial failures "
        "(subscription created but set_unlimited_usage failed). "
        "Investigate DynamoDB sk=SUBSCRIPTION#CURRENT vs sk=USAGE consistency."
    ),
    treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
)
```

**Recovery playbook** (document in runbook):
```bash
# Find users with active subscription but remaining != 9999
aws dynamodb scan \
  --table-name careervp-users-dev \
  --filter-expression "sk = :sub AND #s = :active" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":sub":{"S":"SUBSCRIPTION#CURRENT"},":active":{"S":"active"}}' \
  | jq '.Items[].user_id.S' | while read uid; do
    # Check if USAGE row is missing or not 9999
    aws dynamodb get-item \
      --table-name careervp-users-dev \
      --key "{\"pk\":{\"S\":\"USER#$uid\"},\"sk\":{\"S\":\"USAGE\"}}" \
      | jq "{uid: \"$uid\", remaining: .Item.remaining.N}"
  done
```

---

## API Endpoints Reference

| Method | Path | Auth | Handler | Tests |
|--------|------|------|---------|-------|
| `POST` | `/billing/checkout` | JWT | `handle_checkout_post` | F-SUB-004,005,006 |
| `GET` | `/users/me/subscription` | JWT | `handle_get_subscription` | F-SUB-008,015 |
| `POST` | `/billing/portal` | JWT | `handle_portal_post` | F-SUB-007 |
| `POST` | `/billing/webhook` | None (sig) | `handle_webhook_post` | F-SUB-009–016 |

### Lambda Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `TABLE_NAME` | CDK output | users table (existing) |
| `IDEMPOTENCY_TABLE_NAME` | CDK output | idempotency table (existing) |
| `PAYMENT_PROVIDER` | SSM | `placeholder` / `stripe` / etc. |
| `PAYMENT_PROVIDER_PLACEHOLDER` | SSM | `true` for local dev only |
| `PRICE_ID_MONTHLY` | SSM | Provider price ID for monthly plan |
| `PRICE_ID_QUARTERLY` | SSM | Provider price ID for quarterly plan |
| `PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM` | SSM | Active webhook signing secret |
| `PAYMENT_PROVIDER_WEBHOOK_SECRET_PREVIOUS_SSM_PARAM` | SSM | Previous secret during rotation (set to `"none"` when not rotating) |

---

## Error Handling & Status Codes

| Condition | Code | Error Body |
|-----------|------|------------|
| Invalid plan | 400 | `{"error": "invalid_plan", "message": "..."}` |
| Missing URLs | 400 | `{"error": "invalid_request"}` |
| Already subscribed | 409 | `{"error": "subscription_exists"}` |
| Checkout in progress (concurrent) | 409 | `{"error": "checkout_in_progress"}` |
| Invalid webhook signature | 400 | `{"error": "invalid_signature"}` |
| No billing account (portal) | 404 | `{"error": "no_billing_account"}` |
| Trial expired | 403 | `{"error": "trial_expired"}` |
| Trial exhausted | 403 | `{"error": "trial_exhausted"}` |
| Subscription inactive | 403 | `{"error": "subscription_required"}` |
| Provider timeout | 503 | `{"error": "payment_provider_timeout"}` |
| Provider error | 502 | `{"error": "payment_provider_error"}` |
| DynamoDB error | 500 | `{"error": "internal_error"}` |

All error codes map to `ResultCode` constants in `src/backend/careervp/models/result.py`.

---

## Regression Prevention Checklist

Before merging any subscription PR:

- [ ] `cd src/frontend && npm run test:critical` — all tests pass
- [ ] `cd src/backend && uv run pytest tests/unit/test_subscription_repository.py tests/unit/test_billing_service.py tests/unit/test_webhook_service.py tests/unit/test_quota_service.py -v`
- [ ] `cd src/backend && uv run pytest tests/unit/ -v --tb=short` — all existing tests still pass
- [ ] `cd infra && cdk synth` — no new tables added to CloudFormation
- [ ] No direct Stripe SDK import outside `payment_providers/` directory
- [ ] All new DynamoDB operations use `ExpressionAttributeNames` for reserved keywords (`status`, `plan`)
- [ ] Webhook handler calls `delete_payment_event` in the `except` branch before re-raising
- [ ] Checkout handler calls `release_checkout_intent` in a `finally` block
- [ ] `binary_media_types=["application/json", "*/*"]` present on `RestApi` construct
- [ ] Both SSM webhook secret parameters exist in the account (`previous` set to `"none"` if not rotating)
- [ ] EventBridge reconciliation rule targets `billing-reconcile` Lambda
- [ ] `PaymentProviderInterface` is the only import in business logic (never `stripe`)
