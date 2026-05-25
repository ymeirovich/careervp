---
spec_id: FE-UI-024
title: "new BillingInfoCard — payment method display with Manage Billing CTA"
priority: medium
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /billing
component_file: src/frontend/components/billing/BillingInfoCard.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No payment method information is displayed on the billing page. The only billing action is a disabled "Manage Subscription" button.
**Required behavior:** Dedicated BillingInfoCard component showing the user's payment method (masked card number "•••• XXXX", brand icon/text), a "Billing handled securely via Stripe" trust line, and an orange "Manage Billing" CTA that opens the Stripe billing portal in a new tab. Empty state for trial users with no payment method shows "No payment method" text and an "Add Payment Method" CTA.
**User impact:** Users can verify their payment method on file and access Stripe portal for billing management without leaving the billing overview.

## Evidence
**Mockup files:** Billing page.png, Billing page continued.png
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json
**Gap answers source:** docs/upgrade/gap-answers/billing.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/billing/BillingInfoCard.tsx
**Page file(s):** app/billing/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /users/me/subscription (new fields: payment_method.last4, payment_method.brand — requires backend webhook change), POST /billing/portal
**Imports this component:** BillingContent (app/billing/page.tsx)

## Fix Plan
**Files to modify:**
- src/frontend/components/billing/BillingInfoCard.tsx (new file)

**Behavior changes:**
- Card heading: "Billing Info"
- Has-payment-method state: displays "Payment method •••• {last4} ({brand})" with brand text/icon, plus "Billing handled securely via Stripe." trust line
- Empty state (no payment method): displays "No payment method" text with "Add Payment Method" CTA button
- "Manage Billing" CTA (orange): calls POST /billing/portal, opens returned URL via window.open (new tab)
- "Add Payment Method" CTA (empty state): same action as Manage Billing (Stripe portal handles adding payment methods)
- Loading state: skeleton placeholder matching card shape with shimmer
- Error state: inline error message with "Retry" button

**Non-goals (explicitly out of scope):**
- No direct card input form (Stripe portal handles all PCI-sensitive operations)
- No multiple payment method management
- No invoice history display

**Backend prerequisite:** GET /users/me/subscription must return payment_method.last4 and payment_method.brand fields. This requires webhook handler changes (checkout.session.completed, customer.subscription.updated) to persist card details to DynamoDB. Frontend implementation is blocked until this backend change ships.

**Rollback plan:** Revert to prior billing page component — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given subscription response includes payment_method with last4="6363" and brand="visa", when card renders, then text "Payment method •••• 6363 (Visa)" is displayed
- [ ] AC-002: Given subscription response has no payment_method (null/undefined), when card renders, then text "No payment method" is displayed with "Add Payment Method" CTA
- [ ] AC-003: Given payment method is displayed, when card renders, then "Billing handled securely via Stripe." trust text is shown below the payment method
- [ ] AC-004: Given "Manage Billing" CTA is clicked, when POST /billing/portal returns a URL, then that URL is opened in a new tab via window.open
- [ ] AC-005: Given "Add Payment Method" CTA is clicked (empty state), when POST /billing/portal returns a URL, then that URL is opened in a new tab via window.open
- [ ] AC-006: Given billing info data is loading, when card renders, then a skeleton placeholder with shimmer animation is displayed
- [ ] AC-007: Given subscription fetch fails, when card renders, then an inline error message with "Retry" button is displayed
- [ ] AC-008: Given "Retry" button is clicked, when error state is active, then data is re-fetched
- [ ] AC-009: Given POST /billing/portal fails, when CTA is clicked, then an inline error message is displayed (portal URL not opened)
- [ ] AC-010: Given Hebrew locale is active, when card renders, then all text renders in Hebrew with RTL layout
- [ ] AC-011: Given payment method is displayed, when inspected for accessibility, then the masked card element has aria-label "Payment method ending in {last4}, {brand}"
- [ ] AC-012: Given card renders in any state, when inspected, then "Manage Billing" / "Add Payment Method" buttons have accessible names and are keyboard-focusable

## States to Handle
| State | Condition | Display | CTA |
|-------|-----------|---------|-----|
| has-payment-method | payment_method.last4 exists | "•••• {last4} ({brand})" + Stripe trust line | "Manage Billing" (orange) |
| no-payment-method (empty) | payment_method is null | "No payment method" | "Add Payment Method" |
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
| AC-011 | unit | pre_merge | false |
| AC-012 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on existing billing API calls (GET /users/me/subscription, POST /billing/portal)
- Existing Stripe webhook handling unaffected
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/billing/BillingInfoCard.tsx:TBD | tests/ui/unit/BillingInfoCard.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx on GET /users/me/subscription or POST /billing/portal | Block deploy, investigate |
| RT-003 | Backend prerequisite (webhook card storage) not deployed | Block frontend implementation, spec remains draft |

## Design Notes
- Backend prerequisite: GET /users/me/subscription does NOT currently return last4/brand. Webhook handler must persist payment_method.card.last4 + brand from Stripe events (checkout.session.completed, customer.subscription.updated) to DynamoDB before this component can be fully implemented.
- Frontend spec is complete and testable with mocked data; integration testing blocked on backend change.
- "Manage Billing" opens Stripe portal in new tab (window.open) per gap-answer q16 — keeps app open in current tab.
- Empty state shown for trial users per gap-answer q3 and q18.
- aria-label format per gap-answer q9: "Payment method ending in {last4}, {brand}"
