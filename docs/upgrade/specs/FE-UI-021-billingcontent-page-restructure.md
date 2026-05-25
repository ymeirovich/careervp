---
spec_id: FE-UI-021
title: "modify BillingContent — restructure page to 3 stacked cards + Plans section"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing
component_file: src/frontend/app/billing/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** BillingContent renders a monolithic page with inline "Your Current Plan" card, two plan cards in a 2-column grid (Monthly $20, Annual $16), and a support link. No separate usage or billing-info sections exist.
**Required behavior:** Page restructured into three stacked card sections (SubscriptionCard, UsageCard, BillingInfoCard) followed by a Plans section with three pricing tiers ($30/mo, $25/mo 3-month, $20/mo 6-month). Page title shortened from "Billing & Plan" to "Billing". Plans section anchored for smooth-scroll navigation from UsageCard upgrade link.
**User impact:** Clearer billing overview with separated concerns; users can see subscription status, usage, and payment method at a glance before reviewing plan options.

## Evidence
**Mockup files:** Billing page.png, Billing page continued.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/billing/page.tsx
**Page file(s):** app/billing/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /users/me/subscription, GET /users/me/usage, POST /billing/portal
**Imports this component:** ErrorBoundary, useUserContext, Spinner, SubscriptionCard (new), UsageCard (new), BillingInfoCard (new)

## Fix Plan
**Files to modify:**
- src/frontend/app/billing/page.tsx (restructure layout, update title, replace inline plan cards with PlansSection and import new child components)

**Behavior changes:**
- Page title: "Billing & Plan" → "Billing"
- Remove inline current-plan card; replace with `<SubscriptionCard />`
- Add `<UsageCard />` below subscription card
- Add `<BillingInfoCard />` below usage card
- Replace existing 2-column plan grid with a 3-tier Plans section (id="plans" for anchor scroll)
- Plans section pricing: Monthly $30/mo, 3-Month $25/mo ($75 billed), 6-Month $20/mo ($120 billed)
- Preserve existing ErrorBoundary wrapper and loading state
- Preserve existing useUserContext data fetching

**Non-goals (explicitly out of scope):**
- No new API endpoints (uses existing GET /users/me/subscription, GET /users/me/usage)
- No changes to billing/checkout route
- No Stripe portal logic changes (POST /billing/portal unchanged)
- Plans section plan-card styling is not specified here (inherits existing card pattern)

**Rollback plan:** Revert to prior billing page component — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given the billing page loads, when rendered, then page title displays "Billing" (not "Billing & Plan")
- [ ] AC-002: Given the billing page loads, when rendered, then three card components are stacked vertically: SubscriptionCard, UsageCard, BillingInfoCard (in that order)
- [ ] AC-003: Given the billing page loads, when rendered, then a Plans section with id="plans" appears below the three cards
- [ ] AC-004: Given the Plans section renders, when displayed, then three pricing tiers show: Monthly $30/mo, 3-Month $25/mo ($75 billed quarterly), 6-Month $20/mo ($120 billed semi-annually)
- [ ] AC-005: Given the page is loading, when isLoading is true, then a full-page Spinner with aria-label "Loading billing info…" is displayed
- [ ] AC-006: Given an error occurs fetching data, when the ErrorBoundary catches, then the ErrorBoundary fallback UI renders with cloudwatchKey "billing-page"
- [ ] AC-007: Given Hebrew locale is active, when page renders, then page title, Plans section heading, and plan descriptions render in Hebrew with RTL layout
- [ ] AC-008: Given the page renders, when inspected for accessibility, then the page has a landmark heading structure (h1 for page title, h2 for Plans section)

## States to Handle
| State | Condition | Behavior |
|-------|-----------|----------|
| loading | isLoading=true | Full-page Spinner |
| loaded | Data available | Render all three cards + Plans section |
| error | ErrorBoundary triggered | Fallback error UI |

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

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on existing billing API calls (GET /users/me/subscription, POST /billing/portal)
- Existing Stripe webhook handling unaffected
- Existing test suite passes without modification
- ErrorBoundary behavior unchanged

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/app/billing/page.tsx:TBD | tests/ui/unit/BillingContent.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx on GET /users/me/subscription or POST /billing/portal | Block deploy, investigate |

## Design Notes
- Plans section pricing ($30/$25/$20) differs from current ($20/$16) — this is intentional per gap-answer q13
- Plans section renders on the same /billing route (no separate route) per gap-answer q14
- The "Save 20%" badge on the annual plan is removed; new best-value indicator TBD from design (not shown in mockup detail)
