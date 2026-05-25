# Phase 5 — Batch D: Shared Components (Behavior Contract)
# Components: ErrorBoundary, Spinner
# Model: Opus | New conversation per batch
# Note: Neither component changes visually. These specs document the finalized behavior
#       contract so all future specs can reference them without re-litigating decisions.

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: These are behavior-contract specs, not visual-change specs. Correctness matters more than length.

TASK: Write TWO minimal upgrade specs — one for ErrorBoundary and one for Spinner. Both have NO visual changes. The specs exist solely to document finalized behavior contracts so all other specs can reference them as authoritative decisions.

THINK before writing each spec:
1. What does the component currently do?
2. What is the finalized behavior contract? (from shared-components.json)
3. Are there any ACs at all, or is this a pure documentation spec? (There are minimal ACs — one each confirming the contract.)
4. What regression risk exists? (Any change to either component could silently affect every page.)

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "Finalize {COMPONENT_NAME} — behavior contract for redesign"
priority: low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: all routes (shared)
component_file: {FILE_PATH}
tier: shared

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** (none — no visual change for this component)
**Diff analysis source:** docs/upgrade/diff-analysis/billing.json (finalized shared decisions)
**Gap answers source:** docs/upgrade/gap-answers/shared-components.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** all routes
**Tier:** shared — cascade risk: high
**API dependencies:** none
**Imports this component:** all page routes

## Fix Plan
**Files to modify:** none — behavior contract only, no code changes required
**Behavior changes:** none — this spec documents finalized behavior, not a code change
**Non-goals (explicitly out of scope):** visual changes, new props, API integration
**Rollback plan:** N/A — no code changes

## Acceptance Criteria
(Minimal — these verify the contract is not violated, not that new behavior was introduced)

- [ ] AC-001: Given any API failure on any page, when the request returns a non-2xx response, then no ErrorBoundary/Spinner takeover occurs — error is handled inline by the affected component
- [ ] AC-002: ...

## States to Handle
N/A — no new states; contract documents existing behavior constraints only

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual change to either component
- No new props added
- All existing uses continue to work identically

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any page shows ErrorBoundary takeover for an API error (not a JS exception) | Investigate and fix inline error handler in the affected component |

## Design Notes
- No unresolved ambiguities — behavior fully decided
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: ErrorBoundary
File: components/ErrorBoundary/ErrorBoundary.tsx
Tier: shared
Change type: no change (behavior contract only)
Today's date: 2026-05-23

**Contract verification entry (/billing — representative):**
```json
{
  "route": "/billing",
  "component": "ErrorBoundary",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "No visual change noted — shared component behavior finalized; no backend data required",
  "in_scope": true
}
```

**Shared component decisions (from shared-components.json):**
```json
{
  "component": "ErrorBoundary",
  "decisions": [
    {
      "topic": "error_state",
      "decision": "API failures use inline error message with Retry button inside the affected section/card — NOT a full-page ErrorBoundary takeover. ErrorBoundary remains as the React error boundary for uncaught JS exceptions only."
    },
    {
      "topic": "scope",
      "decision": "ErrorBoundary is kept for uncaught React render errors (JS exceptions). It should NOT change visually in the redesign — it is a safety net, not a primary error UX. All user-facing API error states are handled inline per-component."
    }
  ]
}
```

---

### Component 2: Spinner
File: components/ui/Spinner.tsx
Tier: shared
Change type: no change (behavior contract only)
Today's date: 2026-05-23

**Contract verification entry (/billing — representative):**
```json
{
  "route": "/billing",
  "component": "Spinner",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "No visual change noted — shared component behavior finalized (Spinner retained for inline/button use only); no backend data required",
  "in_scope": true
}
```

**Shared component decisions (from shared-components.json):**
```json
{
  "component": "Spinner",
  "decisions": [
    {
      "topic": "loading_state",
      "decision": "Data-loading states use skeleton placeholders with shimmer, NOT the Spinner component. Spinner remains for inline/button loading indicators only.",
      "derived_from": [
        {"route": "/dashboard", "answer": "Skeleton rows (3 placeholder rows with shimmer)"},
        {"route": "/applications/[id]", "answer": "Skeleton cards (6 placeholder cards matching card shape with shimmer)"},
        {"route": "/applications/[id]/gap-analysis", "answer": "Skeleton cards (3-4 placeholder question cards with shimmer)"},
        {"route": "/cv-center", "answer": "Skeleton rows (3 placeholder rows with shimmer)"}
      ]
    },
    {
      "topic": "usage_pattern",
      "decision": "Spinner is still used for inline button loading states (e.g., 'Creating...' with disabled button). It is NOT used as the primary page/section loading indicator — skeletons replace that role in the redesign."
    }
  ]
}
```

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the two spec markdowns, back-to-back.
