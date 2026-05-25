---
spec_id: FE-UI-022
title: "new SubscriptionCard — current subscription status card with state badges"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing
component_file: src/frontend/components/billing/SubscriptionCard.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No standalone subscription card exists. Subscription info is rendered inline within BillingContent as part of the "Your Current Plan" section with limited state handling (only active, trial, expired).
**Required behavior:** Dedicated SubscriptionCard component displaying: status badge (Active/green, Cancelling/yellow, Trial/blue, Past Due/red), plan-type pill (e.g. "Pro Monthly"), renewal date, next charge amount, and a "View Plans" CTA. Handles all subscription lifecycle states.
**User impact:** Users see their subscription status clearly with contextual CTAs and accurate renewal/charge information.

## Evidence
**Mockup files:** Billing page.png, Billing page continued.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/billing/SubscriptionCard.tsx
**Page file(s):** app/billing/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /users/me/subscription (fields: plan_type, status, current_period_end, next_charge_amount, cancel_at_period_end)
**Imports this component:** BillingContent (app/billing/page.tsx)

## Fix Plan
**Files to modify:**
- src/frontend/components/billing/SubscriptionCard.tsx (new file)

**Behavior changes:**
- Card heading: "Current Subscription"
- Status badge: color-coded by state (green=active, yellow=cancelling, blue=trial, red=past-due)
- Plan-type pill: displays plan_type value (e.g. "Pro Monthly", "Pro 3-Month", "Pro 6-Month")
- Renewal date: formatted from current_period_end
- Next charge amount: displayed from subscription.next_charge_amount
- CTA button (orange): "View Plans" scrolls to #plans anchor; "Resubscribe" shown in cancelling state
- Loading state: skeleton placeholder matching card shape with shimmer animation
- Error state: inline error message with "Retry" button inside the card

**Non-goals (explicitly out of scope):**
- No direct Stripe API calls from this component
- No subscription modification actions (handled via Stripe portal)
- No plan-change logic

**Rollback plan:** Revert to prior billing page component — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given subscription status is "active", when card renders, then a green badge with text "Active" is displayed
- [ ] AC-002: Given subscription has cancel_at_period_end=true, when card renders, then a yellow badge with text "Cancelling" is displayed and text reads "Active until [formatted date]"
- [ ] AC-003: Given subscription status is "trialing", when card renders, then a blue badge with text "Trial" is displayed with trial days remaining
- [ ] AC-004: Given subscription status is "past_due", when card renders, then a red badge with text "Past Due" is displayed with a payment update prompt
- [ ] AC-005: Given subscription is active, when card renders, then plan-type pill displays the plan_type value (e.g. "Pro Monthly")
- [ ] AC-006: Given subscription has current_period_end, when card renders, then renewal date is displayed in localized date format
- [ ] AC-007: Given subscription has next_charge_amount, when card renders, then next charge is displayed as formatted currency (e.g. "$30.00")
- [ ] AC-008: Given subscription is active, when "View Plans" CTA is clicked, then page smooth-scrolls to #plans section
- [ ] AC-009: Given subscription is cancelling, when card renders, then CTA text is "Resubscribe" instead of "View Plans"
- [ ] AC-010: Given subscription data is loading, when card renders, then a skeleton placeholder with shimmer animation is displayed matching card dimensions
- [ ] AC-011: Given subscription fetch fails, when card renders, then an inline error message with "Retry" button is displayed inside the card
- [ ] AC-012: Given "Retry" button is clicked, when error state is active, then subscription data is re-fetched
- [ ] AC-013: Given Hebrew locale is active, when card renders, then all text (badge, plan pill, dates, CTA) renders in Hebrew with RTL layout
- [ ] AC-014: Given card renders, when inspected for accessibility, then status badge has role="status" and aria-label describing the subscription state

## States to Handle
| State | Condition | Badge | CTA | Additional |
|-------|-----------|-------|-----|------------|
| active | status="active", cancel_at_period_end=false | Green "Active" | "View Plans" | Shows renewal date + next charge |
| cancelling | status="active", cancel_at_period_end=true | Yellow "Cancelling" | "Resubscribe" | Shows "Active until [date]" |
| trial | status="trialing" | Blue "Trial" | "View Plans" | Shows trial days remaining |
| past-due | status="past_due" | Red "Past Due" | "Update Payment" | Shows overdue notice |
| expired | status="canceled" or no subscription | — | "Choose a Plan" | Shows "No active subscription" |
| loading | Data fetching | — | — | Skeleton shimmer |
| error | Fetch failed | — | "Retry" | Inline error message |

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | unit | pre_merge | false |
| AC-003 | unit | pre_merge | false |
| AC-004 | unit | pre_merge | false |
| AC-005 | unit | pre_merge | false |
| AC-006 | unit | pre_merge | false |
| AC-007 | unit | pre_merge | false |
| AC-008 | unit | pre_merge | false |
| AC-009 | unit | pre_merge | false |
| AC-010 | unit | pre_merge | false |
| AC-011 | unit | pre_merge | false |
| AC-012 | unit | pre_merge | false |
| AC-013 | unit | pre_merge | false |
| AC-014 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on existing billing API calls (GET /users/me/subscription, POST /billing/portal)
- Existing Stripe webhook handling unaffected
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/billing/SubscriptionCard.tsx:TBD | tests/ui/unit/SubscriptionCard.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx on GET /users/me/subscription or POST /billing/portal | Block deploy, investigate |

## Design Notes
- next_charge_amount comes directly from subscription API response (not calculated client-side) per gap-answer q12 — handles prorations/discounts accurately
- Cancelling state per gap-answer q10: user retains access until period end, badge is yellow/warning
- "Resubscribe" CTA in cancelling state action TBD (may call POST /billing/portal or a dedicated resubscribe endpoint)
