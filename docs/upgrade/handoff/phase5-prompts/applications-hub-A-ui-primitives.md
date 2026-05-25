# Phase 5 — Batch A: UI Primitives (applications-hub route)
# Components: Badge, ProgressBar
# Model: Opus | New conversation per batch
# Paste this entire file as your first message

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — one for Badge and one for ProgressBar — both scoped to changes visible on route /applications/[id] and shared across all routes.

THINK before writing each spec:
1. What does the component currently do? (from component map below)
2. What visual changes are required? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks?

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "Upgrade {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id] (change applies to all routes)
component_file: {FILE_PATH}
tier: ui-primitive

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json
**Gap answers source:** docs/upgrade/gap-answers/applications-hub.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** ui-primitive — cascade risk: high
**API dependencies:** none
**Imports this component:** {list from component-map.json for this component}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for every visual change, gap answer, keyboard/ARIA, Hebrew i18n if applicable, responsive.

## States to Handle
default | loading | error | empty | hover | focus | disabled | {others from gap answers}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |

## Design Notes
- {unresolved ambiguities requiring human decision}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: Badge
File: components/ui/Badge.tsx
Tier: ui-primitive
Today's date: 2026-05-23

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "Badge",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Visual-only change: outlined/soft-fill variants (green for Complete/Ready, blue for Generating/Processing, unchanged solid red for Failed) replacing solid-fill style — no backend data required",
  "in_scope": true
}
```

**Also appears on /applications route (same Badge change):**
```json
{
  "route": "/applications",
  "component": "Badge",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Visual-only change: new Draft (warm orange outlined) and Archived (muted beige outlined) style variants — no backend data required",
  "in_scope": true
}
```

**Also appears on /dashboard route (same Badge change):**
```json
{
  "route": "/dashboard",
  "component": "Badge",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Visual-only change: new Draft (warm orange outlined) and Archived (muted beige outlined) style variants — no backend data required",
  "in_scope": true
}
```

**Diff analysis entry (applications-hub):**
```json
{
  "component": "Badge",
  "file": "components/ui/Badge.tsx",
  "tier": "ui-primitive",
  "change_type": "modify",
  "visual_description": "Current badges are solid-fill with white text. Screenshot shows outlined/soft-fill style: Complete = green bg-green-50 text-green-700, Ready = same green soft, Generating = blue bg-blue-50 text-blue-700, Processing = blue soft, Failed = solid red with white text (unchanged), Final = green soft, Edited = blue/purple soft. Need new outlined/soft variants or restyle existing.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": [],
  "backend_data_required": "none",
  "backend_available": "yes"
}
```

**Token changes relevant to Badge:**
```json
[
  {
    "token": "--color-badge-complete-bg",
    "current": "complete uses 'success' variant — bg-state-active (#22C55E) with white text",
    "desired": "screenshot shows 'Complete' badge with green outlined/soft style — green bg with green text or green border with green text, not solid green with white",
    "confidence": "medium"
  },
  {
    "token": "--color-badge-generating-bg",
    "current": "no 'generating' badge variant exists — processing state shows spinner text only, no badge",
    "desired": "screenshot shows 'Generating' badge with blue/purple outlined style next to Tailored CV title; and 'Processing' badge with blue outlined style next to Job Fit Report title",
    "confidence": "medium"
  },
  {
    "token": "--color-badge-ready-bg",
    "current": "no dedicated 'ready' badge — ready state has no badge by default",
    "desired": "screenshot shows 'Ready' badge with green outlined/soft style next to Cover Letter title",
    "confidence": "medium"
  },
  {
    "token": "--color-badge-failed-bg",
    "current": "failed uses 'error' variant — bg-state-error (#EF4444) with white text",
    "desired": "screenshot shows 'Failed' badge — appears solid red with white text, consistent with current",
    "confidence": "high"
  }
]
```

**Gap answers relevant to Badge (applications-hub.json):**
```json
[
  {
    "question_id": "q10",
    "component": "Badge",
    "topic": "edge_case",
    "question": "Screenshots show badges on ALL module states (Complete, Ready, Processing, Generating, Failed, Final, Edited, Active). Should the Badge component add new soft/outlined variants, or restyle existing solid variants?",
    "answer": "Add a 'soft' prop to Badge that toggles between solid and outlined rendering",
    "applies_to_shared_component": false
  },
  {
    "question_id": "q15",
    "component": "Badge",
    "topic": "edge_case",
    "question": "Screenshots show green-outlined badges for 'Complete' and 'Ready' states, and blue-outlined for 'Generating' and 'Processing'. What is the intended color-to-state semantic mapping for the soft Badge variant?",
    "answer": "Confirmed mapping: green = terminal success states (Complete, Final, Edited); blue = in-progress states (Generating, Processing); red = failure (Failed); gray/neutral = idle states (Ready, Active).",
    "applies_to_shared_component": true
  }
]
```

---

### Component 2: ProgressBar
File: components/ui/ProgressBar.tsx
Tier: ui-primitive
Today's date: 2026-05-23

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "ProgressBar",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Visual-only change: height increase to ~8-12px, rounded ends, percentage label added as sibling element — receives value prop from parent ModuleCard; no new backend data required",
  "in_scope": true
}
```

