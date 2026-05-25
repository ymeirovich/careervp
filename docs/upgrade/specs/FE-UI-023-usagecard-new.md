---
spec_id: FE-UI-023
title: "new UsageCard — credits usage display with upgrade link"
priority: medium
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing
component_file: src/frontend/components/billing/UsageCard.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No usage card exists on the billing page. Credit/usage information is not surfaced in the billing context.
**Required behavior:** Dedicated UsageCard component displaying either "Unlimited credits" for paid subscribers or "X of 3 applications used" with a progress indicator for trial users. Includes a blue "Upgrade subscription to save money" link that smooth-scrolls to the Plans section.
**User impact:** Users understand their usage allowance at a glance; trial users see clear progress toward their limit with an upgrade path.

## Evidence
**Mockup files:** Billing page.png, Billing page continued.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/billing/UsageCard.tsx
**Page file(s):** app/billing/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /users/me/usage (fields: credits_used, credits_total, trial.active, trial.applications_used, trial.applications_limit)
**Imports this component:** BillingContent (app/billing/page.tsx)

## Fix Plan
**Files to modify:**
- src/frontend/components/billing/UsageCard.tsx (new file)

**Behavior changes:**
- Card heading: "Usage"
- Paid state: displays "Unlimited credits" text
- Trial state: displays "X of 3 applications used" with a progress indicator (bar or fraction)
- Upgrade link: blue text link "Upgrade subscription to save money" that smooth-scrolls to #plans anchor on the same page
- Loading state: skeleton placeholder matching card shape with shimmer
- Error state: inline error message with "Retry" button

**Non-goals (explicitly out of scope):**
- No historical usage charts or graphs
- No per-feature usage breakdown
- No usage alerts or notifications

**Rollback plan:** Revert to prior billing page component — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given user has an active paid subscription, when card renders, then text "Unlimited credits" is displayed
- [ ] AC-002: Given user is on trial, when card renders, then text "X of 3 applications used" is displayed where X is the current count from usage API
- [ ] AC-003: Given user is on trial, when card renders, then a progress indicator visualizes applications_used / applications_limit ratio
- [ ] AC-004: Given card renders for a paid user, when "Upgrade subscription to save money" link is clicked, then page smooth-scrolls to the #plans section
- [ ] AC-005: Given card renders for a trial user, when upgrade link is clicked, then page smooth-scrolls to the #plans section
- [ ] AC-006: Given usage data is loading, when card renders, then a skeleton placeholder with shimmer animation is displayed
- [ ] AC-007: Given usage fetch fails, when card renders, then an inline error message with "Retry" button is displayed
- [ ] AC-008: Given "Retry" button is clicked, when error state is active, then usage data is re-fetched
- [ ] AC-009: Given Hebrew locale is active, when card renders, then all text renders in Hebrew with RTL layout and progress indicator direction is correct
- [ ] AC-010: Given card renders, when inspected for accessibility, then progress indicator has aria-valuenow, aria-valuemin, aria-valuemax attributes (trial state) or aria-label "Unlimited credits" (paid state)

## States to Handle
| State | Condition | Display | Link |
|-------|-----------|---------|------|
| unlimited (paid) | has_active_subscription=true | "Unlimited credits" | "Upgrade subscription to save money" → #plans |
| trial | trial.active=true | "X of 3 applications used" + progress bar | "Upgrade subscription to save money" → #plans |
| loading | Data fetching | Skeleton shimmer | — |
| error | Fetch failed | Inline error + Retry | — |

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

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on existing billing API calls (GET /users/me/subscription, POST /billing/portal)
- Existing Stripe webhook handling unaffected
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/billing/UsageCard.tsx:TBD | tests/ui/unit/UsageCard.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx on GET /users/me/usage | Block deploy, investigate |

## Design Notes
- Trial limit is 3 applications (hardcoded in V1 per project CLAUDE.md)
- Upgrade link text "Upgrade subscription to save money" shown for both paid and trial users per mockup; for paid users this enables plan-tier upgrades (monthly → 6-month)
- Smooth-scroll target is id="plans" on the same /billing page per gap-answer q17
