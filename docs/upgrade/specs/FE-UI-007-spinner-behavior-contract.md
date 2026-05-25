---
spec_id: FE-UI-007
title: "Finalize Spinner — behavior contract for redesign"
priority: low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: all routes (shared)
component_file: components/ui/Spinner.tsx
tier: shared
---

## Problem Statement
**Current behavior:** Spinner is a lightweight SVG animation component with three sizes (`sm`, `md`, `lg`), an `aria-label` for accessibility, and `role="status"`. It is currently used for both page/section data-loading states and inline button loading indicators across 10 pages and shared components (Button, ModuleCard, ProtectedLayout).
**Required behavior:** Spinner's role is narrowed to inline/button loading indicators only (e.g., "Creating..." with a disabled button). All page-level and section-level data-loading states must use skeleton placeholders with shimmer instead of Spinner. The Spinner component itself does not change — its usage context changes across consuming pages. This spec documents that contract so all page-level specs treat it as authoritative.
**User impact:** None from Spinner itself — no visual or behavioral change to the component. Pages that currently show a Spinner during data fetch will migrate to skeletons (covered by per-page specs, not this spec).

## Evidence
**Mockup files:** (none — no visual change for this component)
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json (finalized shared decisions)
**Gap answers source:** docs/upgrade/gap-answers/shared-components.json

## Architecture & Ownership Map
**Component file:** components/ui/Spinner.tsx
**Page file(s):** app/dashboard/layout.tsx, app/applications/[id]/page.tsx, app/applications/[id]/company-research/page.tsx, app/applications/[id]/cover-letter/page.tsx, app/applications/[id]/interview-prep/page.tsx, app/applications/[id]/cv-tailored/page.tsx, app/applications/[id]/vpr/page.tsx, app/applications/[id]/gap-analysis/page.tsx, app/cv-center/page.tsx, app/billing/page.tsx
**Shared component consumers:** components/ui/Button.tsx, components/ModuleCard/ModuleCard.tsx, components/layout/ProtectedLayout.tsx
**Tier:** shared — cascade risk: high
**API dependencies:** none
**Imports this component:** all 13 files listed above

## Fix Plan
**Files to modify:** none — behavior contract only, no code changes required
**Behavior changes:** none — this spec documents finalized behavior, not a code change. Per-page migration from Spinner to skeleton is covered by each page's own spec.
**Non-goals (explicitly out of scope):** visual changes to Spinner, new props, new sizes, removing Spinner from the codebase, implementing skeleton components (covered by per-page specs)
**Rollback plan:** N/A — no code changes

## Acceptance Criteria

- [ ] AC-001: Given any page-level or section-level data-loading state, when data is being fetched, then a skeleton placeholder with shimmer is rendered — not a Spinner component
- [ ] AC-002: Given a button that triggers an async action (e.g., form submission), when the action is in progress, then the button shows a Spinner at size `sm` alongside a loading label (e.g., "Creating...") and the button is disabled — confirming the inline-use contract is intact

## States to Handle
N/A — no new states; contract documents existing behavior constraints only

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual change to Spinner's SVG or animation
- No new props added to Spinner
- No changes to size map (`sm`, `md`, `lg`)
- All existing inline/button uses continue to work identically
- `role="status"` and `aria-label` accessibility contract unchanged

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | components/ui/Spinner.tsx:17 | tests/ui/unit/Spinner.test.tsx | unit | pre_merge | pending |
| AC-002 | components/ui/Spinner.tsx:17 | tests/ui/unit/Spinner.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any page uses Spinner as the primary loading indicator for a data-fetch state (full-section spinner instead of skeleton) | Investigate the affected page — it must use skeleton placeholders per its own page spec |
| RT-002 | Spinner no longer renders in inline button loading states | Verify Button component still integrates Spinner for its loading prop |

## Design Notes
- No unresolved ambiguities — behavior fully decided
- This spec is referenced by all page-level specs as the authoritative loading-state contract
- Skeleton component implementation is out of scope for this spec — each page spec defines its own skeleton shape (rows, cards, etc.)
- The Spinner component file itself requires zero code changes; only its call sites change (covered by per-page specs)
