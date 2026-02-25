# CareerVP Trial & Usage Enforcement

**Version:** 1.0 (Beta)
**Last Updated:** 2026-02-25

---

## Overview

This document describes how the CareerVP trial period and usage limits are implemented and enforced.

---

## Trial Period

### 1.1 Trial Configuration

| Parameter | Value |
|-----------|-------|
| Duration | 14 days |
| Applications | 3 free |
| Features | Full access |
| Credit Card | Required |

### 1.2 Trial Start

**When does trial start?**

The trial starts when a user:
1. Completes registration, OR
2. Creates their first job application

**Trigger:**
```python
# Trial starts on first application creation
if user.trial_start_date is None:
    user.trial_start_date = datetime.utcnow()
    user.applications_used = 0
```

### 1.3 Trial End

**When does trial end?**

The trial ends when:
1. 14 days have passed since start, OR
2. All 3 applications have been used

**Whichever comes first.**

### 1.4 Trial Expiration Check

```python
def is_trial_expired(user) -> bool:
    if user.trial_start_date is None:
        return False  # Trial hasn't started

    days_elapsed = (datetime.utcnow() - user.trial_start_date).days
    return days_elapsed >= 14 or user.applications_used >= 3
```

---

## Usage Tracking

### 2.1 Application Count

An "application" is created when a user generates any of:
- VPR (Visual Past Resume)
- Gap Analysis
- CV Tailoring
- Cover Letter
- Interview Prep

**Each generation counts as 1 application.**

```python
# Application is created when user initiates generation
class Application:
    user_id: str
    job_id: str
    created_at: datetime
    generations: list[GenerationType]

    def increment_usage(self, gen_type: GenerationType):
        self.generations.append(gen_type)
        user.applications_used += 1
```

### 2.2 Counting Logic

```python
def can_create_application(user) -> tuple[bool, str]:
    # Check if trial started
    if user.trial_start_date is None:
        # First application starts the trial
        return True, "Trial will start"

    # Check if expired
    if is_trial_expired(user):
        return False, "Trial expired"

    # Check if limit reached
    if user.applications_used >= 3:
        return False, "Application limit reached"

    return True, "OK"
```

### 2.3 What Counts as Usage?

| Action | Counts as Application? |
|--------|----------------------|
| Register account | No |
| Upload CV | No |
| Create job (no generation) | No |
| Generate VPR | Yes |
| Generate Gap Analysis | Yes |
| Generate Tailored CV | Yes |
| Generate Cover Letter | Yes |
| Generate Interview Prep | Yes |

---

## Enforcement

### 3.1 API Response When Trial Active

```json
{
  "trial": {
    "days_remaining": 12,
    "applications_used": 1,
    "applications_remaining": 2,
    "status": "active"
  }
}
```

### 3.2 API Response When Trial Expiring Soon (< 3 days)

```json
{
  "trial": {
    "days_remaining": 2,
    "applications_used": 2,
    "applications_remaining": 1,
    "status": "expiring_soon",
    "message": "Your trial expires in 2 days"
  }
}
```

### 3.3 API Response When Trial Expired

```json
{
  "error": "Trial period has expired",
  "code": "TRIAL_EXPIRED",
  "trial": {
    "days_remaining": 0,
    "applications_used": 3,
    "applications_remaining": 0,
    "status": "expired",
    "upgrade_url": "/billing/upgrade"
  }
}
```

### 3.4 When Limit Reached

```json
{
  "error": "Application limit reached",
  "code": "APPLICATION_LIMIT_REACHED",
  "trial": {
    "days_remaining": 10,
    "applications_used": 3,
    "applications_remaining": 0,
    "status": "limit_reached",
    "upgrade_url": "/billing/upgrade"
  }
}
```

---

## Middleware Enforcement

### 4.1 Trial Check Middleware

```python
def check_trial_status(handler):
    def wrapper(event, context):
        user_id = extract_user_id(event)
        user = get_user(user_id)

        # Allow auth endpoints
        if is_auth_endpoint(event):
            return handler(event, context)

        # Check trial
        if is_trial_expired(user):
            return {
                "statusCode": 403,
                "body": json.dumps({
                    "error": "Trial expired",
                    "code": "TRIAL_EXPIRED"
                })
            }

        # Check application limit before generation
        if is_generation_endpoint(event):
            if user.applications_used >= 3:
                return {
                    "statusCode": 403,
                    "body": json.dumps({
                        "error": "Application limit reached",
                        "code": "APPLICATION_LIMIT_REACHED"
                    })
                }

        return handler(event, context)

    return wrapper
```