**Diff analysis entry (applications-hub):**
```json
{
  "component": "ProgressBar",
  "file": "components/ui/ProgressBar.tsx",
  "tier": "ui-primitive",
  "change_type": "modify",
  "visual_description": "Current is a thin 2px bar. Screenshot shows a thicker progress bar (approximately 8-12px height) with rounded ends. Processing modules show orange fill, failed module shows full-width red fill. Percentage label ('85%', '65%') shown to the right of the bar with 'Progress' label to the left.",
  "interaction_states_visible": ["processing", "error"],
  "interaction_states_needed_but_not_shown": [],
  "backend_data_required": "none — receives value prop",
  "backend_available": "yes"
}
```

**Token changes relevant to ProgressBar:**
```json
[
  {
    "token": "--color-progress-bar-error",
    "current": "ProgressBar has 'error' color option — bg-state-error (#EF4444)",
    "desired": "screenshot shows a thick red progress bar for failed Skills Assessment — consistent with current error color",
    "confidence": "high"
  }
]
```

**Gap answers relevant to ProgressBar (applications-hub.json):**
```json
[
  {
    "question_id": "q6",
    "component": "ModuleCard",
    "topic": "edge_case",
    "question": "The screenshots show a progress percentage (e.g., '85%', '65%') during processing. Should the ProgressBar label show 'Progress' text + percentage, or just the percentage?",
    "answer": "'Progress' label on left + percentage on right (as shown in screenshots)",
    "applies_to_shared_component": false
  },
  {
    "question_id": "q8",
    "component": "ModuleCard",
    "topic": "accessibility",
    "question": "The ProgressBar now shows visible percentage text. Should the existing aria-valuenow + aria-label remain, or should the visible label replace the sr-only span?",
    "answer": "Keep both — aria attributes for screen readers + visible label for sighted users",
    "applies_to_shared_component": false
  },
  {
    "question_id": "q16",
    "component": "ProgressBar",
    "topic": "edge_case",
    "question": "ProgressBar height in screenshots appears taller than the current h-2 (8px). Should the bar height increase (e.g. to h-3 or h-4), or does h-2 already match?",
    "answer": "Keep h-2 (8px) — no height change needed. The current value already matches the screenshot.",
    "applies_to_shared_component": true
  },
  {
    "question_id": "q17",
    "component": "ProgressBar",
    "topic": "edge_case",
    "question": "The progress 'Progress' label and percentage value (per q6) — should this be rendered as new props directly on the ProgressBar component, or rendered externally by ModuleCard wrapping the ProgressBar?",
    "answer": "New props on ProgressBar — ProgressBar receives showLabel and value props and renders the label row itself, making it reusable across any context.",
    "applies_to_shared_component": true
  },
  {
    "question_id": "q18",
    "component": "ProgressBar",
    "topic": "edge_case",
    "question": "In the Failed module card state there is a red bar at the bottom. Is this the existing ProgressBar at full width (value=100) with an error/red color variant, or a completely separate visual element?",
    "answer": "ProgressBar at 100% with an error/destructive color variant — reuse the ProgressBar component with value=100 and a destructive color prop.",
    "applies_to_shared_component": true
  }
]
```

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the two spec markdowns, back-to-back.
