---
spec_id: FE-UI-025
title: "new PlansSection — 3-tier pricing section with scroll anchor on /billing page"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing (section within page)
component_file: src/frontend/components/billing/PlansSection.tsx
tier: feature
---

## Problem Statement
**Current behavior:** The billing page renders two plan cards (Monthly $20, Annual $16) inline within BillingContent in a 2-column grid. No scroll anchor exists. No separate Plans section component.
**Required behavior:** A dedicated PlansSection component renders below SubscriptionCard, UsageCard, and BillingInfoCard. It contains a heading, three PlanCard instances in a horizontal row (Monthly $30/mo, 3-Month $25/mo, 6-Month $20/mo), and a centered "Questions? Contact us" support link. The section has id="plans" enabling smooth-scroll from UsageCard's upgrade link. On mobile (below md breakpoint), cards stack vertically with the recommended plan (3-Month) rendered first.
**User impact:** Users see all pricing options in a clear, scannable layout and can navigate directly to plans from the usage section.

## Evidence
**Mockup files:** subscription plans page.png, Subscription plan page 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/billing/PlansSection.tsx
**Page file(s):** app/billing/page.tsx (via BillingContent)
**Tier:** feature — cascade risk: low (contained within /billing)
**API dependencies:** GET /users/me/subscription (current plan identification), POST /billing/checkout (plan selection — delegated to PlanCard)
**Imports this component:** BillingContent (app/billing/page.tsx)

## Fix Plan
**Files to modify:**
- src/frontend/components/billing/PlansSection.tsx (new file)
- src/frontend/app/billing/page.tsx (add PlansSection import and render below BillingInfoCard)

**Behavior changes:**
- Section wrapper with id="plans" for anchor scrolling
- Section heading: "Choose Your Plan" (h2)
- Three PlanCard children rendered in a 3-column horizontal grid (md and above)
- Mobile layout (below md): single column, recommended plan (3-Month) rendered first via CSS order or conditional rendering
- Plan data is hardcoded within PlansSection (not fetched from API) — pricing is static per gap-answer q13
- currentPlanKey derived from subscription.plan_type via useUserContext to set isCurrentPlan on the matching PlanCard
- "Questions? Contact us" mailto link centered below the cards
- onChoosePlan callback per card triggers POST /billing/checkout with the selected planKey

**Non-goals (explicitly out of scope):**
- No dynamic pricing from API (hardcoded per business decision)
- No plan comparison feature list (cards show price and billing period only)
- No Stripe portal management (handled by BillingInfoCard)
- No loading/error states (plan data is static; subscription loading is handled by parent)

**Rollback plan:** Remove PlansSection from BillingContent — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given the billing page loads, when PlansSection renders, then a section element with id="plans" is present in the DOM
- [ ] AC-002: Given PlansSection renders, when displayed on md+ viewport, then three PlanCard components are laid out in a single horizontal row (3-column grid)
- [ ] AC-003: Given PlansSection renders, when displayed below md breakpoint, then PlanCard components stack vertically in a single column with the recommended plan (3-Month) appearing first
- [ ] AC-004: Given PlansSection renders, when the section heading is inspected, then it displays "Choose Your Plan" as an h2 element
- [ ] AC-005: Given PlansSection renders, when the three plans are displayed, then pricing matches: Monthly $30/mo (billed monthly), 3-Month $25/mo (billed $75 every 3 months), 6-Month $20/mo (billed $120 every 6 months)
- [ ] AC-006: Given the user's current subscription plan_type matches a plan's planKey, when PlansSection renders, then that PlanCard receives isCurrentPlan=true and all others receive isCurrentPlan=false
- [ ] AC-007: Given PlansSection renders, when the 3-Month PlanCard is inspected, then it receives isRecommended=true (hardcoded)
- [ ] AC-008: Given PlansSection renders, when the "Contact us" link is inspected, then it is a centered mailto:support@careervp.com anchor below the plan cards
- [ ] AC-009: Given UsageCard's "Upgrade subscription to save money" link is clicked, when the page scrolls, then the #plans section scrolls into view with smooth scroll behavior
- [ ] AC-010: Given Hebrew locale is active, when PlansSection renders, then heading, plan names, billing period labels, and "Questions? Contact us" text render in Hebrew with RTL layout
- [ ] AC-011: Given PlansSection renders, when inspected for accessibility, then the section has aria-labelledby pointing to the h2 heading element

## States to Handle
| State | Condition | Behavior |
|-------|-----------|----------|
| default | 3 PlanCards rendered, none is current | All cards show "Choose Plan" CTA |
| with-current-plan | subscription.plan_type matches one planKey | Matching card shows disabled "Current Plan"; others show "Choose Plan" |
| scroll-target | User clicks #plans anchor from UsageCard | Section scrolls into view smoothly |
| mobile-stacked | Viewport below md breakpoint | Single column layout, recommended (3-Month) card rendered first |

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
| AC-009 | integration | pre_merge | false |
| AC-010 | unit | pre_merge | false |
| AC-011 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /billing/checkout redirects correctly to Stripe Checkout (live test required post-deploy)
- No regression on BillingContent rendering (PlansSection added below, not replacing anything)
- Existing test suite passes without modification
- UsageCard's #plans anchor link continues to resolve

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/integration/BillingPlansScroll.test.tsx | integration | pre_merge | pending |
| AC-010 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/billing/PlansSection.tsx:TBD | tests/ui/unit/PlansSection.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove PlansSection from BillingContent, re-open spec |
| RT-002 | POST /billing/checkout returns non-2xx | Block deploy, investigate with Stripe |
| RT-003 | #plans anchor scroll breaks after deploy | Verify id attribute present, check for CSS scroll-margin conflicts |

## Design Notes
- Plan data is hardcoded, not fetched from API — if pricing changes, this component must be updated and redeployed
- The recommended highlight is hardcoded on 3-Month plan (isRecommended=true) per gap-answer q19; not dynamically determined
- Mobile reorder (recommended first) may use CSS `order` utility or conditional array sort — implementation choice deferred to executor
- currentPlanKey mapping from subscription.plan_type to planKey ("monthly" | "3month" | "6month") requires a lookup; the API plan_type field format should be verified during implementation
