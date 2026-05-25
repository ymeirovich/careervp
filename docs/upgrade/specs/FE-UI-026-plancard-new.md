---
spec_id: FE-UI-026
title: "new PlanCard — data-driven pricing card with current/recommended/selectable states"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing (section within page)
component_file: src/frontend/components/billing/PlanCard.tsx
tier: feature
---

## Problem Statement
**Current behavior:** Plan options are rendered as inline divs within BillingContent with hardcoded Monthly ($20) and Annual ($16) layouts. No reusable card component exists. No current-plan disabled state. Recommended plan uses a "Save 20%" badge approach.
**Required behavior:** A reusable PlanCard component driven by props (planKey, displayName, pricePerMonth, billingPeriodLabel, isCurrentPlan, isRecommended, onChoosePlan). Renders four visual states: selectable (orange "Choose Plan" button), selectable-recommended (thick border + "Choose Plan"), current (disabled gray "Current Plan" button), and current-recommended (thick border + disabled "Current Plan"). Hover state applies a light background tint on non-current cards. "Choose Plan" click triggers POST /billing/checkout redirect to Stripe Checkout in the same tab.
**User impact:** Users clearly see which plan they're on, which is recommended, and can select a new plan with a single click.

## Evidence
**Mockup files:** subscription plans page.png, Subscription plan page 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/billing/PlanCard.tsx
**Page file(s):** app/billing/page.tsx (via BillingContent → PlansSection)
**Tier:** feature — cascade risk: low (contained within /billing)
**API dependencies:** POST /billing/checkout (triggered on "Choose Plan" click — returns Stripe Checkout URL for same-tab redirect)
**Imports this component:** PlansSection (src/frontend/components/billing/PlansSection.tsx)

## Fix Plan
**Files to modify:**
- src/frontend/components/billing/PlanCard.tsx (new file)

**Behavior changes:**
- Props interface: planKey, displayName, pricePerMonth, billingPeriodLabel, isCurrentPlan, isRecommended, onChoosePlan
- Card layout: plan name (h3), price display ("$X/mo" with large numeral), billing period label (small text), CTA button
- isRecommended=true: thick rounded border (border-2 border-primary-action or equivalent), visually distinguishing from standard cards
- isCurrentPlan=true: CTA button text changes to "Current Plan", button is disabled with gray/muted styling and cursor-not-allowed
- isCurrentPlan=false: CTA button text is "Choose Plan", orange/primary-action background, clickable
- Hover on non-current cards: light background tint change (e.g., bg-card-hover or subtle opacity shift)
- onChoosePlan fires on "Choose Plan" button click only (not on card click), triggers POST /billing/checkout with planKey, redirects to returned Stripe Checkout URL in same tab via window.location.href
- data-testid="plan-card-{planKey}" on root element for test targeting

**Non-goals (explicitly out of scope):**
- No feature comparison list within the card (price and billing period only)
- No animation on state transitions
- No confirmation modal before checkout redirect
- No error toast on POST /billing/checkout failure (handled by redirect failure or Stripe error page)

