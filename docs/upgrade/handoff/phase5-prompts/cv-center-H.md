# Phase 5 — Batch H: CV Center
# Components: CVCenterContent (replace), BaseCVsTable (new)
# Model: Opus | New conversation per batch
# Route: /cv-center

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — one for CVCenterContent (full replace of existing single-CV editing flow with multi-CV table listing) and one for BaseCVsTable (new table component).

THINK before writing each spec:
1. What does the current component do? CVCenterContent is currently a single-CV form/preview/edit flow.
2. What is required? A full replacement with a list-table view and upload flow.
3. What gap answers resolve the ambiguities? (column merge, status source, CVForm relocation)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks? CVForm and CVPreview are moved, not deleted — confirm they are accessible at /cv-center/[cvId].

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "{replace/new} {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cv-center
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Base CVs View page.png, Base CV New Upload modal.png
**Diff analysis source:** docs/upgrade/diff-analysis/cv-center.json
**Gap answers source:** docs/upgrade/gap-answers/cv-center.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** feature — cascade risk: low (route-scoped replacement)
**API dependencies:** GET /users/me/cv
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert page.tsx to previous CVCenterContent — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

## States to Handle
default | loading | error | empty | hover | focus | upload-in-progress

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- CVForm and CVPreview accessible at /cv-center/[cvId] (not deleted, moved)
- No regression on any route that links to /cv-center
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert to previous CVCenterContent, re-open spec |
| RT-002 | New non-2xx response on GET /users/me/cv | Block deploy, investigate |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: CVCenterContent
File: app/cv-center/page.tsx
Tier: feature
Change type: replace (single-CV form → multi-CV table listing page)
Today's date: 2026-05-23

**Contract verification entry (/cv-center):**
```json
{
  "route": "/cv-center",
  "component": "CVCenterContent",
  "change_type": "replace",
  "backend_classification": "derived",
  "resolution": "GET /users/me/cv provides language and updated_at directly. Title derived from full_name field in the same response (render as display title for the row). Status derived client-side as constant 'Ready' — uploaded base CVs have no asynchronous processing pipeline and are immediately usable after upload; no polling or status field needed",
  "in_scope": true
}
```

**Note on contract vs gap answer conflict:**
Contract verification says status is "derived client-side as constant 'Ready'".
cv-center gap-answer q13 says "Backend field — the GET /users/me/cv response includes (or will include) a 'status' field".
Resolution: write AC that covers BOTH cases — if status field is present, use it; if absent, default to 'Ready'. Flag this in Design Notes for developer to confirm with backend.

**Diff analysis entry (cv-center):**
```json
{
  "component": "CVCenterContent",
  "file": "app/cv-center/page.tsx",
  "tier": "feature",
  "change_type": "replace",
  "visual_description": "Current single-CV view/edit/create flow (CVForm + CVPreview + TagInput) is entirely replaced by a multi-CV table listing. The current page renders form fields, preview cards with sections (experience, skills, achievements, languages), and inline editing. The screenshot shows a simple data table with 5 columns.",
  "interaction_states_visible": ["base table state with 2 CVs listed", "View action link"],
  "interaction_states_needed_but_not_shown": ["loading state", "error state", "empty state (0 CVs)", "hover on row", "hover on View link"],
  "backend_data_required": "GET /users/me/cv must return a list with fields: title/filename, language, updated_at, status.",
  "backend_available": "partial — GET /users/me/cv exists but may not return 'status' or filename-style 'title' fields"
}
```

**Diff analysis layout changes:**
```json
[
  {
    "description": "Current page is a single-CV view/edit/create flow with form fields and preview cards. Screenshot shows a multi-CV table listing with Title, Language, Last Updated, Status, and Action columns inside a card container.",
    "affects_component": "CVCenterContent",
    "change_type": "replace"
  },
  {
    "description": "Page header changes from 'CV Center' with Edit CV button to 'Base CVs' as page header bar text (matching sidebar item name).",
    "affects_component": "CVCenterContent",
    "change_type": "structure"
  },
  {
    "description": "Card header row shows 'All Base CVs' title on left and '+ Upload New CV' orange button on right.",
    "affects_component": "unknown",
    "change_type": "addition"
  }
]
```

