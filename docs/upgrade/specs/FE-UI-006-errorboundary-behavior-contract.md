---
spec_id: FE-UI-006
title: "Finalize ErrorBoundary — behavior contract for redesign"
priority: low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: all routes (shared)
component_file: components/ErrorBoundary/ErrorBoundary.tsx
tier: shared
---

## Problem Statement
**Current behavior:** ErrorBoundary is a React class component that catches uncaught JS exceptions via `getDerivedStateFromError` / `componentDidCatch`. It renders a centered fallback with a user-friendly message and a "Try again" reset button. It also accepts custom `fallback` props (ReactNode or render function). It is wrapped around every page route (10 pages) and is the only crash-recovery mechanism in the app.
**Required behavior:** No change. ErrorBoundary remains exclusively for uncaught React render errors (JS exceptions). All user-facing API error states (non-2xx responses) must be handled inline per-component with contextual error messages and Retry buttons — never via ErrorBoundary takeover. This spec documents that contract so all page-level specs treat it as authoritative.
**User impact:** None — no visual or behavioral change. Violation of this contract (e.g., a page letting an API error propagate to ErrorBoundary) would cause a full-section wipeout instead of a scoped inline error, degrading UX.

## Evidence
**Mockup files:** (none — no visual change for this component)
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json (finalized shared decisions)
**Gap answers source:** docs/upgrade/gap-answers/shared-components.json

## Architecture & Ownership Map
**Component file:** components/ErrorBoundary/ErrorBoundary.tsx
**Page file(s):** app/dashboard/layout.tsx, app/settings/page.tsx, app/applications/[id]/page.tsx, app/applications/[id]/company-research/page.tsx, app/applications/[id]/cover-letter/page.tsx, app/applications/[id]/interview-prep/page.tsx, app/applications/[id]/cv-tailored/page.tsx, app/applications/[id]/vpr/page.tsx, app/applications/[id]/gap-analysis/page.tsx, app/cv-center/page.tsx, app/billing/page.tsx
**Tier:** shared — cascade risk: high
**API dependencies:** none
**Imports this component:** all 11 files listed above

## Fix Plan
**Files to modify:** none — behavior contract only, no code changes required
**Behavior changes:** none — this spec documents finalized behavior, not a code change
**Non-goals (explicitly out of scope):** visual changes, new props, API integration, changing the default fallback UI
**Rollback plan:** N/A — no code changes

## Acceptance Criteria

- [ ] AC-001: Given any API failure on any page, when the request returns a non-2xx response, then no ErrorBoundary takeover occurs — the error is handled inline by the affected component (error message + Retry button rendered inside the component's own DOM subtree, not ErrorBoundary's fallback)
- [ ] AC-002: Given an uncaught JS exception during React rendering, when the exception propagates to ErrorBoundary, then ErrorBoundary renders its fallback UI (centered message + "Try again" button) and logs to CloudWatch — confirming the existing crash-recovery contract is intact

## States to Handle
N/A — no new states; contract documents existing behavior constraints only

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual change to ErrorBoundary's fallback UI
- No new props added to ErrorBoundary
- No changes to `getUserMessage` mapping logic
- All existing uses continue to work identically

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | components/ErrorBoundary/ErrorBoundary.tsx:30 | tests/ui/unit/ErrorBoundary.test.tsx | unit | pre_merge | pending |
| AC-002 | components/ErrorBoundary/ErrorBoundary.tsx:33-41 | tests/ui/unit/ErrorBoundary.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any page shows ErrorBoundary takeover for an API error (not a JS exception) | Investigate the affected page component — it must catch API errors inline and render its own error state instead of letting the error propagate |
| RT-002 | ErrorBoundary fails to catch an uncaught JS exception | Verify ErrorBoundary is still wrapping the affected route in the component tree |

## Design Notes
- No unresolved ambiguities — behavior fully decided
- This spec is referenced by all page-level specs as the authoritative error-handling contract
- The `getUserMessage` function handles HTTP-status-like errors that reach ErrorBoundary (legacy path); redesign pages must not rely on this — they must catch API errors before they reach ErrorBoundary
