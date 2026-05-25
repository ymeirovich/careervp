# Phase 5 — Batch K: Billing Plans Section
# Components: PlansSection (new page section), PlanCard (new)
# Model: Opus | New conversation per batch
# Route: /billing (lower section of same page — NOT a separate route)
# Prerequisite: Run Batch J first. PlansSection is part of /billing — reference BillingContent spec from J.

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — PlansSection (new section on /billing page) and PlanCard (new, rendered 3× inside PlansSection).

THINK before writing each spec:
1. PlansSection: How does it integrate with BillingContent? What scroll anchor does UsageCard link to? What is the layout (3 cards horizontal → vertical on mobile)?
2. PlanCard: What is the data-driven variant behavior? (current plan shows disabled 'Current Plan' button, others show 'Choose Plan' → POST /billing/checkout). What is the hardcoded 'recommended' highlight logic?
3. What are the 3 plans and their pricing?
4. What states does PlanCard have? (current | selectable | recommended + current | recommended + selectable)
5. What is BLOCKED? Nothing.

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "new {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing (section within page)
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** subscription plans page.png, Subscription plan page 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** app/billing/page.tsx (via BillingContent)
**Tier:** feature — cascade risk: low (contained within /billing)
**API dependencies:** GET /users/me/subscription (current plan), POST /billing/checkout (plan selection)
**Imports this component:** BillingContent

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Remove section from BillingContent — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for all 3 plan states (current, selectable, recommended), mobile layout, Hebrew i18n, Stripe Checkout redirect.

## States to Handle
{component-specific — see below}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /billing/checkout redirects correctly to Stripe Checkout (live test required post-deploy)
- No regression on BillingContent rendering (PlansSection added below, not replacing anything)
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove PlansSection from BillingContent, re-open spec |
| RT-002 | POST /billing/checkout returns non-2xx | Block deploy, investigate with Stripe |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: PlansSection
File: components/billing/PlansSection.tsx (new)
Tier: feature
Change type: new (section rendered inside BillingContent on /billing page)
Today's date: 2026-05-23
Routing decision: Plans are rendered as a lower section of the same /billing page — per gap-answer q14. UsageCard's upgrade link smooth-scrolls to this section via anchor.

**Diff analysis layout changes:**
```json
[
  {
    "description": "Plans page shows 3 plan cards in a horizontal row instead of the current 2-column grid: Monthly Plan ($30/mo), 3 Month Plan ($25/mo billed $75), 6 Month Plan ($20/mo billed $120)",
    "change_type": "structure"
  },
  {
    "description": "Recommended plan (3 Month Plan) has a thick rounded border highlight instead of the current 'Save 20%' badge approach",
    "change_type": "structure"
  },
  {
    "description": "'Questions? Contact us' link at the bottom of the Plans section as a centered line",
    "change_type": "spacing"
  }
]
```

**Gap answers — billing:**
```json
[
  {
    "question_id": "q6",
    "component": "PlanCard",
    "topic": "responsive",
    "answer": "Stack vertically (1 column) on mobile (below md breakpoint), recommended plan first"
  },
  {
    "question_id": "q11",
    "component": "PlansPage",
    "topic": "i18n",
    "answer": "Yes — Hebrew translations for: 'Monthly Plan', '3 Month Plan', '6 Month Plan', 'Current Plan', 'Choose Plan', 'Billed monthly', 'Billed $X every N months', 'Save money', 'Best value', 'Questions?', 'Contact us'"
  },
  {
    "question_id": "q14",
    "component": "PlansSection",
    "topic": "routing",
    "answer": "Plans are rendered as a lower section of the same /billing page — no separate route needed"
  }
]
```

**Pricing data (canonical per gap-answer q13):**
| Plan | Display price | Billing period | Billing amount |
|---|---|---|---|
| Monthly Plan | $30/mo | Billed monthly | $30 |
| 3 Month Plan | $25/mo | Billed $75 every 3 months | $75 |
| 6 Month Plan | $20/mo | Billed $120 every 6 months | $120 |

**States to handle for PlansSection:**
- default (3 cards rendered)
- scroll-target (smooth-scroll from UsageCard anchor)
- mobile-stacked (single column, recommended first)

---

### Component 2: PlanCard
File: components/billing/PlanCard.tsx (new, rendered 3× inside PlansSection)
Tier: feature
Change type: new
Today's date: 2026-05-23

**Diff analysis layout changes:**
```json
[
  {
    "description": "Current plan card on Plans page shows a grayed-out 'Current Plan' button instead of the active 'Choose Plan' CTA",
    "change_type": "addition"
  },
  {
    "description": "Recommended plan (3 Month Plan) has a thick rounded border highlight — hardcoded, not dynamic",
    "change_type": "structure"
  }
]
```

**Gap answers — billing:**
```json
[
  {
    "question_id": "q5",
    "component": "PlanCard",
    "topic": "hover_state",
    "answer": "Light background tint change on hover"
  },
  {
    "question_id": "q7",
    "component": "PlansPage",
    "topic": "edge_case",
    "answer": "Choose Plan → redirect to Stripe Checkout (POST /billing/checkout) in same tab"
  },
  {
    "question_id": "q8",
    "component": "PlansPage",
    "topic": "edge_case",
    "answer": "Show all 3 plans — 'Current Plan' (disabled) on user's current plan, 'Choose Plan' on others. Allow downgrade."
  },
  {
    "question_id": "q19",
    "component": "PlanCard",
    "topic": "highlight_logic",
    "answer": "Highlight is hardcoded — 3 Month Plan is always shown as the recommended plan regardless of user's current plan. Not dynamic."
  }
]
```

**PlanCard prop interface (inform ACs and implementation):**
```typescript
interface PlanCardProps {
  planKey: "monthly" | "3month" | "6month";
  displayName: string;        // "Monthly Plan" | "3 Month Plan" | "6 Month Plan"
  pricePerMonth: number;      // 30 | 25 | 20
  billingPeriodLabel: string; // "Billed monthly" | "Billed $75 every 3 months" | ...
  isCurrentPlan: boolean;     // drives disabled 'Current Plan' button
  isRecommended: boolean;     // drives thick border highlight (hardcoded true for 3month)
  onChoosePlan: () => void;   // triggers POST /billing/checkout in same tab
}
```

**States to handle for PlanCard:**
| State | Trigger | UI |
|---|---|---|
| selectable | isCurrentPlan=false, isRecommended=false | 'Choose Plan' orange button |
| selectable-recommended | isCurrentPlan=false, isRecommended=true | thick border + 'Choose Plan' |
| current | isCurrentPlan=true, isRecommended=false | 'Current Plan' disabled gray button |
| current-recommended | isCurrentPlan=true, isRecommended=true | thick border + 'Current Plan' disabled |
| hover | any non-current state on hover | light background tint |

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the two spec markdowns, back-to-back.
