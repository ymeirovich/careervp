# Phase 5 — Batch E: Dashboard Feature Tables
# Components: JobsTable (modify — covers both dashboard and applications modes), StatsRow (modify)
# Model: Opus | New conversation per batch
# Note: JobsTable serves BOTH /dashboard (widget mode) and /applications (full-list mode).
#       A single spec covers both by documenting a mode prop that switches behavior.

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — one for JobsTable (covering both dashboard and applications modes) and one for StatsRow — scoped to changes on /dashboard and /applications.

THINK before writing each spec:
1. What does the component currently do?
2. What visual changes are required? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks? JobsTable is used in two contexts — changes must not break either.

THEN produce BOTH specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "Upgrade {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /dashboard + /applications
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Dashboard View page.png, Applications View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json + docs/upgrade/diff-analysis/applications.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json + docs/upgrade/gap-answers/applications.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** feature — cascade risk: medium (used on two routes)
**API dependencies:** {list endpoints}
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for every visual change, gap answer, keyboard/ARIA, Hebrew i18n, responsive.

## States to Handle
default | loading | error | empty | hover | {others from gap answers}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on dashboard widget mode when applications full-list mode is added
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
- {unresolved ambiguities}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: JobsTable
File: components/dashboard/JobsTable.tsx
Tier: feature
Change type: modify (extends to cover full-list mode for /applications)
Today's date: 2026-05-23

**Architecture decision (applications gap-answers q13):**
```json
{
  "question_id": "q13",
  "answer": "Reuse the existing JobsTable component — extend it via new props (e.g., enableSorting, enableSearch, hideViewAll) rather than creating a separate ApplicationsJobsTable file."
}
```

**Contract verification entries:**
```json
[
  {
    "route": "/dashboard",
    "component": "JobsTable",
    "change_type": "modify",
    "backend_classification": "cosmetic",
    "resolution": "Visual-only changes: orange column header text color, new Badge style variants for Draft/Archived, 'View' rendered as bold text link instead of ghost button, alternating row backgrounds — GET /jobs already supplies all row data; no new backend fields required",
    "in_scope": true
  },
  {
    "route": "/applications",
    "component": "JobsTable",
    "change_type": "modify",
    "backend_classification": "yes",
    "resolution": "Full job list from GET /jobs — same endpoint used by dashboard widget; heading change to 'My Jobs', removal of 'View All' link, and orange column headers are client-side config changes only",
    "in_scope": true
  }
]
```

**Diff analysis entry — dashboard:**
```json
{
  "component": "JobsTable",
  "file": "components/dashboard/JobsTable.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Current has muted column headers. Screenshot shows column headers in orange/primary-action color. Badge styles differ: 'Active' is green with white text, 'Draft' is orange-outlined, 'Archived' is muted beige/olive. 'View' action is bold dark text (not ghost button).",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": ["hover", "loading", "empty", "error"],
  "backend_data_required": "none",
  "backend_available": "yes"
}
```

**Diff analysis entry — applications:**
```json
{
  "component": "JobsTable",
  "file": "components/dashboard/JobsTable.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Current component has 'Most Recent Jobs' heading with 'View All' link. Screenshot shows same table structure but with heading 'My Jobs', no 'View All' link, and displays the full job list. Column headers are orange. Badge variants differ (Draft has warm orange style, Archived has muted beige style). 'View' action is bold text, not ghost button. Rows have alternating background.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": ["hover", "loading", "error", "empty"],
  "backend_data_required": "GET /jobs — full list of jobs (same endpoint as dashboard)",
  "backend_available": "yes"
}
```

**Layout changes from diff analysis (applications):**
```json
[
  {
    "description": "Jobs table shows 5 columns: Job Title, Company, Status, Updated, Action — same columns as dashboard JobsTable but this is the full list view (no 'View All' link, no 'Most Recent Jobs' heading)",
    "change_type": "structure"
  },
  {
    "description": "Table rows alternate with subtle background banding — rows appear to alternate between white and very light gray/cream",
    "change_type": "spacing"
  },
  {
    "description": "Column headers use orange/primary-action colored text instead of the current muted gray",
    "change_type": "spacing"
  },
  {
    "description": "'View' action in the last column appears as bold dark text link rather than a ghost button",
    "change_type": "structure"
  }
]
```