**Rollback plan:** Remove PlanCard component and revert PlansSection to not render cards — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given isCurrentPlan=false and isRecommended=false, when PlanCard renders, then an enabled orange "Choose Plan" button is displayed with standard border
- [ ] AC-002: Given isCurrentPlan=false and isRecommended=true, when PlanCard renders, then an enabled orange "Choose Plan" button is displayed with a thick rounded primary-action border on the card
- [ ] AC-003: Given isCurrentPlan=true and isRecommended=false, when PlanCard renders, then a disabled gray "Current Plan" button is displayed with cursor-not-allowed and standard border
- [ ] AC-004: Given isCurrentPlan=true and isRecommended=true, when PlanCard renders, then a disabled gray "Current Plan" button is displayed with cursor-not-allowed and a thick rounded primary-action border on the card
- [ ] AC-005: Given isCurrentPlan=false, when user hovers over PlanCard, then background tint changes to a lighter shade
- [ ] AC-006: Given isCurrentPlan=true, when user hovers over PlanCard, then no background tint change occurs (hover effect suppressed)
- [ ] AC-007: Given PlanCard renders with planKey="monthly", displayName="Monthly Plan", pricePerMonth=30, billingPeriodLabel="Billed monthly", when displayed, then card shows "Monthly Plan" heading, "$30/mo" price, and "Billed monthly" label
- [ ] AC-008: Given PlanCard renders with planKey="3month", displayName="3 Month Plan", pricePerMonth=25, billingPeriodLabel="Billed $75 every 3 months", when displayed, then card shows "3 Month Plan" heading, "$25/mo" price, and "Billed $75 every 3 months" label
- [ ] AC-009: Given PlanCard renders with planKey="6month", displayName="6 Month Plan", pricePerMonth=20, billingPeriodLabel="Billed $120 every 6 months", when displayed, then card shows "6 Month Plan" heading, "$20/mo" price, and "Billed $120 every 6 months" label
- [ ] AC-010: Given isCurrentPlan=false, when "Choose Plan" button is clicked, then onChoosePlan callback is invoked
- [ ] AC-011: Given isCurrentPlan=true, when "Current Plan" button is clicked, then onChoosePlan callback is NOT invoked (button is disabled)
- [ ] AC-012: Given onChoosePlan is invoked, when POST /billing/checkout responds with a Stripe Checkout URL, then the browser redirects to that URL in the same tab via window.location.href
- [ ] AC-013: Given Hebrew locale is active, when PlanCard renders, then displayName, billingPeriodLabel, and button text ("Choose Plan" / "Current Plan") render in Hebrew with RTL layout
- [ ] AC-014: Given PlanCard renders, when inspected for accessibility, then the CTA button has aria-disabled="true" when isCurrentPlan=true and the card root has data-testid="plan-card-{planKey}"
- [ ] AC-015: Given PlanCard renders, when inspected for accessibility, then the price display has aria-label describing the full price (e.g., "25 dollars per month, billed 75 dollars every 3 months")

## States to Handle
| State | Trigger | Border | Button Text | Button Style | Hover |
|-------|---------|--------|-------------|--------------|-------|
| selectable | isCurrentPlan=false, isRecommended=false | standard (border-border-default) | "Choose Plan" | orange bg, white text, enabled | light bg tint |
| selectable-recommended | isCurrentPlan=false, isRecommended=true | thick (border-2 border-primary-action) | "Choose Plan" | orange bg, white text, enabled | light bg tint |
| current | isCurrentPlan=true, isRecommended=false | standard (border-border-default) | "Current Plan" | gray bg, muted text, disabled, cursor-not-allowed | none |
| current-recommended | isCurrentPlan=true, isRecommended=true | thick (border-2 border-primary-action) | "Current Plan" | gray bg, muted text, disabled, cursor-not-allowed | none |

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
| AC-012 | integration | post_deploy | false |
| AC-013 | unit | pre_merge | false |
| AC-014 | unit | pre_merge | false |
| AC-015 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /billing/checkout redirects correctly to Stripe Checkout (live test required post-deploy)
- No regression on BillingContent rendering (PlanCard is a new leaf component)
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/integration/PlanCardCheckout.test.tsx | integration | post_deploy | pending |
| AC-013 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/billing/PlanCard.tsx:TBD | tests/ui/unit/PlanCard.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove PlanCard from PlansSection, re-open spec |
| RT-002 | POST /billing/checkout returns non-2xx for any planKey | Block deploy, investigate Stripe integration |
| RT-003 | Stripe Checkout redirect fails or loops | Disable "Choose Plan" buttons, add error handling, investigate |

## Design Notes
- The recommended highlight (thick border) is hardcoded on the 3-Month plan via isRecommended prop — PlansSection always passes isRecommended=true for planKey="3month" per gap-answer q19
- No "Save 20%" badge — the old approach is replaced by the thick border highlight per diff analysis
- The onChoosePlan callback is responsible for the POST /billing/checkout call and redirect; PlanCard itself does not import fetch or API utilities — the callback is provided by PlansSection
- Price display uses a large numeral for the dollar amount with a smaller "/mo" suffix, matching the existing card pattern in the current codebase
- The disabled button uses aria-disabled="true" rather than the HTML disabled attribute to maintain focusability for screen readers