### 4.2 Endpoints Protected by Trial

| Endpoint | Trial Required |
|----------|---------------|
| POST /cvs/upload | No |
| POST /jobs | No |
| POST /gap-analysis/generate | Yes |
| POST /vpr/generate | Yes |
| POST /cv-tailoring/generate | Yes |
| POST /cover-letter/generate | Yes |
| POST /interview-prep/generate | Yes |

---

## Upgrade Path

### 5.1 Subscription Plans

| Plan | Price | Applications |
|------|-------|--------------|
| Monthly | $20/month | Unlimited |
| Annual | $192/year ($16/month) | Unlimited |

### 5.2 Upgrade Endpoint

```
GET /billing/subscription
POST /billing/subscribe
```

**Request:**
```json
{
  "plan": "monthly" | "annual",
  "payment_token": "tok_xxx"
}
```

**Response:**
```json
{
  "subscription": {
    "id": "sub_123",
    "plan": "monthly",
    "status": "active",
    "started_at": "2026-02-25T12:00:00Z"
  }
}
```

### 5.3 Post-Upgrade

After upgrading:
- Trial status becomes "upgraded"
- Unlimited applications available
- Trial info retained for display

---

## User Dashboard Display

### 6.1 Trial Status Widget

On the dashboard, users see:

```
┌─────────────────────────────────┐
│  Your Trial                     │
│  ┌───────────────────────────┐  │
│  │ Days Remaining: 12        │  │
│  │ ████████░░░░░░░░ 80%     │  │
│  │                           │  │
│  │ Applications: 1/3        │  │
│  │ ████████████░░░░░ 33%    │  │
│  └───────────────────────────┘  │
│                                 │
│  [Upgrade Now]                  │
└─────────────────────────────────┘
```

### 6.2 Upgrade Prompt

When trial is expiring (within 3 days):

```
⚠️ Your trial expires in 3 days!
Don't lose access - upgrade now for unlimited applications.
[Upgrade Now] [Remind Me Later]
```

---

## Admin/Monitoring

### 7.1 Metrics to Track

| Metric | Description |
|--------|-------------|
| trial_start_count | Number of trials started |
| trial_conversion_rate | % converting to paid |
| trial_expiry_count | Trials expiring |
| avg_applications_per_trial | Applications per trial |
| days_to_conversion | Days from start to paid |

### 7.2 CloudWatch Metrics

```python
# Emit trial-related metrics
metrics.add_metric(name="TrialStarted", unit="Count", value=1)
metrics.add_metric(name="TrialExpired", unit="Count", value=1)
metrics.add_metric(name="TrialConverted", unit="Count", value=1)
metrics.add_metric(name="ApplicationsCreated", unit="Count", value=1)
```

---

## Testing

### 8.1 Test Scenarios

| Scenario | Expected Result |
|----------|----------------|
| New user creates first app | Trial starts, count = 1 |
| User at 2/3 apps creates app | Trial continues, count = 3 |
| User at 3/3 apps creates app | 403 error |
| User on day 13 creates app | Trial continues |
| User on day 15 creates app | 403 error |

### 8.2 Test Commands

```bash
# Test trial start
curl -X POST /jobs -H "Authorization: Bearer $TOKEN" \
  -d '{"company": "Test", "title": "Dev"}'

# Test application limit
curl -X POST /vpr/generate -H "Authorization: Bearer $TOKEN" \
  -d '{"job_id": "job-123"}'
# Repeat 3 times, expect 403 on 4th
```

---

## Troubleshooting

### Issue: User says they have applications but system says limit reached

**Possible causes:**
1. Application was created but failed to count
2. Cache inconsistency

**Resolution:**
1. Check DynamoDB user record
2. Verify applications_used value
3. Clear cache if necessary

### Issue: Trial shows as expired but 14 days not passed

**Possible causes:**
1. Application limit reached first
2. Timezone issue

**Resolution:**
1. Check both conditions - limit OR time can trigger expiry

---

## Future Enhancements

### Planned Features

1. **Extend Trial**: Allow extending trial for specific users
2. **Trial Pause**: Pause trial during maintenance
3. **Freemium Tier**: Limited free tier post-trial
4. **Application Rollover**: Unused apps roll to next month
