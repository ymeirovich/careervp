# CareerVP Admin Portal — Backend Specification

**Status:** Design — Pre-Implementation
**Last Updated:** 2026-03-08
**Audience:** Backend developer, AI code generation
**Covers:** All admin endpoints, Lambda logic, DynamoDB access patterns, auth enforcement

---

## Table of Contents

1. [Overview](#1-overview)
2. [Auth & Access Control](#2-auth--access-control)
3. [DynamoDB Access Patterns](#3-dynamodb-access-patterns)
4. [Endpoint Reference](#4-endpoint-reference)
5. [Lambda Handler Design](#5-lambda-handler-design)
6. [DAL Functions](#6-dal-functions)
7. [Error Handling](#7-error-handling)
8. [CDK Infrastructure](#8-cdk-infrastructure)

---

## 1. Overview

The admin portal exposes a set of protected API endpoints that allow internal operators to:

- View and search all users
- Inspect a user's subscription, usage, and application history
- Perform manual actions (extend trial, cancel subscription)
- View platform-wide metrics (total users, MRR, conversion rate)
- List all subscriptions by status

**All admin endpoints require:**
1. A valid Cognito JWT in the `Authorization` header
2. The `cognito:groups` claim to include `"Admins"`

Regular users who happen to send valid JWTs will receive `403 Forbidden`.

---

## 2. Auth & Access Control

### Cognito Admin Group

Create an `Admins` group in the Cognito User Pool. Assign admin users to this group via the Cognito Console or CDK.

Admin group membership is embedded in the ID token as:
```json
{
  "cognito:groups": ["Admins"],
  "sub": "user-uuid",
  "email": "admin@careervp.com"
}
```

### Shared Admin Auth Decorator

Every admin Lambda handler calls this check **before any business logic**:

```python
# shared/auth_utils.py

def require_admin(event: dict) -> str:
    """
    Validates the JWT and asserts Admins group membership.
    Returns the caller's user_id on success.
    Raises AdminAuthError (→ 403) if not admin.
    """
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})

    # API Gateway Cognito Authorizer populates claims automatically
    groups_raw = claims.get('cognito:groups', '')
    groups = groups_raw.split(',') if isinstance(groups_raw, str) else (groups_raw or [])

    if 'Admins' not in groups:
        raise AdminAuthError("Caller is not a member of the Admins group")

    user_id = claims.get('sub')
    if not user_id:
        raise AdminAuthError("Missing sub claim")

    return user_id


class AdminAuthError(Exception):
    pass
```

The API Gateway uses a **Cognito User Pool Authorizer** (same as all other endpoints). Group enforcement happens inside each Lambda — not at the API Gateway level (keeping infrastructure simple while maintaining security).

---

## 3. DynamoDB Access Patterns

Admin endpoints read from existing tables. No new tables are required. They may need additional GSIs.

### Existing Tables Used

| Table | Env Var | Used For |
|---|---|---|
| `careervp-users` | `USERS_TABLE_NAME` | User profile lookup |
| `careervp-subscriptions` | `SUBSCRIPTIONS_TABLE_NAME` | Subscription status per user |
| `careervp-jobs` | `JOBS_TABLE_NAME` | Jobs created per user |
| `careervp-applications` | `APPLICATIONS_TABLE_NAME` | Application pipeline state per job |
| `careervp-usage` | `USAGE_TABLE_NAME` | Applications used/remaining per user |

### Required GSIs

**On `careervp-users` table:** GSI for listing/searching all users.

```
GSI: AllUsersIndex
  Partition key: entity_type = "USER"   (static string — write "USER" on every user record)
  Sort key:      created_at             (ISO 8601 string)
  Projection:    ALL
```

This allows `Query(entity_type=USER, ScanIndexForward=False)` to list all users ordered by signup date.

**On `careervp-subscriptions` table:** GSI for filtering by status.

```
GSI: StatusIndex
  Partition key: status    ("trialing" | "active" | "past_due" | "canceled")
  Sort key:      user_id
  Projection:    ALL
```

This allows `Query(status="past_due")` to find all users with payment failures.

> **Note:** If DynamoDB Scan performance is acceptable at current user volumes (< 10,000 users), the AllUsersIndex GSI can be deferred. Use `Scan` with `FilterExpression` as a short-term alternative.

---

## 4. Endpoint Reference

### 4.1 GET /admin/users

List all users with pagination, search, and optional status filter.

**Auth:** Admin group required

**Query Parameters:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | int | No | 1 | Page number (1-based) |
| `page_size` | int | No | 20 | Results per page (max 100) |
| `search` | string | No | — | Filter by email or name prefix |
| `subscription_status` | string | No | — | Filter: `trialing`, `active`, `past_due`, `canceled` |

**Request:** No body

**Success Response — 200:**
```json
{
  "users": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "name": "Jane Smith",
      "created_at": "2026-01-15T10:30:00Z",
      "subscription_status": "trialing",
      "applications_used": 2,
      "applications_remaining": 1,
      "trial_active": true,
      "last_active_at": "2026-03-07T14:22:00Z"
    }
  ],
  "total": 342,
  "page": 1,
  "page_size": 20
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 400 | Invalid page or page_size parameter |
| 401 | Missing or invalid JWT |
| 403 | Not an admin |

---

### 4.2 GET /admin/users/{userId}

Get full detail for a single user.

**Auth:** Admin group required

**Path Parameters:** `userId` — the Cognito `sub` UUID

**Request:** No body

**Success Response — 200:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "Jane Smith",
  "created_at": "2026-01-15T10:30:00Z",
  "subscription_status": "active",
  "applications_used": 3,
  "applications_remaining": 0,
  "trial_active": false,
  "last_active_at": "2026-03-07T14:22:00Z",
  "cv_count": 1,
  "subscription": {
    "subscription_id": "sub_1abc",
    "customer_id": "cus_xyz",
    "status": "active",
    "plan": "monthly",
    "current_period_end": "2026-04-08T00:00:00Z"
  },
  "jobs": [
    {
      "job_id": "uuid",
      "title": "Senior Engineer",
      "company_name": "Acme Corp",
      "status": "active",
      "created_at": "2026-03-01T09:00:00Z",
      "application_state": "artifacts_completed"
    }
  ]
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 403 | Not admin |
| 404 | User not found |

---

### 4.3 GET /admin/metrics

Return platform-wide KPI metrics.

**Auth:** Admin group required

**Request:** No body

**Success Response — 200:**
```json
{
  "total_users": 342,
  "active_subscriptions": 47,
  "trialing_users": 218,
  "past_due_users": 8,
  "churned_users": 69,
  "trial_to_paid_rate": 0.177,
  "mrr": 89300,
  "applications_created_today": 14,
  "applications_created_this_week": 87,
  "new_users_today": 6,
  "new_users_this_week": 31
}
```

**Note:** `mrr` is in cents (89300 = $893.00). Frontend divides by 100.

---

### 4.4 POST /admin/users/{userId}/trial

Manually extend a user's trial period.

**Auth:** Admin group required

**Path Parameters:** `userId`

**Request Body:**
```json
{
  "extend_days": 7
}
```

**Success Response — 200:**
```json
{
  "user_id": "uuid",
  "new_trial_end": "2026-03-15T00:00:00Z",
  "extended_by_days": 7
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 400 | `extend_days` missing, not an integer, or <= 0 |
| 403 | Not admin |
| 404 | User not found |
| 409 | User is not on trial (already converted or canceled) |

---

### 4.5 POST /admin/users/{userId}/subscription/cancel

Immediately cancel a user's Stripe subscription.

**Auth:** Admin group required

**Path Parameters:** `userId`

**Request Body:** None (empty `{}` acceptable)

**Success Response — 200:**
```json
{
  "user_id": "uuid",
  "subscription_id": "sub_1abc",
  "status": "canceled",
  "canceled_at": "2026-03-08T12:00:00Z"
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 403 | Not admin |
| 404 | User not found, or no active subscription |
| 409 | Subscription already canceled |
| 502 | Stripe API error |

---

### 4.6 GET /admin/subscriptions

List all subscriptions with optional status filter.

**Auth:** Admin group required

**Query Parameters:**

| Param | Type | Required | Default |
|---|---|---|---|
| `status` | string | No | all |
| `page` | int | No | 1 |
| `page_size` | int | No | 20 |

**Success Response — 200:**
```json
{
  "subscriptions": [
    {
      "subscription_id": "sub_1abc",
      "customer_id": "cus_xyz",
      "user_id": "uuid",
      "user_email": "user@example.com",
      "status": "past_due",
      "plan": "monthly",
      "current_period_end": "2026-03-10T00:00:00Z",
      "created_at": "2026-02-08T00:00:00Z"
    }
  ],
  "total": 55,
  "page": 1,
  "page_size": 20
}
```

---

## 5. Lambda Handler Design

All admin handlers follow the same pattern:

```
Request → API GW → admin_handler.py → require_admin() → business logic → admin_dal.py → DynamoDB
```

### File: `handlers/admin_handler.py`

```python
import json
import os
import logging
from shared.auth_utils import require_admin, AdminAuthError
from shared.response_utils import build_response, build_error_response
from dal.admin_dal import AdminDAL

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dal = AdminDAL(
    users_table=os.environ['USERS_TABLE_NAME'],
    subscriptions_table=os.environ['SUBSCRIPTIONS_TABLE_NAME'],
    jobs_table=os.environ['JOBS_TABLE_NAME'],
    applications_table=os.environ['APPLICATIONS_TABLE_NAME'],
    usage_table=os.environ.get('USAGE_TABLE_NAME', ''),
)


def lambda_handler(event: dict, context) -> dict:
    try:
        caller_id = require_admin(event)
    except AdminAuthError as e:
        return build_error_response(403, str(e))

    method = event.get('httpMethod', '')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    query_params = event.get('queryStringParameters') or {}

    try:
        # Route dispatch
        if method == 'GET' and path == '/admin/users':
            return handle_list_users(query_params)

        elif method == 'GET' and '/admin/users/' in path and path.endswith('/') is False and len(path_params) == 1:
            user_id = path_params.get('userId')
            return handle_get_user(user_id)

        elif method == 'GET' and path == '/admin/metrics':
            return handle_get_metrics()

        elif method == 'POST' and '/trial' in path:
            user_id = path_params.get('userId')
            body = json.loads(event.get('body') or '{}')
            return handle_extend_trial(user_id, body)

        elif method == 'POST' and '/subscription/cancel' in path:
            user_id = path_params.get('userId')
            return handle_cancel_subscription(user_id)

        elif method == 'GET' and path == '/admin/subscriptions':
            return handle_list_subscriptions(query_params)

        else:
            return build_error_response(404, 'Not found')

    except ValueError as e:
        return build_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Admin handler error: {e}", exc_info=True)
        return build_error_response(500, 'Internal server error')


def handle_list_users(query_params: dict) -> dict:
    page = int(query_params.get('page', 1))
    page_size = min(int(query_params.get('page_size', 20)), 100)
    search = query_params.get('search')
    status_filter = query_params.get('subscription_status')

    if page < 1 or page_size < 1:
        raise ValueError('page and page_size must be positive integers')

    result = dal.list_users(page=page, page_size=page_size, search=search, status_filter=status_filter)
    return build_response(200, result)


def handle_get_user(user_id: str) -> dict:
    user = dal.get_user_detail(user_id)
    if not user:
        return build_error_response(404, 'User not found')
    return build_response(200, user)


def handle_get_metrics() -> dict:
    metrics = dal.get_platform_metrics()
    return build_response(200, metrics)


def handle_extend_trial(user_id: str, body: dict) -> dict:
    extend_days = body.get('extend_days')
    if not isinstance(extend_days, int) or extend_days <= 0:
        raise ValueError('extend_days must be a positive integer')

    result = dal.extend_user_trial(user_id, extend_days)
    if result is None:
        return build_error_response(404, 'User not found')
    if result == 'not_trialing':
        return build_error_response(409, 'User is not currently on a trial')
    return build_response(200, result)


def handle_cancel_subscription(user_id: str) -> dict:
    import stripe
    stripe.api_key = os.environ['STRIPE_SECRET_KEY']

    sub = dal.get_subscription_by_user(user_id)
    if not sub:
        return build_error_response(404, 'No active subscription found for user')
    if sub['status'] == 'canceled':
        return build_error_response(409, 'Subscription is already canceled')

    try:
        stripe.Subscription.cancel(sub['subscription_id'])
    except stripe.error.StripeError as e:
        logger.error(f"Stripe cancel error: {e}")
        return build_error_response(502, 'Stripe API error')

    dal.update_subscription_status(sub['subscription_id'], 'canceled')
    return build_response(200, {
        'user_id': user_id,
        'subscription_id': sub['subscription_id'],
        'status': 'canceled',
        'canceled_at': _now_iso(),
    })


def handle_list_subscriptions(query_params: dict) -> dict:
    status = query_params.get('status')
    page = int(query_params.get('page', 1))
    page_size = min(int(query_params.get('page_size', 20)), 100)
    result = dal.list_subscriptions(status=status, page=page, page_size=page_size)
    return build_response(200, result)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

---

## 6. DAL Functions

### File: `dal/admin_dal.py`

```python
import boto3
import os
import logging
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger()


class AdminDAL:
    def __init__(self, users_table, subscriptions_table, jobs_table, applications_table, usage_table):
        dynamodb = boto3.resource('dynamodb')
        self.users = dynamodb.Table(users_table)
        self.subscriptions = dynamodb.Table(subscriptions_table)
        self.jobs = dynamodb.Table(jobs_table)
        self.applications = dynamodb.Table(applications_table)
        self.usage = dynamodb.Table(usage_table) if usage_table else None

    # ─── LIST USERS ───────────────────────────────────────────────────────────

    def list_users(self, page: int, page_size: int, search: Optional[str], status_filter: Optional[str]) -> dict:
        """
        Scan users table with optional search filter.
        For MVP: DynamoDB Scan (acceptable under ~10k users).
        For scale: use AllUsersIndex GSI + Query.
        """
        filter_expr = None
        if search:
            filter_expr = Attr('email').contains(search) | Attr('name').contains(search)

        scan_kwargs = {'FilterExpression': filter_expr} if filter_expr else {}
        all_users = self._scan_all(self.users, **scan_kwargs)

        # Join subscription status for each user
        user_ids = [u['user_id'] for u in all_users]
        subscriptions = self._batch_get_subscriptions(user_ids)
        usage_map = self._batch_get_usage(user_ids)

        enriched = []
        for u in all_users:
            uid = u['user_id']
            sub = subscriptions.get(uid)
            usage = usage_map.get(uid, {})
            row = {
                'user_id': uid,
                'email': u.get('email', ''),
                'name': u.get('name', ''),
                'created_at': u.get('created_at', ''),
                'subscription_status': sub.get('status') if sub else None,
                'applications_used': int(usage.get('used', 0)),
                'applications_remaining': int(usage.get('remaining', 0)),
                'trial_active': sub.get('status') == 'trialing' if sub else False,
                'last_active_at': u.get('last_active_at'),
            }
            enriched.append(row)

        # Apply status filter post-join
        if status_filter:
            enriched = [r for r in enriched if r['subscription_status'] == status_filter]

        # Sort by created_at desc, paginate
        enriched.sort(key=lambda r: r['created_at'], reverse=True)
        total = len(enriched)
        start = (page - 1) * page_size
        page_items = enriched[start:start + page_size]

        return {'users': page_items, 'total': total, 'page': page, 'page_size': page_size}

    # ─── GET USER DETAIL ──────────────────────────────────────────────────────

    def get_user_detail(self, user_id: str) -> Optional[dict]:
        user_resp = self.users.get_item(Key={'user_id': user_id})
        user = user_resp.get('Item')
        if not user:
            return None

        sub = self.get_subscription_by_user(user_id)
        usage_resp = self.usage.get_item(Key={'user_id': user_id}).get('Item', {}) if self.usage else {}

        # Fetch jobs
        jobs_resp = self.jobs.query(
            IndexName='UserJobsIndex',
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False,
            Limit=50,
        )
        jobs = jobs_resp.get('Items', [])

        # Get application state for each job
        job_details = []
        for j in jobs:
            app_resp = self.applications.query(
                IndexName='JobApplicationsIndex',
                KeyConditionExpression=Key('job_id').eq(j['job_id']),
                Limit=1,
            )
            app = app_resp['Items'][0] if app_resp['Items'] else None
            job_details.append({
                'job_id': j['job_id'],
                'title': j.get('title', ''),
                'company_name': j.get('company_name', ''),
                'status': j.get('status', ''),
                'created_at': j.get('created_at', ''),
                'application_state': app.get('status') if app else None,
            })

        cv_count = int(user.get('cv_count', 0))

        return {
            'user_id': user_id,
            'email': user.get('email', ''),
            'name': user.get('name', ''),
            'created_at': user.get('created_at', ''),
            'subscription_status': sub.get('status') if sub else None,
            'applications_used': int(usage_resp.get('used', 0)),
            'applications_remaining': int(usage_resp.get('remaining', 0)),
            'trial_active': sub.get('status') == 'trialing' if sub else False,
            'last_active_at': user.get('last_active_at'),
            'cv_count': cv_count,
            'subscription': {
                'subscription_id': sub.get('subscription_id') if sub else None,
                'customer_id': sub.get('customer_id') if sub else None,
                'status': sub.get('status') if sub else None,
                'plan': sub.get('plan') if sub else None,
                'current_period_end': sub.get('current_period_end') if sub else None,
            },
            'jobs': job_details,
        }

    # ─── METRICS ──────────────────────────────────────────────────────────────

    def get_platform_metrics(self) -> dict:
        """
        Computes platform KPIs. For MVP: Scan-based.
        For scale: use pre-computed metrics table updated by EventBridge.
        """
        all_users = self._scan_all(self.users)
        all_subs = self._scan_all(self.subscriptions)

        total_users = len(all_users)
        status_counts = {}
        mrr = 0
        for sub in all_subs:
            s = sub.get('status', 'unknown')
            status_counts[s] = status_counts.get(s, 0) + 1
            if s == 'active':
                plan = sub.get('plan', 'monthly')
                mrr += 1900 if plan == 'monthly' else round(14900 / 12)

        trialing = status_counts.get('trialing', 0)
        active = status_counts.get('active', 0)
        past_due = status_counts.get('past_due', 0)
        canceled = status_counts.get('canceled', 0)

        # Conversion rate = active / (active + canceled) — excludes current trials
        converted_base = active + canceled
        trial_to_paid_rate = round(active / converted_base, 3) if converted_base > 0 else 0.0

        # Applications created today / this week
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_start = (now - timedelta(days=7)).isoformat()

        all_jobs = self._scan_all(self.jobs)
        apps_today = sum(1 for j in all_jobs if j.get('created_at', '') >= today_start)
        apps_week = sum(1 for j in all_jobs if j.get('created_at', '') >= week_start)

        new_today = sum(1 for u in all_users if u.get('created_at', '') >= today_start)
        new_week = sum(1 for u in all_users if u.get('created_at', '') >= week_start)

        return {
            'total_users': total_users,
            'active_subscriptions': active,
            'trialing_users': trialing,
            'past_due_users': past_due,
            'churned_users': canceled,
            'trial_to_paid_rate': trial_to_paid_rate,
            'mrr': mrr,
            'applications_created_today': apps_today,
            'applications_created_this_week': apps_week,
            'new_users_today': new_today,
            'new_users_this_week': new_week,
        }

    # ─── TRIAL EXTENSION ──────────────────────────────────────────────────────

    def extend_user_trial(self, user_id: str, extend_days: int):
        sub = self.get_subscription_by_user(user_id)
        if sub is None:
            return None
        if sub.get('status') != 'trialing':
            return 'not_trialing'

        from datetime import datetime, timezone, timedelta
        current_end = datetime.fromisoformat(sub['trial_end'].replace('Z', '+00:00'))
        new_end = current_end + timedelta(days=extend_days)
        new_end_iso = new_end.isoformat()

        self.subscriptions.update_item(
            Key={'subscription_id': sub['subscription_id']},
            UpdateExpression='SET trial_end = :te, updated_at = :ua',
            ExpressionAttributeValues={
                ':te': new_end_iso,
                ':ua': datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            'user_id': user_id,
            'new_trial_end': new_end_iso,
            'extended_by_days': extend_days,
        }

    # ─── SUBSCRIPTION HELPERS ─────────────────────────────────────────────────

    def get_subscription_by_user(self, user_id: str) -> Optional[dict]:
        resp = self.subscriptions.query(
            IndexName='UserSubscriptionIndex',
            KeyConditionExpression=Key('user_id').eq(user_id),
            Limit=1,
            ScanIndexForward=False,
        )
        items = resp.get('Items', [])
        return items[0] if items else None

    def update_subscription_status(self, subscription_id: str, status: str):
        from datetime import datetime, timezone
        self.subscriptions.update_item(
            Key={'subscription_id': subscription_id},
            UpdateExpression='SET #s = :s, updated_at = :ua',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': status,
                ':ua': datetime.now(timezone.utc).isoformat(),
            }
        )

    def list_subscriptions(self, status: Optional[str], page: int, page_size: int) -> dict:
        if status:
            # Use StatusIndex GSI
            resp = self.subscriptions.query(
                IndexName='StatusIndex',
                KeyConditionExpression=Key('status').eq(status),
            )
            items = resp.get('Items', [])
        else:
            items = self._scan_all(self.subscriptions)

        # Join user email
        user_ids = [s.get('user_id') for s in items if s.get('user_id')]
        user_emails = self._batch_get_user_emails(user_ids)

        enriched = []
        for s in items:
            uid = s.get('user_id', '')
            enriched.append({
                'subscription_id': s.get('subscription_id'),
                'customer_id': s.get('customer_id'),
                'user_id': uid,
                'user_email': user_emails.get(uid, ''),
                'status': s.get('status'),
                'plan': s.get('plan'),
                'current_period_end': s.get('current_period_end'),
                'created_at': s.get('created_at'),
            })

        enriched.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        total = len(enriched)
        start = (page - 1) * page_size
        return {'subscriptions': enriched[start:start + page_size], 'total': total, 'page': page, 'page_size': page_size}

    # ─── UTILITIES ────────────────────────────────────────────────────────────

    def _scan_all(self, table, **kwargs) -> list:
        """Paginated scan — returns all items."""
        items = []
        resp = table.scan(**kwargs)
        items.extend(resp.get('Items', []))
        while 'LastEvaluatedKey' in resp:
            resp = table.scan(ExclusiveStartKey=resp['LastEvaluatedKey'], **kwargs)
            items.extend(resp.get('Items', []))
        return items

    def _batch_get_subscriptions(self, user_ids: list) -> dict:
        """Returns { user_id: subscription_item } for a list of user IDs."""
        result = {}
        for uid in user_ids:
            sub = self.get_subscription_by_user(uid)
            if sub:
                result[uid] = sub
        return result

    def _batch_get_usage(self, user_ids: list) -> dict:
        if not self.usage:
            return {}
        result = {}
        for uid in user_ids:
            resp = self.usage.get_item(Key={'user_id': uid})
            item = resp.get('Item')
            if item:
                result[uid] = item
        return result

    def _batch_get_user_emails(self, user_ids: list) -> dict:
        result = {}
        for uid in user_ids:
            resp = self.users.get_item(Key={'user_id': uid})
            item = resp.get('Item')
            if item:
                result[uid] = item.get('email', '')
        return result
```

---

## 7. Error Handling

All admin handlers use the shared `build_error_response` helper:

```python
# shared/response_utils.py
import json

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',   # tighten to admin domain in prod
}

def build_response(status_code: int, body: dict) -> dict:
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, default=str),
    }

def build_error_response(status_code: int, message: str) -> dict:
    return build_response(status_code, {'error': message})
```

### Standard Error Codes

| Code | When |
|---|---|
| 400 | Invalid input (bad param type, missing required field) |
| 401 | JWT missing or expired |
| 403 | Valid JWT but not in Admins group |
| 404 | Resource (user, subscription) not found |
| 409 | Conflict (already canceled, not trialing) |
| 502 | Stripe API call failed |
| 500 | Unexpected exception |

---

## 8. CDK Infrastructure

### New Lambda Function

```python
# infra/careervp/api_construct.py

admin_handler = aws_lambda.Function(
    self, 'AdminHandler',
    function_name=f'careervp-admin-{stage}',
    runtime=aws_lambda.Runtime.PYTHON_3_12,
    code=aws_lambda.Code.from_asset('src/handlers'),
    handler='admin_handler.lambda_handler',
    timeout=Duration.seconds(30),
    memory_size=256,
    environment={
        'USERS_TABLE_NAME': users_table.table_name,
        'SUBSCRIPTIONS_TABLE_NAME': subscriptions_table.table_name,
        'JOBS_TABLE_NAME': jobs_table.table_name,
        'APPLICATIONS_TABLE_NAME': applications_table.table_name,
        'USAGE_TABLE_NAME': usage_table.table_name,
        'STRIPE_SECRET_KEY': stripe_secret_key_param.string_value,
        'ALLOWED_ORIGINS': 'https://app.careervp.com',
    }
)

# Grant DynamoDB read access
for table in [users_table, subscriptions_table, jobs_table, applications_table, usage_table]:
    table.grant_read_data(admin_handler)

# Grant write access for trial extension + subscription cancel
subscriptions_table.grant_write_data(admin_handler)

# API Gateway routes — all under /admin
api.add_resource('admin').add_proxy(
    default_integration=aws_apigateway.LambdaIntegration(admin_handler),
    any_method=True,
)
```

### GSI Additions to Existing Tables

```python
# Add to users_table definition:
users_table.add_global_secondary_index(
    index_name='AllUsersIndex',
    partition_key=aws_dynamodb.Attribute(name='entity_type', type=aws_dynamodb.AttributeType.STRING),
    sort_key=aws_dynamodb.Attribute(name='created_at', type=aws_dynamodb.AttributeType.STRING),
    projection_type=aws_dynamodb.ProjectionType.ALL,
)

# Add to subscriptions_table definition:
subscriptions_table.add_global_secondary_index(
    index_name='StatusIndex',
    partition_key=aws_dynamodb.Attribute(name='status', type=aws_dynamodb.AttributeType.STRING),
    sort_key=aws_dynamodb.Attribute(name='user_id', type=aws_dynamodb.AttributeType.STRING),
    projection_type=aws_dynamodb.ProjectionType.ALL,
)
```