**Gap answers — cv-center:**
```json
[
  {
    "question_id": "q6",
    "component": "BaseCVsTable",
    "topic": "edge_case",
    "answer": "Merge both — show all columns from spec and screenshot: File Name, Upload Date, Language, Last Updated, Status, Used In, Actions (Set as Default / Delete / View)"
  },
  {
    "question_id": "q16",
    "component": "AppSidebar",
    "topic": "edge_case",
    "answer": "Change sidebar nav label to 'Primary CVs' (not 'Base CVs' or 'CV Center') — note: this decision is owned by the AppSidebar spec (Batch B). CVCenterContent spec references this change but does not own it."
  },
  {
    "question_id": "q18",
    "component": "CVForm",
    "topic": "edge_case",
    "answer": "Move CVForm + CVPreview to /cv-center/[cvId] detail route — accessible via the table's 'View' action. NOT deleted."
  }
]
```

---

### Component 2: BaseCVsTable
File: components/BaseCVsTable/BaseCVsTable.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23

**No contract verification entry** — new component. Data from GET /users/me/cv (verified above).

**Diff analysis (cv-center new_components_needed):**
```
"BaseCVsTable — data table displaying all uploaded base CVs with columns: Title, Language,
Last Updated, Status, Action"
```

**Gap answers — cv-center:**
```json
[
  {"question_id": "q1", "component": "BaseCVsTable", "topic": "loading_state", "answer": "Skeleton rows (3 placeholder rows with shimmer)"},
  {"question_id": "q2", "component": "BaseCVsTable", "topic": "error_state", "answer": "Inline error message inside the table card with a Retry button"},
  {"question_id": "q3", "component": "BaseCVsTable", "topic": "empty_state", "answer": "Table headers visible with centered 'No primary CVs uploaded yet' text + '+ Upload New CV' CTA"},
  {"question_id": "q4", "component": "BaseCVsTable", "topic": "hover_state", "answer": "Row background highlight + 'View' text becomes underlined"},
  {"question_id": "q5", "component": "BaseCVsTable", "topic": "edge_case", "answer": "View navigates to /cv-center/[cvId]"},
  {
    "question_id": "q6",
    "component": "BaseCVsTable",
    "topic": "edge_case",
    "answer": "Merge both column sets: File Name, Upload Date, Language, Last Updated, Status, Used In, Actions (Set as Default / Delete) + View link"
  },
  {
    "question_id": "q7",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Upload-only modal (showChoices=false) opened from '+ Upload New CV' button — ChooseBaseCVModal is specced separately in Batch F"
  },
  {"question_id": "q8", "component": "BaseCVsTable", "topic": "responsive", "answer": "Stack into card layout (one card per CV)"},
  {"question_id": "q9", "component": "StatusBadge", "topic": "edge_case", "answer": "Status states: Ready (green), Processing (blue), Failed (red) — use Badge component from Batch A"},
  {"question_id": "q10", "component": "BaseCVsTable", "topic": "edge_case", "answer": "Yes — client-side sorting on all columns, default: newest first"},
  {"question_id": "q11", "component": "BaseCVsTable", "topic": "accessibility", "answer": "Yes — semantic <table> with <thead>/<th>/<tbody>/<tr>/<td>"},
  {
    "question_id": "q12",
    "component": "BaseCVsTable",
    "topic": "i18n",
    "answer": "Yes — Hebrew translations for: 'All Base CVs', '+ Upload New CV', 'Title', 'Language', 'Last Updated', 'Status', 'Action', 'View', 'Ready', 'Choose Base CV', 'Select uploaded CV', 'Select generated CV', 'Upload New CV', 'Upload', 'Cancel', empty/error states"
  },
  {
    "question_id": "q13",
    "component": "BaseCVsTable",
    "topic": "edge_case",
    "answer": "Status field: backend field from GET /users/me/cv — write AC with fallback to 'Ready' if field absent, flag in Design Notes"
  },
  {
    "question_id": "q14",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Separate data model — generated CVs are a distinct type from uploaded base CVs"
  },
  {
    "question_id": "q15",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Match existing disabled button pattern — no new variant"
  },
  {
    "question_id": "q17",
    "component": "ChooseBaseCVModal",
    "topic": "edge_case",
    "answer": "Yes — add X close icon in top-right corner of upload modal"
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
