# Phase 5 — Batch F: New Application Flow
# Components: NewApplicationPage (new, replaces modal), ChooseBaseCVModal (new, shared)
# Model: Opus | New conversation per batch
# Route: /dashboard (new page route TBD — see gap answers)

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — one for NewApplicationPage (which replaces NewApplicationModal) and one for ChooseBaseCVModal (shared across dashboard and cv-center). Both are new components.

THINK before writing each spec:
1. What does the current component do? (NewApplicationModal exists; ChooseBaseCVModal is entirely new)
2. What is required in the replacement? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks? NewApplicationModal is removed — the entire flow must transition cleanly.

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "Replace {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /dashboard (new application flow)
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** New Application Form.png, New Application-Job Description textbox edit.png, New Application Form-Choose Base CV Modal.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** feature — cascade risk: low (new components, replaces modal)
**API dependencies:** {list endpoints}
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert NewApplicationPage to NewApplicationModal pattern — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for loading, error, empty, hover states; keyboard/ARIA; Hebrew i18n; responsive.

## States to Handle
default | loading | error | empty | hover | focus | disabled | submitting

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- Existing NewApplicationModal tests must be updated to test NewApplicationPage — existing tests should not be deleted without replacement
- POST /jobs endpoint contract unchanged

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert to NewApplicationModal pattern, re-open spec |
| RT-002 | New non-2xx response on POST /jobs | Block deploy, investigate |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: NewApplicationPage (replaces NewApplicationModal)
File: app/applications/new/page.tsx (new — exact path TBD)
Tier: feature
Change type: replace (NewApplicationModal removed, replaced by full-page form)
Today's date: 2026-05-23

**Contract verification entry (/dashboard):**
```json
{
  "route": "/dashboard",
  "component": "NewApplicationModal",
  "change_type": "replace",
  "backend_classification": "yes",
  "resolution": "Replaced by full-page form at new route; form submission uses existing POST /jobs endpoint; ChooseBaseCVModal CV picker uses existing GET /users/me/cv endpoint — both exist in Swagger",
  "in_scope": true
}
```

**Diff analysis entry (dashboard):**
```json
{
  "component": "NewApplicationModal",
  "file": "components/NewApplicationModal/NewApplicationModal.tsx",
  "tier": "feature",
  "change_type": "replace",
  "visual_description": "Current is a modal dialog. Screenshot shows a full page with '← Back' navigation, same form fields (Job Title, Company, Job URL, Job Description), plus a 'Choose Base CV' step accessible before submission. Form layout is single-column in a card. Cancel and Create Application buttons at bottom.",
  "interaction_states_visible": ["default", "edit"],
  "interaction_states_needed_but_not_shown": ["loading", "error", "disabled"],
  "backend_data_required": "none — same POST /jobs endpoint",
  "backend_available": "yes"
}
```

**New components noted in diff analysis:**
```json
[
  "NewApplicationPage — full page replacement for NewApplicationModal, at a new route (e.g., /dashboard/new or /applications/new)",
  "ChooseBaseCVModal — modal with 'Select uploaded CV', 'Select generated CV' buttons and file upload option",
  "AccountDropdownMenu — dropdown panel under account button with Help, Log out, Upgrade items"
]
```

**Gap answers — dashboard:**
```json
[
  {
    "question_id": "q5",
    "component": "NewApplicationPage",
    "topic": "loading_state",
    "answer": "Button text changes to 'Creating...' with disabled state"
  },
  {
    "question_id": "q6",
    "component": "NewApplicationPage",
    "topic": "error_state",
    "answer": "Error banner at top of the form card"
  },
  {
    "question_id": "q11",
    "component": "NewApplicationPage",
    "topic": "i18n",
    "answer": "Yes — add Hebrew translations for all new strings ('← Back', 'Choose Base CV', 'Select uploaded CV', 'Select generated CV', 'Upload New CV')"
  },
  {
    "question_id": "q13",
    "component": "NewApplicationPage",
    "topic": "routing",
    "answer": "POST /jobs — the New Application flow does not have its own standalone route; it submits to POST /jobs. (Interpretation: the page itself lives at /applications/new or similar, but the form submits to POST /jobs)"
  },
  {
    "question_id": "q4",
    "component": "AccountDropdownMenu",
    "topic": "edge_case",
    "answer": "The 'Upgrade' button in the account dropdown navigates to /billing page"
  }
]
```

**Note on AccountDropdownMenu:**
The AccountDropdownMenu (Help, Log out, Upgrade) is a sub-component of AppHeader.
Include an AC in the AppHeader spec (already written in Batch B) or note it here as a
dependency. The NewApplicationPage spec does NOT own AccountDropdownMenu.

---

### Component 2: ChooseBaseCVModal (new, shared)
File: components/ChooseBaseCVModal/ChooseBaseCVModal.tsx (new)
Tier: feature
Change type: new (used by both NewApplicationPage and BaseCVsTable upload flow)
Today's date: 2026-05-23

**No contract verification entry** — new component. Backend: GET /users/me/cv verified in the
NewApplicationModal replacement entry above.

**Diff analysis (dashboard new_components_needed):**
```
"ChooseBaseCVModal — modal with 'Select uploaded CV', 'Select generated CV' buttons and file upload option"
```

**Diff analysis (cv-center new_components_needed):**
```
"ChooseBaseCVModal — modal overlay for selecting or uploading a base CV, with two modes:
choice mode (select uploaded/generated + upload) and upload-only mode"
```

**Gap answers — dashboard:**
```json
[
  {
    "question_id": "q7",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Shows a list/table of existing CVs to pick from within the same modal"
  },
  {
    "question_id": "q8",
    "component": "ChooseBaseCVModal",
    "topic": "empty_state",
    "answer": "Disable both Select buttons, highlight the Upload New CV section"
  },
  {
    "question_id": "q12",
    "component": "ChooseBaseCVModal",
    "topic": "accessibility",
    "answer": "Yes — focus trap + Escape to dismiss; also add aria-describedby for the subtitle text"
  },
  {
    "question_id": "q16",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "No — the Upload button is always enabled and directly opens the OS file picker"
  }
]
```

**Gap answers — cv-center (additional decisions for ChooseBaseCVModal):**
```json
[
  {
    "question_id": "q7",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Upload-only modal (showChoices=false — just file input + Upload) when opened from '+ Upload New CV' button on BaseCVsTable"
  },
  {
    "question_id": "q14",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Separate data model — generated CVs are a distinct type (TailoredCV produced by VPR/tailoring flow), not the same as uploaded base CVs"
  },
  {
    "question_id": "q15",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Match the existing disabled pattern already defined for buttons in the design system — do not introduce a new variant"
  },
  {
    "question_id": "q17",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Yes — add an X close icon in the top-right corner of the modal, following the spec"
  }
]
```

**Mode prop summary:**
- `showChoices=true` (default): shows 'Select uploaded CV' + 'Select generated CV' + upload section
- `showChoices=false`: shows upload-only mode (used from BaseCVsTable '+ Upload New CV' button)

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the two spec markdowns, back-to-back.
