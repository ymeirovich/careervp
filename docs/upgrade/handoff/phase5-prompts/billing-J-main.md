# Phase 5 — Batch J: Billing Main Page
# Components: BillingContent (modify), SubscriptionCard (new),
#             UsageCard (new), BillingInfoCard (new)
# Model: Opus | New conversation per batch
# Route: /billing

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write FOUR complete upgrade specs — BillingContent (page shell, modify), SubscriptionCard (new), UsageCard (new), BillingInfoCard (new).

THINK before writing each spec:
1. BillingContent: What is the new page structure? (3 stacked cards + Plans section below, all on same /billing route). What states does the page itself own?
2. SubscriptionCard: What backend fields drive it? What states exist (active, cancelling, trial, past-due)?
3. UsageCard: What does 'unlimited credits' vs trial look like? Where does the upgrade link scroll to?
4. BillingInfoCard: What is the empty state (no payment method)? last4/brand come from GET /users/me/subscription after a backend change — see backend prerequisite note below.
5. What is BLOCKED? Nothing functional — but BillingInfoCard has a backend prerequisite (webhook handler must store card details before these fields exist in the subscription response).

THEN produce ALL FOUR specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "{modify/new} {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Billing page.png, Billing page continued.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** app/billing/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /users/me/subscription (+ new last4/brand fields after backend change), GET /users/me/usage
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert to prior billing page component — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for each subscription state, loading/error/empty states, ARIA, Hebrew i18n.

## States to Handle
{component-specific — see data below}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on existing billing API calls (GET /users/me/subscription, POST /billing/portal)
- Existing Stripe webhook handling unaffected
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx on GET /users/me/subscription or POST /billing/portal | Block deploy, investigate |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output all four specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: BillingContent (page shell)
File: app/billing/page.tsx
Tier: feature
Change type: modify (restructure page layout — 3 stacked cards + Plans section)
Today's date: 2026-05-23

**Contract verification entry (/billing):**
```json
{
  "route": "/billing",
  "component": "BillingContent",
  "change_type": "modify",
  "backend_classification": "yes",
  "resolution": "plan_type, status, current_period_end, next_charge_amount from GET /users/me/subscription; credits_used and credits_total from GET /users/me/usage; payment method last4 and brand from the payment_method object in GET /users/me/subscription response (standard Stripe subscription payload includes attached payment method details); Manage Billing CTA calls existing POST /billing/portal",
  "in_scope": true
}
```

**Payment method resolution (confirmed 2026-05-23):**
GET /users/me/subscription does NOT currently return last4/brand — handle_get_subscription
only returns subscription_id, customer_id, status, plan, current_period_end,
cancel_at_period_end, trial_end. No separate GET /billing/payment-method endpoint exists.

Correct approach (Option A — webhook-time storage): on checkout.session.completed and
customer.subscription.updated, extract payment_method.card.last4 + brand from the Stripe
event and persist to DynamoDB alongside the subscription record. GET /users/me/subscription
then returns these new fields.

**Backend prerequisite:** BillingInfoCard frontend spec can be written now but implementation
is blocked until the webhook handler + DynamoDB change ships.

**Diff analysis entry (billing):**
```json
{
  "component": "BillingContent",
  "file": "app/billing/page.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Main billing page now shows three stacked cards (Current Subscription, Usage, Billing Info) instead of current plan status + inline plan cards. Page title shortened to 'Billing'. Plan selection moved to a lower section on the same page.",
  "interaction_states_visible": ["active subscription with renewal info"],
  "interaction_states_needed_but_not_shown": ["trial active state", "trial expired state", "cancelled/expiring subscription state", "past-due invoice state", "loading state", "error state"]
}
```

**Diff analysis layout changes:**
```json
[
  {"description": "Page title changed from 'Billing & Plan' to 'Billing'"},
  {"description": "Plan cards moved to a lower Plans section on the same /billing page (gap-answer q14 resolves: not a separate route)", "change_type": "structure"},
  {"description": "Pricing structure changed to: Monthly $30/mo, 3-Month $25/mo ($75 billed), 6-Month $20/mo ($120 billed) — per gap-answer q13"}
]
```

**Gap answers — billing (page-level):**
```json
[
  {
    "question_id": "q14",
    "component": "PlansSection",
    "topic": "routing",
    "answer": "Plans are rendered as a lower section of the same /billing page — no separate route needed"
  },
  {
    "question_id": "q13",
    "component": "PlansSection",
    "topic": "pricing",
    "answer": "Use the three-tier pricing shown in the design screenshots: $30/mo (1 month), $25/mo (3 month), $20/mo (6 month)"
  },
  {
    "question_id": "q18",
    "component": "BillingPage",
    "topic": "trial_state",
    "answer": "Both cards are shown for trial users — Usage card displays trial credits; Billing Info card renders in empty state ('No payment method' + 'Add Payment Method' CTA)"
  }
]
```

