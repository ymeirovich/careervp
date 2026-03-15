# Subscription Service Implementation Specifications

**Purpose:** This document provides implementation specifications that directly map to the test suite defined in `SUBSCRIPTION_FEATURE_TEST_PROMPT.md`. Each specification guarantees that unit, integration, E2E, and regression tests will pass.

**Output audience:** Backend developers implementing subscription features, code generation agents.

**Prerequisite:** All tests in `src/frontend/tests/` must pass. Run tests with npm scripts documented in the [Test Execution Guide](#test-execution-guide) at the end of this document.

**Constraint:** No breaking changes to existing CareerVP APIs. All new endpoints and data models must follow established patterns.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Shared Data Models](#shared-data-models)
3. [Implementation Groups](#implementation-groups)
   - [Group 1: Trial & Quota Foundation (S-001)](#group-1-trial--quota-foundation-s-001)
   - [Group 2: Checkout Flow (S-002)](#group-2-checkout-flow-s-002)
   - [Group 3: Subscription Lifecycle (S-003)](#group-3-subscription-lifecycle-s-003)
   - [Group 4: Webhooks & Billing Events (S-004)](#group-4-webhooks--billing-events-s-004)
   - [Group 5: Portal & Access Control (S-005)](#group-5-portal--access-control-s-005)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Test Execution Guide](#test-execution-guide)
6. [Error Handling & Status Codes](#error-handling--status-codes)
7. [Regression Prevention Checklist](#regression-prevention-checklist)

---

## Architecture Overview

### Request-Response Pipeline

Every subscription request follows this pipeline:

```
Client HTTP Request
    ↓
API Gateway (CORS, raw body passthrough for webhooks)
    ↓
Cognito Authorizer (validates JWT; skipped for webhooks)
    ↓
Lambda Handler (careervp-billing-{stage})
    ↓
Billing Logic (subscription check, quota validation)
    ↓
DAL (Data Access Layer: UsersDAL, UsageDAL, SubscriptionsDAL)
    ↓
DynamoDB Tables
    ↓
Response Builder (applies CORS, error formatting)
    ↓
Client HTTP Response
```

### Core Tables

| Table | Primary Key | Role |
|-------|------------|------|
| `careervp-users-{stage}` | `user_id` (STRING) | Stores `created_at` (trial start), `stripe_customer_id` |
| `careervp-usage-{stage}` | `user_id` (STRING) | Stores `remaining` (credit count; 9999 = unlimited) |
| `careervp-subscriptions-{stage}` | `subscription_id` (STRING) | Stores Stripe subscription state, plan, billing dates |
| `careervp-applications-{stage}` (existing) | `application_id` (STRING) | Job application record; partition key for quota check |

### New GSIs

| Table | GSI Name | Partition Key | Sort Key | Use Case |
|-------|----------|---------------|----------|----------|
| `careervp-subscriptions-{stage}` | `UserSubscriptionIndex` | `user_id` | `created_at` | Query user's active subscription |
| `careervp-subscriptions-{stage}` | `CustomerIndex` | `stripe_customer_id` | `subscription_id` | Lookup subscription by Stripe customer |

---

## Shared Data Models

### User Model

```python
# src/backend/careervp/models/user.py

@dataclass
class User:
    user_id: str              # Cognito sub UUID
    created_at: str           # ISO 8601 timestamp (trial start)
    email: str
    stripe_customer_id: Optional[str] = None  # Stripe Customer ID
    updated_at: Optional[str] = None

    @property
    def trial_remaining_days(self) -> int:
        """Days left in 14-day trial."""
        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        trial_end = created + timedelta(days=14)
        remaining = (trial_end - datetime.now(timezone.utc)).days
        return max(remaining, 0)

    @property
    def trial_expired(self) -> bool:
        """True if more than 14 days since creation."""
        return self.trial_remaining_days == 0
```

### Usage Model

```python
# src/backend/careervp/models/usage.py

@dataclass
class Usage:
    user_id: str              # Partition key
    remaining: int            # Credits remaining; 9999 = unlimited (subscribed)
    created_at: str           # ISO 8601 (when usage record created)
    updated_at: Optional[str] = None

    @property
    def has_credits(self) -> bool:
        """True if user can create a new application."""
        return self.remaining > 0

    @property
    def is_subscribed(self) -> bool:
        """True if unlimited (remaining = 9999)."""
        return self.remaining >= 9999
```

### Subscription Model

```python
# src/backend/careervp/models/subscription.py

from enum import Enum

class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"

class SubscriptionPlan(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

@dataclass
class Subscription:
    subscription_id: str          # Stripe subscription ID
    user_id: str                  # Partition key
    stripe_customer_id: str       # For lookup via CustomerIndex
    status: SubscriptionStatus    # Stripe status enum
    plan: SubscriptionPlan        # "monthly" or "quarterly"
    current_period_start: int     # Unix timestamp (Stripe)
    current_period_end: int       # Unix timestamp (Stripe)
    cancel_at_period_end: bool    # Scheduled for cancellation?
    trial_end: Optional[int] = None  # Unix timestamp if in trial
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """True if subscription is currently providing access."""
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def period_remaining_days(self) -> int:
        """Days left in current billing period."""
        period_end = datetime.fromtimestamp(self.current_period_end, tz=timezone.utc)
        remaining = (period_end - datetime.now(timezone.utc)).days
        return max(remaining, 0)
```

### API Error Model

```python
# src/backend/careervp/models/errors.py

@dataclass
class ApiError(Exception):
    status_code: int
    error_code: str             # Machine-readable code (e.g., "trial_expired")
    message: str                # Human-readable message
    details: Optional[dict] = None  # Additional context

    def to_response(self) -> dict:
        """Serialize to API response."""
        body = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            body.update(self.details)
        return body
```

---

## Implementation Groups

### Group 1: Trial & Quota Foundation (S-001)

**Spec:** Core quota and trial state checking logic.
**Maps to Tests:** F-SUB-001, F-SUB-002, F-SUB-003
**Unit Tests:** `src/frontend/tests/unit/trial.test.ts`
**Acceptance Criteria:**
- All unit tests in `trial.test.ts` pass
- No breaking changes to existing `/jobs` endpoint

#### S-001.1: Trial Activation on Sign-Up

**Requirement:** When a new user registers via Cognito, trial state is implicitly activated.

**Implementation:**
1. In sign-up flow, create a `User` record in `careervp-users-{stage}` with `created_at = now()`
2. Create a `Usage` record in `careervp-usage-{stage}` with `remaining = 3`
3. No explicit `Subscription` record created (trial is absence of subscription)

**Data Model:**
- User: `created_at` timestamp
- Usage: `remaining = 3`
- Subscription: `null` (no record)

**Code Location:** `src/backend/careervp/logic/subscription_service.py` → `activate_trial(user_id: str) -> None`

**Pseudo-code:**
```python
def activate_trial(user_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    users_dal.put_item(User(user_id=user_id, created_at=now))
    usage_dal.put_item(Usage(user_id=user_id, remaining=3, created_at=now))
```

**Verification:**
- User created at integration with Cognito signup
- Usage record initialized with 3 credits
- Unit test F-SUB-001 passes

---

#### S-001.2: Check Trial and Quota

**Requirement:** Before allowing job creation, validate trial and credit status.

**Implementation:**
1. Create shared function `check_trial_and_quota(user_id: str) -> None`
2. Check conditions in order:
   a. Is there an active subscription? → Grant access
   b. Is trial expired? → Raise `403 trial_expired`
   c. Are credits exhausted? → Raise `403 trial_exhausted`
   d. Otherwise → Grant access

**Code Location:** `src/backend/careervp/logic/subscription_service.py` → `check_trial_and_quota(user_id: str) -> None`

**Pseudo-code:**
```python
def check_trial_and_quota(user_id: str) -> None:
    """Validate user can create new application."""
    # Check 1: Active subscription grants unlimited access
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    if sub and sub.is_active:
        return  # Allowed

    # Check 2: Trial expiry
    user = users_dal.get_user(user_id)
    if user.trial_expired:
        raise ApiError(403, "trial_expired", "Your trial has expired")

    # Check 3: Credit availability
    usage = usage_dal.get_usage(user_id)
    if not usage.has_credits:
        raise ApiError(403, "trial_exhausted", "No credits remaining")

    # Allowed
```

**Invocation Points:**
- Lambda handler for `POST /jobs` (before creating job)
- Lambda handler for `POST /gap-analyses` (before generating questions)

**Verification:**
- Unit tests F-SUB-002 (expired), F-SUB-003 (exhausted) pass
- Boundary regression tests pass (14-day, 1-credit boundaries)

---

#### S-001.3: Deduct Credit on Job Creation

**Requirement:** When a job (application) is created, decrement `remaining` by 1.

**Implementation:**
1. After job successfully created, call `usage_dal.decrement_remaining(user_id, 1)`
2. This is idempotent: if called twice on same job, usage becomes negative (guard in check function)
3. Only decrement after successful job creation (transactional: create job, then deduct)

**Code Location:** `src/backend/careervp/logic/subscription_service.py` → `deduct_credit(user_id: str) -> None`

**Pseudo-code:**
```python
def deduct_credit(user_id: str) -> None:
    """Decrement remaining credits by 1."""
    usage = usage_dal.get_usage(user_id)
    updated_usage = Usage(
        user_id=user_id,
        remaining=max(0, usage.remaining - 1),
        created_at=usage.created_at,
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    usage_dal.update_item(updated_usage)
```

**Invocation Points:**
- After `POST /jobs` returns 200 (in same Lambda handler, after job created)

**Verification:**
- Create 3 jobs, verify usage goes 3→2→1→0
- Regression test confirms credit count never goes negative

---

### Group 2: Checkout Flow (S-002)

**Spec:** Stripe checkout session creation and customer lifecycle.
**Maps to Tests:** F-SUB-004, F-SUB-005, F-SUB-006
**Unit Tests:** `src/frontend/tests/unit/checkout.test.ts`
**Integration Tests:** `src/frontend/tests/integration/checkout.integration.test.ts`
**Acceptance Criteria:**
- All unit tests in `checkout.test.ts` pass
- Integration test hits real Stripe test API
- No duplicate Stripe Customer records created

#### S-002.1: Create Checkout Session Endpoint

**Requirement:** `POST /billing/checkout` creates a Stripe checkout session for subscription upgrade.

**Endpoint:** `POST /billing/checkout`
**Auth:** Cognito JWT required
**Request Body:**
```json
{
  "plan": "monthly" | "quarterly",
  "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.careervp.com/settings/billing"
}
```

**Response (200 OK):**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_..."
}
```

**Error Responses:**
- `400`: Invalid plan (not "monthly" or "quarterly")
- `400`: Invalid URLs (missing or malformed)
- `409`: User already has active subscription
- `500`: Stripe API error

**Implementation Steps:**
1. Extract `user_id` from Cognito JWT via `get_user_id_from_event(event)`
2. Validate request body schema
3. Check for existing active subscription → return 409 if found
4. Get or create Stripe Customer (via S-002.2)
5. Map plan to price ID: `monthly` → `STRIPE_PRICE_MONTHLY`, `quarterly` → `STRIPE_PRICE_QUARTERLY`
6. Call `stripe.checkout.Session.create()`
7. Return checkout URL

**Code Location:** `src/backend/careervp/handlers/billing_handler.py` → `handle_checkout_post(event, context)`

**Pseudo-code:**
```python
def handle_checkout_post(event, context):
    user_id = get_user_id_from_event(event)
    body = json.loads(event['body'])

    # Validate plan
    if body['plan'] not in ['monthly', 'quarterly']:
        raise ApiError(400, "invalid_plan", "Plan must be monthly or quarterly")

    # Check existing subscription
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    if sub and sub.is_active:
        raise ApiError(409, "subscription_exists", "User already has active subscription")

    # Get/create Stripe customer
    customer_id = get_or_create_stripe_customer(user_id)

    # Map plan to price ID
    price_id = {
        'monthly': os.getenv('STRIPE_PRICE_MONTHLY'),
        'quarterly': os.getenv('STRIPE_PRICE_QUARTERLY'),
    }[body['plan']]

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='subscription',
        success_url=body['success_url'],
        cancel_url=body['cancel_url'],
    )

    return {
        'statusCode': 200,
        'body': json.dumps({'checkout_url': session.url}),
        'headers': cors_headers(event.get('headers', {}).get('Origin'))
    }
```

**Verification:**
- Unit test F-SUB-004 (monthly), F-SUB-004b (quarterly) pass
- Unit test F-SUB-004c (invalid plan) returns 400
- Integration test completes checkout and receives Stripe URL

---

#### S-002.2: Get or Create Stripe Customer

**Requirement:** Reuse existing Stripe customer; create only if necessary.

**Implementation:**
1. Look up `stripe_customer_id` on User record
2. If found and valid, use it
3. If not found, check `CustomerIndex` GSI on Subscriptions table as fallback
4. If still not found, create new Stripe Customer with metadata
5. Store `stripe_customer_id` on User record

**Code Location:** `src/backend/careervp/logic/stripe_service.py` → `get_or_create_stripe_customer(user_id: str) -> str`

**Pseudo-code:**
```python
def get_or_create_stripe_customer(user_id: str) -> str:
    """Get existing Stripe customer ID or create new one."""
    # Check User record first
    user = users_dal.get_user(user_id)
    if user.stripe_customer_id:
        return user.stripe_customer_id

    # Check Subscriptions table as fallback
    subs = subscriptions_dal.query_by_user(user_id)
    if subs:
        existing_customer_id = subs[0].stripe_customer_id
        # Update User record for future lookups
        users_dal.update_stripe_customer_id(user_id, existing_customer_id)
        return existing_customer_id

    # Create new customer
    customer = stripe.Customer.create(
        metadata={'user_id': user_id}
    )

    # Store on User record
    users_dal.update_stripe_customer_id(user_id, customer.id)
    return customer.id
```

**Verification:**
- Unit test F-SUB-005 confirms no duplicate Customer.create() calls
- Regression test F-SUB-005-R confirms only 1 Stripe customer for reused user

---

#### S-002.3: Block Duplicate Checkout

**Requirement:** Prevent initiating checkout if user already has active subscription.

**Implementation:**
- In `handle_checkout_post`, check for existing active subscription (done in S-002.1)
- Return `409 Conflict` with message

**Code Location:** (same as S-002.1)

**Verification:**
- Unit test F-SUB-006 confirms 409 and no Stripe API call

---

### Group 3: Subscription Lifecycle (S-003)

**Spec:** Subscription state management, portal access, and status queries.
**Maps to Tests:** F-SUB-007, F-SUB-008, F-SUB-015
**Unit Tests:** `src/frontend/tests/unit/portal.test.ts`, `src/frontend/tests/unit/subscription-status.test.ts`
**Acceptance Criteria:**
- All unit tests pass
- Subscription states correctly reflect Stripe state
- Portal URL correctly constructed

#### S-003.1: Get Subscription Status Endpoint

**Requirement:** `GET /users/me/subscription` returns current subscription state.

**Endpoint:** `GET /users/me/subscription`
**Auth:** Cognito JWT required

**Response (200 OK) — Active Subscription:**
```json
{
  "subscription": {
    "subscription_id": "sub_1Pxyz",
    "status": "active",
    "plan": "monthly",
    "current_period_end": "2026-04-14T00:00:00Z",
    "cancel_at_period_end": false,
    "trial_end": null
  },
  "has_active_subscription": true
}
```

**Response (200 OK) — No Subscription:**
```json
{
  "subscription": null,
  "has_active_subscription": false
}
```

**Implementation:**
1. Extract `user_id` from JWT
2. Query subscriptions via `UserSubscriptionIndex` GSI
3. If found, return subscription object with `has_active_subscription = (status == "active")`
4. If not found, return `null` with `has_active_subscription = false`

**Code Location:** `src/backend/careervp/handlers/billing_handler.py` → `handle_subscription_get(event, context)`

**Pseudo-code:**
```python
def handle_subscription_get(event, context):
    user_id = get_user_id_from_event(event)
    sub = subscriptions_dal.get_subscription_by_user(user_id)

    if sub:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'subscription': {
                    'subscription_id': sub.subscription_id,
                    'status': sub.status.value,
                    'plan': sub.plan.value,
                    'current_period_end': datetime.fromtimestamp(
                        sub.current_period_end, tz=timezone.utc
                    ).isoformat(),
                    'cancel_at_period_end': sub.cancel_at_period_end,
                    'trial_end': datetime.fromtimestamp(
                        sub.trial_end, tz=timezone.utc
                    ).isoformat() if sub.trial_end else None,
                },
                'has_active_subscription': sub.is_active,
            }),
            'headers': cors_headers(event.get('headers', {}).get('Origin'))
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'subscription': None,
                'has_active_subscription': False,
            }),
            'headers': cors_headers(event.get('headers', {}).get('Origin'))
        }
```

**Verification:**
- Unit test F-SUB-008 returns active subscription
- Unit test F-SUB-008b returns null
- Regression test F-SUB-008-R covers all status values

---

#### S-003.2: Customer Portal Session Endpoint

**Requirement:** `POST /billing/portal` returns Stripe Customer Portal URL for managing subscription.

**Endpoint:** `POST /billing/portal`
**Auth:** Cognito JWT required
**Request Body:**
```json
{
  "return_url": "https://app.careervp.com/settings/billing"
}
```

**Response (200 OK):**
```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

**Error Responses:**
- `404`: No billing account found (no customer_id)

**Implementation:**
1. Extract `user_id` from JWT
2. Look up `stripe_customer_id` via `get_or_create_stripe_customer()` (returns existing or creates new)
3. If no customer found, return `404 No billing account found`
4. Call `stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)`
5. Return portal URL

**Code Location:** `src/backend/careervp/handlers/billing_handler.py` → `handle_portal_post(event, context)`

**Pseudo-code:**
```python
def handle_portal_post(event, context):
    user_id = get_user_id_from_event(event)
    body = json.loads(event['body'])

    customer_id = users_dal.get_stripe_customer_id(user_id)
    if not customer_id:
        raise ApiError(404, "no_billing_account", "No billing account found")

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=body['return_url'],
    )

    return {
        'statusCode': 200,
        'body': json.dumps({'portal_url': portal_session.url}),
        'headers': cors_headers(event.get('headers', {}).get('Origin'))
    }
```

**Verification:**
- Unit test F-SUB-007 confirms portal URL returned
- Unit test F-SUB-007b confirms 404 when no customer

---

#### S-003.3: Subscription Cancellation Label

**Requirement:** If `cancel_at_period_end = true`, show cancellation-pending label in UI.

**Implementation:**
- No new endpoint needed; status is returned in `GET /users/me/subscription` (S-003.1)
- Frontend checks `cancel_at_period_end` and renders appropriate UI

**Code Location:** N/A (handled by webhook in S-004)

**Verification:**
- Regression test F-SUB-015-R confirms UI labels for cancellation states

---

### Group 4: Webhooks & Billing Events (S-004)

**Spec:** Stripe webhook processing, signature verification, and billing state transitions.
**Maps to Tests:** F-SUB-009, F-SUB-010, F-SUB-011, F-SUB-012, F-SUB-013, F-SUB-014, F-SUB-016, F-SUB-017
**Unit Tests:** `src/frontend/tests/unit/webhook-*.test.ts`
**Integration Tests:** `src/frontend/tests/integration/webhook-rawbody.integration.test.ts`
**E2E Tests:** `src/frontend/tests/e2e/*.e2e.test.ts`
**Acceptance Criteria:**
- All webhook tests pass
- Signature verification mandatory
- Idempotent event processing
- No data loss on duplicate events

#### S-004.1: Webhook Endpoint & Signature Verification

**Requirement:** `POST /billing/webhook` validates Stripe webhook signature before processing.

**Endpoint:** `POST /billing/webhook`
**Auth:** NO Cognito authorizer (webhook is from Stripe, not user)
**API Gateway Config:** Must pass raw body bytes unchanged (no content transformation)

**Implementation:**
1. Read `Stripe-Signature` header from request
2. Read raw request body (critical: must be exact bytes)
3. Call `stripe.Webhook.construct_event(body, signature, webhook_secret)`
4. If signature invalid → return `400 Invalid signature`, **zero DynamoDB writes**
5. If valid → proceed to event handler

**Code Location:** `src/backend/careervp/handlers/billing_handler.py` → `handle_webhook_post(event, context)`

**Pseudo-code:**
```python
import stripe

def handle_webhook_post(event, context):
    # Get raw body (API Gateway must use contentHandling: CONVERT_TO_TEXT)
    raw_body = event['body']
    if isinstance(raw_body, str):
        raw_body = raw_body.encode('utf-8')

    signature = event['headers'].get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        webhook_event = stripe.Webhook.construct_event(
            raw_body, signature, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid signature'}),
        }

    # Route to handler
    handler = webhook_handlers.get(webhook_event['type'])
    if handler:
        handler(webhook_event['data']['object'])

    return {
        'statusCode': 200,
        'body': json.dumps({'received': True}),
    }
```

**API Gateway Configuration:**
- Do NOT use `requestModels` or `requestTemplates` that transform body
- Set `contentHandling: CONVERT_TO_TEXT` if needed (pass bytes as-is)
- No body transformation layer

**Verification:**
- Unit test F-SUB-009 confirms 400 on invalid signature
- Integration test F-SUB-009-INT confirms Stripe CLI signature passes
- No DynamoDB writes on failed signature

---

#### S-004.2: Webhook — Checkout Session Completed

**Requirement:** Handle `checkout.session.completed` event to activate subscription.

**Event:** `checkout.session.completed`
**Trigger:** User completes Stripe Checkout payment

**Data Extraction:**
```
webhook_event['data']['object'] = {
  'id': 'cs_test_...',
  'subscription': 'sub_1Pxyz',       # Stripe subscription ID
  'customer': 'cus_Nabc',              # Stripe customer ID
  'metadata': {
    'user_id': 'user-123',
    'plan': 'monthly'
  }
}
```

**Implementation:**
1. Extract `user_id`, `subscription_id`, `customer_id`, `plan` from event
2. Call `stripe.Subscription.retrieve(subscription_id)` to get full subscription object
3. Create/upsert `Subscription` record with:
   - `status = "active"`
   - `plan = metadata['plan']`
   - `current_period_start` and `current_period_end` from Stripe object
   - `cancel_at_period_end = false`
4. Set usage `remaining = 9999` (unlimited)
5. Log: "Subscription activated for user {user_id}"

**Code Location:** `src/backend/careervp/logic/webhook_handlers.py` → `handle_checkout_session_completed(session_data)`

**Pseudo-code:**
```python
def handle_checkout_session_completed(session_data):
    user_id = session_data['metadata']['user_id']
    subscription_id = session_data['subscription']
    customer_id = session_data['customer']
    plan = session_data['metadata']['plan']

    # Get full subscription from Stripe
    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    # Create subscription record
    sub = Subscription(
        subscription_id=subscription_id,
        user_id=user_id,
        stripe_customer_id=customer_id,
        status=SubscriptionStatus.ACTIVE,
        plan=SubscriptionPlan(plan),
        current_period_start=stripe_sub.current_period_start,
        current_period_end=stripe_sub.current_period_end,
        cancel_at_period_end=stripe_sub.cancel_at_period_end,
        trial_end=stripe_sub.trial_end,
    )
    subscriptions_dal.upsert_subscription(sub)

    # Grant unlimited access
    usage_dal.set_unlimited_usage(user_id)

    logger.info(f"Subscription activated for user {user_id}")
```

**Verification:**
- Unit test F-SUB-010 confirms subscription created with `status = "active"`
- E2E test F-SUB-010-E2E confirms full checkout → webhook → access granted flow
- DynamoDB confirms `remaining = 9999`

---

#### S-004.3: Webhook Idempotency

**Requirement:** Processing the same webhook event twice must not create duplicates or break state.

**Implementation:**
1. `upsert_subscription()` uses DynamoDB `put_item` (overwrite with same data = safe)
2. `set_unlimited_usage()` is idempotent (setting to 9999 twice = same result)
3. No unique constraints that could be violated
4. Return `200` on all successful webhook processing (even if event processed before)

**Code Location:** (same handlers as S-004.2, etc.)

**Verification:**
- Regression test F-SUB-011-R sends same webhook twice, confirms idempotent result

---

#### S-004.4: Webhook — Invoice Events

**Requirement:** Handle `invoice.payment_succeeded` and `invoice.payment_failed` events.

**Event 1:** `invoice.payment_succeeded`
**Action:** Mark subscription as paid; reset `status = "active"` if was `past_due`

**Event 2:** `invoice.payment_failed`
**Action:** Mark subscription as `past_due`; optionally email user

**Implementation:**
1. Extract `subscription` and `customer` from invoice data
2. Query `Subscription` by `stripe_customer_id` (via `CustomerIndex` GSI)
3. For `invoice.payment_succeeded`: set `status = "active"`
4. For `invoice.payment_failed`: set `status = "past_due"`
5. Update via `subscriptions_dal.update_subscription_status()`

**Code Location:** `src/backend/careervp/logic/webhook_handlers.py` → `handle_invoice_payment_*`

**Pseudo-code:**
```python
def handle_invoice_payment_succeeded(invoice_data):
    customer_id = invoice_data['customer']
    sub = subscriptions_dal.get_subscription_by_customer(customer_id)
    if sub:
        sub.status = SubscriptionStatus.ACTIVE
        subscriptions_dal.update_subscription(sub)
        logger.info(f"Invoice succeeded; subscription active for {sub.user_id}")

def handle_invoice_payment_failed(invoice_data):
    customer_id = invoice_data['customer']
    sub = subscriptions_dal.get_subscription_by_customer(customer_id)
    if sub:
        sub.status = SubscriptionStatus.PAST_DUE
        subscriptions_dal.update_subscription(sub)
        logger.info(f"Invoice failed; subscription past_due for {sub.user_id}")
```

**Verification:**
- Unit tests F-SUB-012, F-SUB-013 confirm status transitions
- E2E tests confirm user access blocked when `past_due`

---

#### S-004.5: Webhook — Subscription Updated

**Requirement:** Handle `customer.subscription.updated` for plan changes and cancellation scheduling.

**Event:** `customer.subscription.updated`
**Cases:**
- Plan changed (monthly → quarterly)
- Cancellation scheduled (`cancel_at_period_end = true`)

**Implementation:**
1. Extract `subscription_id` from event
2. Query `Subscription` by `subscription_id`
3. Update fields from Stripe subscription object:
   - `plan` (if changed)
   - `cancel_at_period_end` (if changed)
   - `current_period_start`, `current_period_end` (always update)

**Code Location:** `src/backend/careervp/logic/webhook_handlers.py` → `handle_subscription_updated(subscription_data)`

**Verification:**
- Unit test F-SUB-014a confirms plan change
- Unit test F-SUB-014b confirms cancellation scheduling

---

#### S-004.6: Webhook — Subscription Deleted

**Requirement:** Handle `customer.subscription.deleted` for canceled subscriptions.

**Event:** `customer.subscription.deleted`
**Action:** Mark subscription as `canceled`; optionally reset usage to trial credits if trial re-eligible

**Implementation:**
1. Extract `subscription_id` and `customer_id` from event
2. Query `Subscription` by `subscription_id`
3. Set `status = SubscriptionStatus.CANCELED`
4. (Optional) Check if user's trial can be extended, or reset usage to 0
5. Update via `subscriptions_dal.update_subscription()`

**Code Location:** `src/backend/careervp/logic/webhook_handlers.py` → `handle_subscription_deleted(subscription_data)`

**Verification:**
- Unit test F-SUB-016 confirms `status = "canceled"`
- E2E test confirms access blocked post-cancellation

---

#### S-004.7: Quota Enforcement — All States

**Requirement:** Enforce access control based on subscription state (active, past_due, canceled, expired).

**Implementation:**
- Only `active` subscriptions grant access
- `past_due`, `canceled`, `expired` → block new job creation
- Use `check_trial_and_quota()` from S-001.2; extend to check subscription status

**Code Update to S-001.2:**
```python
def check_trial_and_quota(user_id: str) -> None:
    # Check 1: Active subscription grants unlimited access
    sub = subscriptions_dal.get_subscription_by_user(user_id)
    if sub and sub.status == SubscriptionStatus.ACTIVE:
        return  # Allowed

    # Blocks: past_due, canceled, expired, trialing (no sub)
    if sub and sub.status != SubscriptionStatus.ACTIVE:
        raise ApiError(403, "subscription_inactive", f"Subscription is {sub.status}")

    # Check 2: Trial expiry (if no sub)
    user = users_dal.get_user(user_id)
    if user.trial_expired:
        raise ApiError(403, "trial_expired", "Your trial has expired")

    # Check 3: Credit availability
    usage = usage_dal.get_usage(user_id)
    if not usage.has_credits:
        raise ApiError(403, "trial_exhausted", "No credits remaining")

    # Allowed
```

**Verification:**
- Regression test F-SUB-017-R tests all status states

---

### Group 5: Portal & Access Control (S-005)

**Spec:** CORS, security headers, and CDK infrastructure provisioning.
**Maps to Tests:** F-SUB-018, F-SUB-019, F-SUB-020
**Unit Tests:** `src/frontend/tests/unit/cdk-infra.test.ts`, `src/frontend/tests/unit/ssm-cold-start.test.ts`, `src/frontend/tests/unit/cors.test.ts`
**Integration Tests:** `src/frontend/tests/integration/cdk-deploy.integration.test.ts`
**Acceptance Criteria:**
- CDK snapshot tests pass
- CORS headers correct
- No wildcard origins in production

#### S-005.1: CDK Infrastructure Provisioning

**Requirement:** Define CDK stacks for Lambda, API Gateway, DynamoDB tables, and SSM parameters.

**Location:** `infra/careervp/billing_stack.py`

**Resources:**

| Resource | Type | Details |
|----------|------|---------|
| Lambda Function | `aws_lambda.Function` | `careervp-billing-{stage}`, timeout 30s, 512MB |
| API Gateway | Routes | `/billing/checkout`, `/billing/portal`, `/billing/webhook`, `/users/me/subscription` |
| DynamoDB Tables | Tables | Create if not exist: `careervp-subscriptions-{stage}` with GSIs |
| IAM Role | Lambda execution role | Permissions: DynamoDB read/write, SSM read, CloudWatch Logs |
| SSM Parameters | Secure String | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_QUARTERLY` |

**Pseudo-code (CDK):**
```python
from aws_cdk import (
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
    aws_iam as iam,
    core
)

class BillingStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # DynamoDB table for subscriptions
        subscriptions_table = dynamodb.Table(
            self, 'SubscriptionsTable',
            table_name=f'careervp-subscriptions-{self.node.try_get_context("stage")}',
            partition_key=dynamodb.Attribute(name='subscription_id', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # GSI: UserSubscriptionIndex
        subscriptions_table.add_global_secondary_index(
            index_name='UserSubscriptionIndex',
            partition_key=dynamodb.Attribute(name='user_id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='created_at', type=dynamodb.AttributeType.STRING),
        )

        # GSI: CustomerIndex
        subscriptions_table.add_global_secondary_index(
            index_name='CustomerIndex',
            partition_key=dynamodb.Attribute(name='stripe_customer_id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='subscription_id', type=dynamodb.AttributeType.STRING),
        )

        # Lambda function
        billing_lambda = lambda_.Function(
            self, 'BillingFunction',
            function_name=f'careervp-billing-{self.node.try_get_context("stage")}',
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset('src/backend'),
            handler='careervp.handlers.billing_handler.lambda_handler',
            timeout=core.Duration.seconds(30),
            memory_size=512,
            environment={
                'SUBSCRIPTIONS_TABLE': subscriptions_table.table_name,
                'USERS_TABLE': f'careervp-users-{self.node.try_get_context("stage")}',
                'USAGE_TABLE': f'careervp-usage-{self.node.try_get_context("stage")}',
            }
        )

        # Permissions
        subscriptions_table.grant_read_write_data(billing_lambda)

        # SSM parameters (pre-created, not managed by CDK)
        stripe_secret = ssm.StringParameter.from_string_parameter_attributes(
            self, 'StripeSecret',
            parameter_name=f'/careervp/{self.node.try_get_context("stage")}/stripe_secret_key',
        )
        stripe_secret.grant_read(billing_lambda)
```

**Verification:**
- Unit test F-SUB-018 snapshot test confirms CDK output
- Integration test F-SUB-018-INT deploys stack and verifies resources exist

---

#### S-005.2: SSM Parameter Cold Start Handling

**Requirement:** Lambda reads SSM parameters at cold start; failures must not block request.

**Implementation:**
1. Load SSM parameters in Lambda `__init__` (before request)
2. Cache parameters in memory
3. If SSM read fails: retry with exponential backoff, or fail fast with 500 error
4. Log cold start time and parameter load time

**Code Location:** `src/backend/careervp/handlers/billing_handler.py`

**Pseudo-code:**
```python
import os
import logging
from aws_lambda_powertools import Logger

logger = Logger()

# Module-level initialization (runs once per container)
def load_ssm_parameters():
    ssm_client = boto3.client('ssm')
    try:
        stripe_secret = ssm_client.get_parameter(
            Name=f'/careervp/{os.getenv("STAGE")}/stripe_secret_key',
            WithDecryption=True
        )['Parameter']['Value']
        return stripe_secret
    except ssm_client.exceptions.ParameterNotFound:
        logger.exception("SSM parameter not found")
        raise RuntimeError("Missing SSM parameter: stripe_secret_key")

STRIPE_SECRET_KEY = None

def lambda_handler(event, context):
    global STRIPE_SECRET_KEY
    if not STRIPE_SECRET_KEY:
        STRIPE_SECRET_KEY = load_ssm_parameters()

    # ... rest of handler
```

**Verification:**
- Unit test F-SUB-019 confirms parameter loading
- Regression test F-SUB-019-R confirms all env vars covered

---

#### S-005.3: CORS Headers

**Requirement:** Apply correct CORS headers to all responses; prevent wildcard origins in production.

**Implementation:**
1. Define `ALLOWED_ORIGINS = ['https://app.careervp.com', 'http://localhost:3000']` in environment
2. For protected routes (`/billing/checkout`, `/billing/portal`, `/users/me/subscription`):
   - Check `Origin` header in request
   - If origin in `ALLOWED_ORIGINS`, return `Access-Control-Allow-Origin: <origin>`
   - Otherwise, return no origin header
3. For public route (`/billing/webhook`):
   - **Do NOT** return `Access-Control-Allow-Origin` header (webhooks are from Stripe, not browser)
   - Do NOT set to `*`

**Code Location:** `src/backend/careervp/logic/response_builder.py` → `build_cors_headers(origin, is_public_route=False)`

**Pseudo-code:**
```python
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

def build_cors_headers(origin, is_public_route=False):
    headers = {'Content-Type': 'application/json'}

    if is_public_route:
        # No CORS headers for public routes (webhooks)
        return headers

    if origin in ALLOWED_ORIGINS:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'

    return headers

# In Lambda handler:
def handle_checkout_post(event, context):
    origin = event.get('headers', {}).get('Origin')
    headers = build_cors_headers(origin, is_public_route=False)

    # ... rest of handler
    return {
        'statusCode': 200,
        'body': json.dumps({...}),
        'headers': headers
    }
```

**Verification:**
- Unit test F-SUB-020 confirms correct headers for allowed/disallowed origins
- Regression test F-SUB-020-R grep confirms no `*` in CORS config

---

---

## API Endpoints Reference

| Endpoint | Method | Auth | Request | Response | Tests |
|----------|--------|------|---------|----------|-------|
| `/billing/checkout` | POST | Cognito | `{plan, success_url, cancel_url}` | `{checkout_url}` | F-SUB-004, F-SUB-005, F-SUB-006 |
| `/billing/portal` | POST | Cognito | `{return_url}` | `{portal_url}` | F-SUB-007 |
| `/users/me/subscription` | GET | Cognito | — | `{subscription, has_active_subscription}` | F-SUB-008 |
| `/billing/webhook` | POST | None (signature) | Stripe webhook | `{received: true}` | F-SUB-009, F-SUB-010–016 |
| `/jobs` | POST | Cognito | Job data | Job response | F-SUB-001, 002, 003 (quota check) |

---

## Test Execution Guide

### Prerequisites
```bash
cd src/frontend
npm install
```

### Run All Tests
```bash
npm test
```

### Run by Category
```bash
npm run test:unit              # Unit tests only (~30s)
npm run test:integration       # Integration tests (~2m, requires Stripe test creds)
npm run test:e2e               # E2E tests (~3m, requires Stripe CLI + test user)
npm run test:regression        # Regression tests (~1m)
npm run test:coverage          # All tests with coverage report
```

### Run Specific Test File
```bash
npx jest src/frontend/tests/unit/trial.test.ts
npx jest src/frontend/tests/integration/checkout.integration.test.ts
npx jest src/frontend/tests/e2e/upgrade-flow.e2e.test.ts
```

### Manual Testing

#### 1. Test Trial Activation
```bash
# Create test user in Cognito
aws cognito-idp admin-create-user --user-pool-id us-east-1_WiHMRqLpe --username test-trial --temporary-password TempPass123! --region us-east-1

# Verify User and Usage records created in DynamoDB
aws dynamodb get-item --table-name careervp-users-dev --key '{"user_id": {"S": "test-trial"}}'
aws dynamodb get-item --table-name careervp-usage-dev --key '{"user_id": {"S": "test-trial"}}'
```

#### 2. Test Checkout Session
```bash
# Get JWT for test user
JWT=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id us-east-1_WiHMRqLpe \
  --client-id <CLIENT_ID> \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=test-user,PASSWORD=TestPass123! \
  --region us-east-1 | jq -r '.AuthenticationResult.IdToken')

# Call checkout endpoint
curl -X POST https://dev-api.careervp.com/billing/checkout \
  -H "Authorization: $JWT" \
  -H "Content-Type: application/json" \
  -d '{"plan": "monthly", "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}", "cancel_url": "https://app.careervp.com/settings/billing"}'
```

#### 3. Test Webhook (Using Stripe CLI)
```bash
# Start webhook relay
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook

# In another terminal, trigger test event
stripe trigger checkout.session.completed --override subscription='sub_test' --override customer='cus_test' --override metadata.user_id='test-user' --override metadata.plan='monthly'

# Check DynamoDB for created subscription
aws dynamodb query --table-name careervp-subscriptions-dev \
  --index-name UserSubscriptionIndex \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid": {"S": "test-user"}}' \
  --region us-east-1
```

#### 4. Test Access Control
```bash
# With expired trial and no subscription
curl -X POST https://dev-api.careervp.com/jobs \
  -H "Authorization: $JWT" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected: 403 trial_expired
```

### Debug CloudWatch Logs
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/careervp-billing-dev --follow --region us-east-1

# Search for specific user
aws logs filter-log-events \
  --log-group-name /aws/lambda/careervp-billing-dev \
  --filter-pattern "test-user" \
  --region us-east-1
```

### Coverage Report
```bash
npm run test:coverage
open coverage/index.html  # View HTML report
```

---

## Error Handling & Status Codes

| Status | Error Code | Message | Example |
|--------|-----------|---------|---------|
| `200` | — | Success | Checkout session created |
| `400` | `invalid_plan` | Plan must be monthly or quarterly | Invalid POST body |
| `400` | `invalid_signature` | Webhook signature verification failed | Webhook from non-Stripe source |
| `403` | `trial_expired` | Your trial has expired | Job creation after 14 days |
| `403` | `trial_exhausted` | No credits remaining | Job creation with 0 credits |
| `403` | `subscription_inactive` | Subscription is {status} | Access blocked on past_due |
| `404` | `no_billing_account` | No billing account found | Portal access without customer ID |
| `409` | `subscription_exists` | User already has active subscription | Checkout with existing subscription |
| `500` | `internal_error` | Internal server error | Lambda or Stripe API error |

---

## Regression Prevention Checklist

### Data Model Constraints
- [ ] User `created_at` is immutable (set once, never updated)
- [ ] Usage `remaining` never goes below 0 (guard in deduct_credit)
- [ ] Subscription `subscription_id` is primary key (unique per subscription)
- [ ] All timestamps are ISO 8601 or Unix timestamps (never mixed)

### API Contract
- [ ] `/jobs` endpoint still works (quota check added, no breaking changes)
- [ ] All existing endpoints return same response format
- [ ] Error responses follow `{error, message, details?}` format
- [ ] CORS headers never include `*` in production

### Webhook Security
- [ ] Signature verification is mandatory (cannot be bypassed)
- [ ] Webhook endpoint has NO Cognito authorizer
- [ ] Raw body is never transformed (API Gateway passthrough)
- [ ] Failed signature verification returns immediately (no DynamoDB writes)

### State Transitions
- [ ] Only `active` subscriptions grant access
- [ ] Trial users can access existing jobs (read-only)
- [ ] Expired trials cannot create new jobs
- [ ] Plan changes do not reset subscription start date
- [ ] Cancellation does not delete subscription record (mark as canceled)

### Stripe Integration
- [ ] No duplicate `stripe.Customer.create()` calls
- [ ] Customer ID reused from User record
- [ ] Webhook events are idempotent (upsert, not insert)
- [ ] All Stripe fields (subscription_id, customer_id) are validated before use

### Testing
- [ ] All 129 test cases pass
- [ ] Coverage >80% for billing module
- [ ] Manual webhook testing via Stripe CLI
- [ ] E2E test with real Stripe test card
- [ ] Regression tests pass for boundary cases

---

## Implementation Order

Implement features in this order to allow tests to pass incrementally:

1. **S-001** (Trial & Quota) → Unit tests F-SUB-001, 002, 003 pass
2. **S-002** (Checkout) → Unit tests F-SUB-004, 005, 006 + Integration test F-SUB-004-INT pass
3. **S-003** (Subscription Lifecycle) → Unit tests F-SUB-007, 008 pass
4. **S-004** (Webhooks) → Unit tests F-SUB-009–017 pass; E2E tests F-SUB-010-E2E, etc. pass
5. **S-005** (Portal & Access) → Unit tests F-SUB-018, 019, 020 + Integration test F-SUB-018-INT pass
6. **Regression Tests** → All F-SUB-*-R tests pass

---

## File Structure Summary

```
src/backend/careervp/
├── models/
│   ├── user.py              # User dataclass
│   ├── usage.py             # Usage dataclass
│   ├── subscription.py      # Subscription dataclass + enums
│   └── errors.py            # ApiError class
├── logic/
│   ├── subscription_service.py    # check_trial_and_quota, deduct_credit
│   ├── stripe_service.py          # get_or_create_stripe_customer
│   ├── webhook_handlers.py        # handle_checkout_session_completed, etc.
│   └── response_builder.py        # build_cors_headers
├── dal/
│   ├── users_dal.py         # UsersDAL (get_user, update_stripe_customer_id, etc.)
│   ├── usage_dal.py         # UsageDAL (get_usage, decrement_remaining, set_unlimited_usage)
│   └── subscriptions_dal.py  # SubscriptionsDAL (upsert, query by user/customer, etc.)
└── handlers/
    └── billing_handler.py   # Lambda entry points (handle_checkout_post, handle_webhook_post, etc.)

infra/careervp/
└── billing_stack.py         # CDK stack for Lambda, API Gateway, DynamoDB, SSM

src/frontend/tests/
├── setup.ts                 # Test utilities and mock factories
├── payloads/                # 22 JSON fixtures
├── unit/                    # 13 unit test files
├── integration/             # 3 integration test files
├── e2e/                     # 5 E2E test files
└── regression/              # 7 regression test files
```

---

## Next Steps

1. Use this specification to generate implementation code
2. Each implementation spec (S-001.1, S-001.2, etc.) maps to one or more test cases
3. Run tests incrementally as each spec is implemented
4. Ensure no breaking changes to existing APIs
5. Follow error handling and regression prevention checklist
