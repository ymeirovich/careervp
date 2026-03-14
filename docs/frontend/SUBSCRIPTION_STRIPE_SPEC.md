# CareerVP Subscription & Stripe Integration — Backend Specification

**Status:** Design — Pre-Implementation
**Last Updated:** 2026-03-08
**Audience:** Backend developer, AI code generation
**Covers:** Stripe products/prices, DynamoDB subscription table, all billing endpoints, webhook handling, subscription state machine

---

## Table of Contents

1. [Overview](#1-overview)
2. [Stripe Account Setup](#2-stripe-account-setup)
3. [Subscription State Machine](#3-subscription-state-machine)
4. [DynamoDB Schema — Subscriptions Table](#4-dynamodb-schema--subscriptions-table)
5. [Endpoint Reference](#5-endpoint-reference)
6. [Lambda Handler Design](#6-lambda-handler-design)
7. [Webhook Handler](#7-webhook-handler)
8. [DAL Functions](#8-dal-functions)
9. [Quota Enforcement Integration](#9-quota-enforcement-integration)
10. [CDK Infrastructure](#10-cdk-infrastructure)
11. [Testing Strategy](#11-testing-strategy)

---

## 1. Overview

CareerVP users get a **7-day free trial** with 3 application credits. After the trial ends, they must subscribe to continue using the product. Stripe handles all payment processing via hosted UI — no card data ever touches CareerVP servers.

**Flow summary:**
1. User signs up → trial record created in DynamoDB automatically
2. Trial expires OR credits exhausted → user sees upgrade prompt
3. User clicks upgrade → `POST /billing/checkout` → backend creates Stripe checkout session → frontend redirects to Stripe
4. Payment succeeds → Stripe fires `checkout.session.completed` webhook → backend updates subscription → user gets unlimited access
5. Monthly renewal → Stripe auto-charges → `invoice.payment_succeeded` webhook → no action needed
6. Payment fails → `invoice.payment_failed` webhook → mark `past_due` → show banner to user
7. User cancels → `customer.subscription.deleted` webhook → mark `canceled` → block access at next API call

---

## 2. Stripe Account Setup

### Products & Prices

Create in Stripe Dashboard (or via Stripe CLI for test mode):

```
Product: CareerVP Pro
  Price 1 (Monthly):
    ID: store as STRIPE_PRICE_MONTHLY env var
    Amount: $19.00 USD
    Interval: monthly
    Nickname: "Monthly"

  Price 2 (Annual):
    ID: store as STRIPE_PRICE_ANNUAL env var
    Amount: $149.00 USD
    Interval: yearly
    Nickname: "Annual"
```

### Webhook Endpoint

Register in Stripe Dashboard:
- **URL:** `https://dev-api.careervp.com/billing/webhook` (test) / `https://api.careervp.com/billing/webhook` (prod)
- **Events to listen for:**
  - `checkout.session.completed`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- **Webhook signing secret:** Store as `STRIPE_WEBHOOK_SECRET` in Lambda environment

### Environment Variables Required

```bash
STRIPE_SECRET_KEY=sk_test_xxx          # sk_live_xxx in prod
STRIPE_PRICE_MONTHLY=price_xxx
STRIPE_PRICE_ANNUAL=price_yyy
STRIPE_WEBHOOK_SECRET=whsec_xxx
SUBSCRIPTIONS_TABLE_NAME=careervp-subscriptions-dev
USERS_TABLE_NAME=careervp-users-dev
USAGE_TABLE_NAME=careervp-usage-dev
```

---

## 3. Subscription State Machine

```
[signup]
    │
    ▼
 trialing ──── trial expires (7 days) ──────────────────► expired
    │                                                         │
    │  user upgrades (checkout.session.completed)             │ user upgrades
    ▼                                                         ▼
 active ◄─────────────────────────────────────────────── active
    │
    │ invoice.payment_failed (1st/2nd)
    ▼
 past_due ──── invoice.payment_failed (3rd, or subscription deleted) ──► canceled
    │
    │ invoice.payment_succeeded (user updates card)
    ▼
 active

[any state] ── user cancels in portal ─► canceled
              (customer.subscription.deleted)
```

### State Definitions

| State | Access | Description |
|---|---|---|
| `trialing` | Full (limited credits) | Default on signup; 3 credits, 7 days |
| `active` | Full (unlimited) | Stripe subscription active and paid |
| `past_due` | Blocked | Payment failed; grace period for card update |
| `canceled` | Blocked | Subscription ended; must re-subscribe |
| `expired` | Blocked | Trial ended without upgrading |

### Access Enforcement

The existing `POST /jobs` handler already checks trial status. This logic must be extended:

```python
# In job_handler.py — existing trial check
def _check_access(user_id: str, usage_dal, subscription_dal) -> None:
    """Raises AccessDeniedError if user cannot create a job."""
    sub = subscription_dal.get_subscription_by_user(user_id)

    if sub:
        status = sub.get('status')
        if status == 'active':
            return   # unlimited access
        if status == 'trialing':
            # Check credits
            usage = usage_dal.get_usage(user_id)
            remaining = usage.get('remaining', 0)
            if remaining <= 0:
                raise AccessDeniedError('trial_exhausted')
            return
        if status in ('past_due', 'canceled', 'expired'):
            raise AccessDeniedError('subscription_required')

    # No subscription record — check if trial is active by created_at
    user = users_dal.get_user(user_id)
    created_at = user.get('created_at')
    trial_end = _compute_trial_end(created_at)
    if _now() > trial_end:
        raise AccessDeniedError('trial_expired')

    # Trial active — check credits
    usage = usage_dal.get_usage(user_id)
    if usage.get('remaining', 0) <= 0:
        raise AccessDeniedError('trial_exhausted')
```

---

## 4. DynamoDB Schema — Subscriptions Table

### Table: `careervp-subscriptions-{stage}`

**Primary Key:**
- Partition key: `subscription_id` (string) — Stripe subscription ID (`sub_xxx`)

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `subscription_id` | String | Stripe subscription ID — primary key |
| `user_id` | String | Cognito `sub` UUID |
| `customer_id` | String | Stripe customer ID (`cus_xxx`) |
| `status` | String | `trialing` \| `active` \| `past_due` \| `canceled` \| `expired` |
| `plan` | String | `monthly` \| `annual` |
| `stripe_price_id` | String | Stripe price ID |
| `current_period_start` | String | ISO 8601 — start of current billing period |
| `current_period_end` | String | ISO 8601 — end of current billing period |
| `trial_end` | String | ISO 8601 — when trial ends (null if not trialing) |
| `cancel_at_period_end` | Boolean | True if user requested cancel at end of period |
| `canceled_at` | String | ISO 8601 — when canceled (null if active) |
| `payment_failed_count` | Number | Number of consecutive payment failures (resets on success) |
| `last_invoice_id` | String | Most recent Stripe invoice ID |
| `created_at` | String | ISO 8601 |
| `updated_at` | String | ISO 8601 |

**Global Secondary Indexes:**

```
GSI 1: UserSubscriptionIndex
  Partition key: user_id
  Sort key:      created_at
  Projection:    ALL
  Purpose:       Look up subscription by user_id

GSI 2: StatusIndex
  Partition key: status
  Sort key:      user_id
  Projection:    ALL
  Purpose:       Query all users by subscription status (admin, billing jobs)

GSI 3: CustomerIndex
  Partition key: customer_id
  Projection:    ALL
  Purpose:       Look up subscription by Stripe customer_id (used in webhook handler)
```

### Example Item

```json
{
  "subscription_id": "sub_1Pxyz",
  "user_id": "a1b2c3d4-e5f6-...",
  "customer_id": "cus_Nabc",
  "status": "active",
  "plan": "monthly",
  "stripe_price_id": "price_1Pabc",
  "current_period_start": "2026-03-08T00:00:00Z",
  "current_period_end": "2026-04-08T00:00:00Z",
  "trial_end": null,
  "cancel_at_period_end": false,
  "canceled_at": null,
  "payment_failed_count": 0,
  "last_invoice_id": "in_1xyz",
  "created_at": "2026-02-01T10:30:00Z",
  "updated_at": "2026-03-08T00:01:00Z"
}
```

---

## 5. Endpoint Reference

### 5.1 POST /billing/checkout

Creates a Stripe Checkout session for a new subscription.

**Auth:** Required (Cognito JWT)

**Request Body:**
```json
{
  "plan": "monthly",
  "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.careervp.com/settings/billing"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `plan` | string | Yes | `"monthly"` or `"annual"` |
| `success_url` | string | Yes | Where Stripe redirects on success. Must include `{CHECKOUT_SESSION_ID}` placeholder |
| `cancel_url` | string | Yes | Where Stripe redirects if user cancels checkout |

**Backend Steps:**

1. Validate JWT → extract `user_id`
2. Validate `plan` value
3. Look up or create Stripe Customer for `user_id`
   - Query `CustomerIndex` GSI for existing `customer_id`
   - If none: `stripe.Customer.create(email=user_email, metadata={"user_id": user_id})`
   - Store `customer_id` on user record if new
4. Resolve Stripe price ID: `STRIPE_PRICE_MONTHLY` or `STRIPE_PRICE_ANNUAL`
5. Call `stripe.checkout.Session.create()`
6. Return checkout URL

**Success Response — 200:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_xxx"
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 400 | Invalid `plan` value |
| 400 | Missing `success_url` or `cancel_url` |
| 401 | Not authenticated |
| 409 | User already has an active subscription |
| 502 | Stripe API error |

---

### 5.2 POST /billing/portal

Creates a Stripe Customer Portal session.

**Auth:** Required

**Request Body:**
```json
{
  "return_url": "https://app.careervp.com/settings/billing"
}
```

**Backend Steps:**

1. Validate JWT → extract `user_id`
2. Look up `customer_id` for user from subscriptions table (CustomerIndex GSI)
3. Call `stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)`
4. Return portal URL

**Success Response — 200:**
```json
{
  "portal_url": "https://billing.stripe.com/session/xxx"
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 401 | Not authenticated |
| 404 | No Stripe customer found for user (never checked out) |
| 502 | Stripe API error |

---

### 5.3 GET /users/me/subscription

Returns the current user's subscription status.

**Auth:** Required

**Request:** No body

**Backend Steps:**

1. Validate JWT → extract `user_id`
2. Query `UserSubscriptionIndex` GSI for user's subscription
3. Return subscription data or `null` if none

**Success Response — 200:**
```json
{
  "subscription": {
    "subscription_id": "sub_1Pxyz",
    "customer_id": "cus_Nabc",
    "status": "active",
    "plan": "monthly",
    "current_period_end": "2026-04-08T00:00:00Z",
    "cancel_at_period_end": false,
    "trial_end": null
  },
  "has_active_subscription": true
}
```

When no subscription exists:
```json
{
  "subscription": null,
  "has_active_subscription": false
}
```

---

### 5.4 POST /billing/webhook

Receives Stripe webhook events. **This endpoint does NOT require Cognito auth** — it uses Stripe signature verification instead.

**Auth:** Stripe webhook signature (`Stripe-Signature` header)

**Important:** API Gateway must be configured to pass the raw body to Lambda (disable body parsing). The raw bytes are needed for signature verification.

**Request Headers:**
```
Stripe-Signature: t=1234567890,v1=abc...
Content-Type: application/json
```

**Request Body:** Raw Stripe event JSON (any of the 5 registered event types)

**Success Response — 200:**
```json
{ "received": true }
```

**Error Responses:**

| Status | Condition |
|---|---|
| 400 | Signature verification failed |
| 400 | Unknown or unhandled event type |
| 500 | Processing error (Stripe will retry) |

**Important:** Return 200 even for events you don't handle, otherwise Stripe will retry indefinitely.

---

## 6. Lambda Handler Design

### File: `handlers/billing_handler.py`

```python
import json
import os
import logging
import stripe
from shared.auth_utils import get_user_id_from_event
from shared.response_utils import build_response, build_error_response
from dal.subscription_dal import SubscriptionDAL
from dal.user_dal import UserDAL

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stripe.api_key = os.environ['STRIPE_SECRET_KEY']
PRICE_MAP = {
    'monthly': os.environ['STRIPE_PRICE_MONTHLY'],
    'annual': os.environ['STRIPE_PRICE_ANNUAL'],
}

dal = SubscriptionDAL(
    subscriptions_table=os.environ['SUBSCRIPTIONS_TABLE_NAME'],
    users_table=os.environ['USERS_TABLE_NAME'],
    usage_table=os.environ['USAGE_TABLE_NAME'],
)
user_dal = UserDAL(users_table=os.environ['USERS_TABLE_NAME'])


def lambda_handler(event: dict, context) -> dict:
    method = event.get('httpMethod', '')
    path = event.get('path', '')

    # Webhook — no Cognito auth; signature-verified separately
    if method == 'POST' and path == '/billing/webhook':
        return handle_webhook(event)

    # All other billing routes require auth
    try:
        user_id = get_user_id_from_event(event)
    except Exception:
        return build_error_response(401, 'Unauthorized')

    try:
        if method == 'POST' and path == '/billing/checkout':
            body = json.loads(event.get('body') or '{}')
            return handle_checkout(user_id, body)

        elif method == 'POST' and path == '/billing/portal':
            body = json.loads(event.get('body') or '{}')
            return handle_portal(user_id, body)

        elif method == 'GET' and path == '/users/me/subscription':
            return handle_get_subscription(user_id)

        else:
            return build_error_response(404, 'Not found')

    except ValueError as e:
        return build_error_response(400, str(e))
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return build_error_response(502, 'Payment provider error')
    except Exception as e:
        logger.error(f"Billing handler error: {e}", exc_info=True)
        return build_error_response(500, 'Internal server error')


def handle_checkout(user_id: str, body: dict) -> dict:
    plan = body.get('plan')
    success_url = body.get('success_url')
    cancel_url = body.get('cancel_url')

    if plan not in PRICE_MAP:
        raise ValueError(f"Invalid plan '{plan}'. Must be 'monthly' or 'annual'.")
    if not success_url or not cancel_url:
        raise ValueError('success_url and cancel_url are required')

    # Check for existing active subscription
    existing = dal.get_subscription_by_user(user_id)
    if existing and existing.get('status') == 'active':
        return build_error_response(409, 'User already has an active subscription')

    # Get or create Stripe customer
    customer_id = dal.get_customer_id(user_id)
    if not customer_id:
        user = user_dal.get_user(user_id)
        customer = stripe.Customer.create(
            email=user.get('email', ''),
            metadata={'user_id': user_id},
        )
        customer_id = customer.id
        dal.store_customer_id(user_id, customer_id)

    price_id = PRICE_MAP[plan]
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': user_id, 'plan': plan},
    )

    logger.info(f"Checkout session created for user {user_id}: {session.id}")
    return build_response(200, {'checkout_url': session.url})


def handle_portal(user_id: str, body: dict) -> dict:
    return_url = body.get('return_url', 'https://app.careervp.com/settings/billing')

    customer_id = dal.get_customer_id(user_id)
    if not customer_id:
        return build_error_response(404, 'No billing account found. Please subscribe first.')

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )

    return build_response(200, {'portal_url': portal_session.url})


def handle_get_subscription(user_id: str) -> dict:
    sub = dal.get_subscription_by_user(user_id)
    if not sub:
        return build_response(200, {'subscription': None, 'has_active_subscription': False})

    return build_response(200, {
        'subscription': {
            'subscription_id': sub.get('subscription_id'),
            'customer_id': sub.get('customer_id'),
            'status': sub.get('status'),
            'plan': sub.get('plan'),
            'current_period_end': sub.get('current_period_end'),
            'cancel_at_period_end': sub.get('cancel_at_period_end', False),
            'trial_end': sub.get('trial_end'),
        },
        'has_active_subscription': sub.get('status') == 'active',
    })
```

---

## 7. Webhook Handler

### File: `handlers/webhook_handler.py`

```python
import json
import os
import logging
import stripe
from shared.response_utils import build_response, build_error_response
from dal.subscription_dal import SubscriptionDAL
from dal.user_dal import UserDAL

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stripe.api_key = os.environ['STRIPE_SECRET_KEY']
WEBHOOK_SECRET = os.environ['STRIPE_WEBHOOK_SECRET']

PRICE_TO_PLAN = {
    os.environ.get('STRIPE_PRICE_MONTHLY', ''): 'monthly',
    os.environ.get('STRIPE_PRICE_ANNUAL', ''): 'annual',
}

dal = SubscriptionDAL(
    subscriptions_table=os.environ['SUBSCRIPTIONS_TABLE_NAME'],
    users_table=os.environ['USERS_TABLE_NAME'],
    usage_table=os.environ['USAGE_TABLE_NAME'],
)


def handle_webhook(event: dict) -> dict:
    """Entry point from billing_handler.py"""
    # API GW passes raw body as string
    payload = event.get('body', '')
    sig_header = (event.get('headers') or {}).get('Stripe-Signature', '')

    try:
        stripe_event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.warning('Stripe signature verification failed')
        return build_error_response(400, 'Invalid signature')
    except ValueError:
        return build_error_response(400, 'Invalid payload')

    event_type = stripe_event['type']
    data = stripe_event['data']['object']

    logger.info(f"Processing Stripe event: {event_type}")

    try:
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data)

        elif event_type == 'invoice.payment_succeeded':
            _handle_invoice_succeeded(data)

        elif event_type == 'invoice.payment_failed':
            _handle_invoice_failed(data)

        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(data)

        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data)

        else:
            logger.info(f"Unhandled event type: {event_type} — acknowledging")

    except Exception as e:
        logger.error(f"Webhook processing error for {event_type}: {e}", exc_info=True)
        # Return 500 so Stripe retries
        return build_error_response(500, 'Processing error')

    return build_response(200, {'received': True})


def _handle_checkout_completed(session: dict) -> None:
    """
    Fires when user completes Stripe Checkout.
    Creates or updates subscription record. Resets usage quota.
    """
    subscription_id = session.get('subscription')
    customer_id = session.get('customer')
    user_id = session.get('metadata', {}).get('user_id')
    plan = session.get('metadata', {}).get('plan', 'monthly')

    if not subscription_id or not user_id:
        logger.error(f"checkout.session.completed missing subscription or user_id: {session}")
        return

    # Fetch full subscription from Stripe to get period dates
    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    dal.upsert_subscription({
        'subscription_id': subscription_id,
        'user_id': user_id,
        'customer_id': customer_id,
        'status': 'active',
        'plan': plan,
        'stripe_price_id': stripe_sub['items']['data'][0]['price']['id'],
        'current_period_start': _ts_to_iso(stripe_sub['current_period_start']),
        'current_period_end': _ts_to_iso(stripe_sub['current_period_end']),
        'trial_end': None,
        'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
        'canceled_at': None,
        'payment_failed_count': 0,
    })

    # Remove credit limits — paid users get unlimited applications
    dal.set_unlimited_usage(user_id)

    logger.info(f"Subscription activated for user {user_id}: {subscription_id}")


def _handle_invoice_succeeded(invoice: dict) -> None:
    """
    Fires on successful monthly renewal.
    Reset payment_failed_count. Confirm status is active.
    """
    subscription_id = invoice.get('subscription')
    customer_id = invoice.get('customer')

    if not subscription_id:
        return

    sub = dal.get_subscription_by_stripe_id(subscription_id)
    if not sub:
        logger.warning(f"invoice.payment_succeeded: no local record for {subscription_id}")
        return

    dal.update_subscription_fields(subscription_id, {
        'status': 'active',
        'payment_failed_count': 0,
        'last_invoice_id': invoice.get('id'),
    })
    logger.info(f"Invoice succeeded for subscription {subscription_id}")


def _handle_invoice_failed(invoice: dict) -> None:
    """
    Fires when payment fails. After 3 failures, Stripe cancels the subscription
    (triggers customer.subscription.deleted separately).
    We mark past_due after first failure.
    """
    subscription_id = invoice.get('subscription')
    attempt_count = invoice.get('attempt_count', 1)

    if not subscription_id:
        return

    sub = dal.get_subscription_by_stripe_id(subscription_id)
    if not sub:
        return

    dal.update_subscription_fields(subscription_id, {
        'status': 'past_due',
        'payment_failed_count': attempt_count,
        'last_invoice_id': invoice.get('id'),
    })
    logger.warning(f"Payment failed (attempt {attempt_count}) for subscription {subscription_id}")


def _handle_subscription_updated(stripe_sub: dict) -> None:
    """
    Fires when subscription is modified (plan change, cancel_at_period_end toggled).
    Sync key fields to DynamoDB.
    """
    subscription_id = stripe_sub.get('id')
    if not subscription_id:
        return

    price_id = stripe_sub['items']['data'][0]['price']['id']
    plan = PRICE_TO_PLAN.get(price_id, 'monthly')

    dal.update_subscription_fields(subscription_id, {
        'status': stripe_sub.get('status'),
        'plan': plan,
        'stripe_price_id': price_id,
        'current_period_start': _ts_to_iso(stripe_sub['current_period_start']),
        'current_period_end': _ts_to_iso(stripe_sub['current_period_end']),
        'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
    })
    logger.info(f"Subscription updated: {subscription_id}")


def _handle_subscription_deleted(stripe_sub: dict) -> None:
    """
    Fires when subscription is fully canceled (either by user or after max payment failures).
    Mark canceled — block access at next API call.
    """
    from datetime import datetime, timezone

    subscription_id = stripe_sub.get('id')
    if not subscription_id:
        return

    dal.update_subscription_fields(subscription_id, {
        'status': 'canceled',
        'canceled_at': datetime.now(timezone.utc).isoformat(),
        'cancel_at_period_end': False,
    })
    logger.info(f"Subscription canceled: {subscription_id}")


def _ts_to_iso(unix_ts: int) -> str:
    """Convert Unix timestamp to ISO 8601 string."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
```

---

## 8. DAL Functions

### File: `dal/subscription_dal.py`

```python
import boto3
import logging
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger()


class SubscriptionDAL:
    def __init__(self, subscriptions_table: str, users_table: str, usage_table: str):
        dynamodb = boto3.resource('dynamodb')
        self.subscriptions = dynamodb.Table(subscriptions_table)
        self.users = dynamodb.Table(users_table)
        self.usage = dynamodb.Table(usage_table)

    def get_subscription_by_user(self, user_id: str) -> Optional[dict]:
        """Look up subscription by user_id via UserSubscriptionIndex GSI."""
        resp = self.subscriptions.query(
            IndexName='UserSubscriptionIndex',
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get('Items', [])
        return items[0] if items else None

    def get_subscription_by_stripe_id(self, subscription_id: str) -> Optional[dict]:
        """Direct primary key lookup."""
        resp = self.subscriptions.get_item(Key={'subscription_id': subscription_id})
        return resp.get('Item')

    def get_customer_id(self, user_id: str) -> Optional[str]:
        """Return the Stripe customer_id for a user, or None."""
        sub = self.get_subscription_by_user(user_id)
        if sub:
            return sub.get('customer_id')
        # Also check user record (set during first checkout)
        user_resp = self.users.get_item(Key={'user_id': user_id})
        return user_resp.get('Item', {}).get('stripe_customer_id')

    def store_customer_id(self, user_id: str, customer_id: str) -> None:
        """Persist stripe_customer_id on the user record for fast retrieval."""
        self.users.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET stripe_customer_id = :cid, updated_at = :ua',
            ExpressionAttributeValues={
                ':cid': customer_id,
                ':ua': datetime.now(timezone.utc).isoformat(),
            }
        )

    def upsert_subscription(self, data: dict) -> None:
        """Create or fully replace a subscription record."""
        now = datetime.now(timezone.utc).isoformat()
        data['updated_at'] = now
        if 'created_at' not in data:
            data['created_at'] = now
        self.subscriptions.put_item(Item=data)

    def update_subscription_fields(self, subscription_id: str, fields: dict) -> None:
        """Partial update — only update the specified fields."""
        if not fields:
            return

        fields['updated_at'] = datetime.now(timezone.utc).isoformat()

        expr_parts = []
        expr_values = {}
        expr_names = {}

        for i, (key, val) in enumerate(fields.items()):
            placeholder = f':v{i}'
            name_placeholder = f'#k{i}'
            expr_parts.append(f'{name_placeholder} = {placeholder}')
            expr_values[placeholder] = val
            expr_names[name_placeholder] = key

        self.subscriptions.update_item(
            Key={'subscription_id': subscription_id},
            UpdateExpression='SET ' + ', '.join(expr_parts),
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )

    def set_unlimited_usage(self, user_id: str) -> None:
        """
        After successful checkout, set remaining = 9999 to signal unlimited.
        The job handler checks remaining > 0; 9999 is effectively unlimited.
        A cleaner approach: add a `subscription_active` boolean to usage record.
        """
        self.usage.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET remaining = :r, updated_at = :ua',
            ExpressionAttributeValues={
                ':r': 9999,
                ':ua': datetime.now(timezone.utc).isoformat(),
            }
        )
```

---

## 9. Quota Enforcement Integration

The existing trial check in `job_handler.py` must be updated to also check subscription status:

```python
# job_handler.py — updated _check_trial_and_quota()

def _check_trial_and_quota(user_id: str) -> None:
    """
    Called at the start of POST /jobs.
    Raises ApiError(403) if user cannot create a job.
    """
    sub = subscription_dal.get_subscription_by_user(user_id)

    if sub:
        status = sub.get('status')

        if status == 'active':
            return  # Paid — no quota check

        if status in ('past_due', 'canceled', 'expired'):
            raise ApiError(403, {
                'error': 'subscription_required',
                'message': 'Your subscription is inactive. Please update your payment method.'
            })

        if status == 'trialing':
            # Fall through to credit check below
            pass

    # Trial or no subscription — check credits
    usage = usage_dal.get_usage(user_id)
    remaining = int(usage.get('remaining', 0))

    if remaining <= 0:
        # Check if trial has expired
        user = user_dal.get_user(user_id)
        if _trial_expired(user.get('created_at')):
            raise ApiError(403, {'error': 'trial_expired'})
        raise ApiError(403, {'error': 'trial_exhausted'})


def _trial_expired(created_at_iso: str) -> bool:
    from datetime import datetime, timezone, timedelta
    try:
        created = datetime.fromisoformat(created_at_iso.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > created + timedelta(days=7)
    except Exception:
        return False
```

---

## 10. CDK Infrastructure

### New Lambda Functions

```python
# infra/careervp/api_construct.py

# Billing handler (checkout + portal + subscription status)
billing_handler = aws_lambda.Function(
    self, 'BillingHandler',
    function_name=f'careervp-billing-{stage}',
    runtime=aws_lambda.Runtime.PYTHON_3_12,
    code=aws_lambda.Code.from_asset('src/handlers'),
    handler='billing_handler.lambda_handler',
    timeout=Duration.seconds(30),
    memory_size=256,
    environment={
        'STRIPE_SECRET_KEY': stripe_key.string_value,
        'STRIPE_PRICE_MONTHLY': stripe_price_monthly.string_value,
        'STRIPE_PRICE_ANNUAL': stripe_price_annual.string_value,
        'STRIPE_WEBHOOK_SECRET': stripe_webhook_secret.string_value,
        'SUBSCRIPTIONS_TABLE_NAME': subscriptions_table.table_name,
        'USERS_TABLE_NAME': users_table.table_name,
        'USAGE_TABLE_NAME': usage_table.table_name,
    }
)

subscriptions_table.grant_read_write_data(billing_handler)
users_table.grant_read_write_data(billing_handler)
usage_table.grant_read_write_data(billing_handler)
```

### New DynamoDB Table

```python
subscriptions_table = aws_dynamodb.Table(
    self, 'SubscriptionsTable',
    table_name=f'careervp-subscriptions-{stage}',
    partition_key=aws_dynamodb.Attribute(
        name='subscription_id',
        type=aws_dynamodb.AttributeType.STRING
    ),
    billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.RETAIN,
)

# GSI 1: by user_id
subscriptions_table.add_global_secondary_index(
    index_name='UserSubscriptionIndex',
    partition_key=aws_dynamodb.Attribute(name='user_id', type=aws_dynamodb.AttributeType.STRING),
    sort_key=aws_dynamodb.Attribute(name='created_at', type=aws_dynamodb.AttributeType.STRING),
    projection_type=aws_dynamodb.ProjectionType.ALL,
)

# GSI 2: by status
subscriptions_table.add_global_secondary_index(
    index_name='StatusIndex',
    partition_key=aws_dynamodb.Attribute(name='status', type=aws_dynamodb.AttributeType.STRING),
    sort_key=aws_dynamodb.Attribute(name='user_id', type=aws_dynamodb.AttributeType.STRING),
    projection_type=aws_dynamodb.ProjectionType.ALL,
)

# GSI 3: by customer_id
subscriptions_table.add_global_secondary_index(
    index_name='CustomerIndex',
    partition_key=aws_dynamodb.Attribute(name='customer_id', type=aws_dynamodb.AttributeType.STRING),
    projection_type=aws_dynamodb.ProjectionType.ALL,
)
```

### API Gateway Routes

```python
billing = api.root.add_resource('billing')
billing.add_resource('checkout').add_method('POST', aws_apigateway.LambdaIntegration(billing_handler), authorizer=cognito_authorizer)
billing.add_resource('portal').add_method('POST', aws_apigateway.LambdaIntegration(billing_handler), authorizer=cognito_authorizer)

# Webhook: NO Cognito authorizer — Stripe signature verified in Lambda
billing.add_resource('webhook').add_method('POST', aws_apigateway.LambdaIntegration(billing_handler))

# Subscription status on /users/me path
users_me.add_resource('subscription').add_method('GET', aws_apigateway.LambdaIntegration(billing_handler), authorizer=cognito_authorizer)
```

### SSM Parameters (store secrets safely)

```python
stripe_key = aws_ssm.StringParameter.from_secure_string_parameter_attributes(
    self, 'StripeKey',
    parameter_name=f'/careervp/{stage}/stripe/secret-key',
    version=1,
)
stripe_price_monthly = aws_ssm.StringParameter.from_string_parameter_name(
    self, 'StripePriceMonthly',
    string_parameter_name=f'/careervp/{stage}/stripe/price-monthly',
)
```

---

## 11. Testing Strategy

### Unit Tests

| Test | What it covers |
|---|---|
| `test_checkout_creates_session.py` | Valid plan → correct Stripe call → returns URL |
| `test_checkout_invalid_plan.py` | `plan="weekly"` → 400 |
| `test_checkout_already_active.py` | Existing active sub → 409 |
| `test_portal_no_customer.py` | No customer_id → 404 |
| `test_webhook_signature_fail.py` | Bad sig → 400 |
| `test_webhook_checkout_completed.py` | `checkout.session.completed` → subscription created, usage set to 9999 |
| `test_webhook_invoice_failed.py` | `invoice.payment_failed` → status=past_due, count incremented |
| `test_webhook_subscription_deleted.py` | `customer.subscription.deleted` → status=canceled |
| `test_get_subscription_none.py` | No sub → `{ subscription: null, has_active_subscription: false }` |
| `test_quota_blocks_past_due.py` | `status=past_due` → POST /jobs returns 403 `subscription_required` |

### Stripe Test Mode

Use Stripe's test card numbers:
- Success: `4242 4242 4242 4242`
- Payment fails: `4000 0000 0000 0002`
- Requires 3DS: `4000 0025 0000 3155`

Use Stripe CLI to replay webhook events locally:
```bash
stripe listen --forward-to localhost:3000/billing/webhook
stripe trigger checkout.session.completed
stripe trigger invoice.payment_failed
```