---

### Component 2: SubscriptionCard (new)
File: components/billing/SubscriptionCard.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23

**Diff analysis (billing new_components_needed):**
```
"SubscriptionCard — displays current subscription status (Active badge, plan-type pill,
renewal date, next charge amount, View Plans CTA)"
```

**Diff analysis layout change:**
```json
{
  "description": "Current plan section restructured: now a 'Current Subscription' card with green 'Active' badge, plan-type pill ('Pro Monthly'), renewal date, next charge amount, and an orange 'View Plans' CTA button on the right side"
}
```

**Backend fields:**
- plan_type: GET /users/me/subscription
- status: GET /users/me/subscription
- current_period_end: GET /users/me/subscription
- next_charge_amount: GET /users/me/subscription (field: subscription.next_charge_amount per gap-answer q12)

**Gap answers — billing:**
```json
[
  {"question_id": "q1", "component": "SubscriptionCard", "topic": "loading_state", "answer": "Skeleton placeholder matching card shape with shimmer"},
  {"question_id": "q2", "component": "SubscriptionCard", "topic": "error_state", "answer": "Inline error message with Retry button inside the card"},
  {
    "question_id": "q10",
    "component": "SubscriptionCard",
    "topic": "edge_case",
    "answer": "Cancelled subscription still active until period end: show 'Cancelling' badge (yellow/warning) with 'Active until [date]' text and a 'Resubscribe' CTA"
  },
  {
    "question_id": "q12",
    "component": "SubscriptionCard",
    "topic": "edge_case",
    "answer": "next_charge_amount fetched from API (subscription.next_charge_amount) — most accurate for prorations/discounts"
  }
]
```

**States to handle:** active | cancelling | trial | expired | past-due | loading | error

---

### Component 3: UsageCard (new)
File: components/billing/UsageCard.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23

**Diff analysis (billing new_components_needed):**
```
"UsageCard — shows credits remaining/unlimited with upgrade link"
```

**Diff analysis layout change:**
```json
{
  "description": "New 'Usage' card section added below subscription card showing 'Unlimited credits' and a blue 'Upgrade subscription to save money' link"
}
```

**Backend fields:**
- Credits: GET /users/me/usage → credits_used / credits_total
- Trial credits display: per gap-answer q4 — "X of 3 applications used" with progress indicator

**Gap answers — billing:**
```json
[
  {
    "question_id": "q4",
    "component": "UsageCard",
    "topic": "edge_case",
    "answer": "Trial users: 'X of 3 applications used' with a progress indicator"
  },
  {
    "question_id": "q17",
    "component": "UsageCard",
    "topic": "navigation",
    "answer": "Upgrade link smooth-scrolls to the Plans section of the same /billing page (anchor scroll, no route change)"
  }
]
```

**States to handle:** unlimited (paid) | trial | loading | error

---

### Component 4: BillingInfoCard (new)
File: components/billing/BillingInfoCard.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23

**Diff analysis (billing new_components_needed):**
```
"BillingInfoCard — shows payment method (masked card number, brand) with Manage Billing CTA"
```

**Diff analysis layout change:**
```json
{
  "description": "New 'Billing Info' card section added below Usage showing 'Payment method .... XXXX (Visa)', 'Billing handled securely via Stripe.' text, and an orange 'Manage Billing' button on the right"
}
```

**Backend fields:**

- last4 + brand: GET /users/me/subscription (new fields added via webhook-time storage —
  see payment method resolution note above under BillingContent)
- Backend prerequisite must ship before this component can be implemented

**Gap answers — billing:**
```json
[
  {
    "question_id": "q3",
    "component": "BillingInfoCard",
    "topic": "empty_state",
    "answer": "Card visible with 'No payment method' text and an 'Add Payment Method' CTA button (shown for trial users)"
  },
  {
    "question_id": "q9",
    "component": "BillingInfoCard",
    "topic": "accessibility",
    "answer": "Yes — aria-label 'Payment method ending in 6363, Visa' on the masked card number element"
  },
  {
    "question_id": "q15",
    "component": "BillingInfoCard",
    "topic": "api_contract",
    "answer": "A separate existing endpoint GET /billing/payment-method returns payment method details (last4, brand) — NOT from the subscription response"
  },
  {
    "question_id": "q16",
    "component": "BillingInfoCard",
    "topic": "navigation",
    "answer": "Manage Billing opens Stripe portal in a new tab via window.open (POST /billing/portal) — keeps app open in current tab"
  }
]
```

**States to handle:** has-payment-method | no-payment-method (empty) | loading | error

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the four spec markdowns, back-to-back.