**Gap answers — dashboard:**
```json
[
  {"question_id": "q1", "component": "JobsTable", "topic": "loading_state", "answer": "Skeleton rows (3 placeholder rows with shimmer)"},
  {"question_id": "q2", "component": "JobsTable", "topic": "error_state", "answer": "Inline error message inside the table card with a Retry button"},
  {"question_id": "q10", "component": "JobsTable", "topic": "responsive", "answer": "Stack into card layout (one card per job)"},
  {"question_id": "q14", "component": "JobsTable", "topic": "design_token", "answer": "#FED7AA (orange-200) — soft orange tint for Draft badge"},
  {"question_id": "q15", "component": "JobsTable", "topic": "design_token", "answer": "#D1D5DB (gray-300) — neutral gray muted state for Archived badge"},
  {"question_id": "q17", "component": "JobsTable", "topic": "design_token", "answer": "#6B7280 (gray-500) — standard neutral gray for column header text (NOT primary orange)"}
]
```

**Gap answers — applications (new props and behaviors):**
```json
[
  {"question_id": "q1", "component": "ApplicationsPage", "topic": "empty_state", "answer": "Table headers visible with centered 'No applications yet' text + prominent '+ New Application' CTA — match current JobsTable empty state"},
  {"question_id": "q2", "component": "ApplicationsPage", "topic": "edge_case", "answer": "Show all jobs (no pagination) — V1 users have max ~50 jobs, default sorted latest application first"},
  {"question_id": "q3", "component": "ApplicationsPage", "topic": "edge_case", "answer": "Yes, keep both headers — header label changes to 'Applications' to show route context, card shows 'My Jobs' section title"},
  {"question_id": "q4", "component": "ApplicationsJobsTable", "topic": "hover_state", "answer": "Row background highlight + 'View' text becomes underlined"},
  {"question_id": "q5", "component": "ApplicationsJobsTable", "topic": "edge_case", "answer": "Yes — alternate between white and a very light gray/cream"},
  {"question_id": "q7", "component": "ApplicationsPage", "topic": "accessibility", "answer": "Use semantic <table> with <thead>/<th>/<tbody>/<tr>/<td> for full accessibility"},
  {"question_id": "q8", "component": "ApplicationsPage", "topic": "i18n", "answer": "Yes — add Hebrew translations for all new strings on this page"},
  {"question_id": "q9", "component": "ApplicationsJobsTable", "topic": "edge_case", "answer": "Navigate to /applications/[id] — same as dashboard View"},
  {"question_id": "q10", "component": "ApplicationsJobsTable", "topic": "edge_case", "answer": "Yes — client-side sorting on all columns"},
  {"question_id": "q11", "component": "ApplicationsJobsTable", "topic": "edge_case", "answer": "Search input above the table for job title filtering"},
  {"question_id": "q16", "component": "ApplicationsJobsTable", "topic": "design_token", "answer": "Use --color-primary-action (#F97316) for column header text — confirmed for /applications; note: /dashboard uses gray-500 per q17 above"}
]
```

**Note on column header color discrepancy:**
Dashboard gap-answer q17 specifies gray-500 (#6B7280) for JobsTable column headers on /dashboard.
Applications gap-answer q16 specifies --color-primary-action (#F97316) for /applications.
This is a real discrepancy. The spec must flag this and let the mode prop control which color is applied: `headerColor` prop or derived from `mode` ("dashboard" | "full-list").

---

### Component 2: StatsRow
File: components/dashboard/StatsRow.tsx
Tier: feature
Change type: modify (very minor visual change)
Today's date: 2026-05-23

**Contract verification entry (/dashboard):**
```json
{
  "route": "/dashboard",
  "component": "StatsRow",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Minor visual adjustment (pill corner radius may increase slightly) — no backend data required",
  "in_scope": true
}
```

**Diff analysis entry (dashboard):**
```json
{
  "component": "StatsRow",
  "file": "components/dashboard/StatsRow.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Visually very similar to current. Minor: pill corners may be slightly rounder. Content format unchanged.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": [],
  "backend_data_required": "none",
  "backend_available": "yes"
}
```

**Gap answers — dashboard:**
```json
[
  {"question_id": "q3", "component": "StatsRow", "topic": "loading_state", "answer": "Skeleton placeholders matching pill shape"}
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
