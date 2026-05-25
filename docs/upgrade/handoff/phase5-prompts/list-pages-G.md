# Phase 5 — Batch G: List Pages
# Components: CoverLettersPage (new), CoverLettersListTable (new),
#             TailoredCVsPage (new), TailoredCVsListTable (new)
# Model: Opus | New conversation per batch
# Note: All 4 are new components following the exact same list-page pattern.
#       Batch together — Opus will recognize the pattern and maintain consistency across all 4 specs.

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.
EFFICIENCY NOTE: All 4 components follow the established list-page pattern (skeleton loading, inline error + retry, empty state with CTA, zebra striping, semantic table, client-side sort + search, card-stack on mobile, Hebrew i18n, 'View' link underline on hover). Apply this pattern consistently across all 4 specs without restating it in full for each — reference the pattern by name and call out only the per-component differences.

TASK: Write FOUR complete upgrade specs — CoverLettersPage, CoverLettersListTable, TailoredCVsPage, TailoredCVsListTable.

THINK before writing each spec:
1. What is unique about this component vs the established list-page pattern?
2. What data fields does its table show, and where do they come from?
3. What status states exist and what Badge colors map to each?
4. What is the empty state message and CTA?
5. Where does 'View' navigate?
6. What new i18n strings are needed?

THEN produce ALL FOUR specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "{COMPONENT_NAME} — new list page"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cover-letters | /tailored-cvs
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** (route does not exist / no component exists)
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Cover Letters View page.png | Tailored CVs View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/cover-letters.json | tailored-cvs.json
**Gap answers source:** docs/upgrade/gap-answers/cover-letters.json | tailored-cvs.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {route page that renders this component}
**Tier:** feature — cascade risk: low (new routes, no existing component to break)
**API dependencies:** {list endpoints}
**Imports this component:** {page file}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Remove route file — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Apply the established list-page pattern plus component-specific ACs.

## States to Handle
default | loading | error | empty | hover | focus

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on any existing route
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove route, re-open spec |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output all four specs back-to-back with no prose between them.

---

## CROSS-CUTTING PATTERN (applies to all 4 components)

These decisions are already established across all prior routes and apply without exception:

| Pattern | Decision | Source |
|---|---|---|
| Loading state | Skeleton rows (3 placeholder rows with shimmer) | /dashboard q1, /cv-center q1 |
| Error state | Inline error message inside the table card with a Retry button | /dashboard q2, all routes |
| Hover state | Row background highlight + 'View' text becomes underlined | /applications q4 |
| Zebra striping | Alternate white and very light gray/cream | /applications q5 |
| Responsive | Stack into card layout (one card per row) on mobile | /dashboard q10 |
| Sorting | Client-side sorting on all columns | /applications q10 |
| Search | Search input above the table for filtering | /applications q11 |
| Accessibility | Semantic `<table>/<thead>/<th>/<tbody>/<tr>/<td>` | /applications q7 |
| i18n | Yes — Hebrew translations for all new strings | every route |
| ErrorBoundary | Uncaught JS exceptions only — API errors handled inline | shared-components.json |
| Spinner | Not used for data loading — skeletons only | shared-components.json |
| AppSidebar | Already specced in Batch B — no re-spec needed here | applications-hub Batch B |
| AppHeader | Already specced in Batch B — no re-spec needed here | applications-hub Batch B |
| Badge variants | Already specced in Batch A — soft prop available | applications-hub Batch A |

---

## CONTEXT

### Component 1: CoverLettersPage
File: app/cover-letters/page.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23
Route: /cover-letters (new route)

**No contract verification entry** — new component, no blocked items.

**Diff analysis (cover-letters new_components_needed):**
```
"CoverLettersPage — top-level page at /cover-letters with header bar (title + credits + user dropdown)
and table card"
```

**Gap answers — cover-letters:**
```json
[
  {
    "question_id": "q10",
    "component": "CoverLettersPage",
    "topic": "edge_case",
    "answer": "Yes — implement the sidebar split as part of this ticket. Note: sidebar split (CV Center → Base CVs + Tailored CVs) is already specced in Batch B (AppSidebar). Reference that spec — do not duplicate here."
  },
  {
    "question_id": "q11",
    "component": "CoverLettersPage",
    "topic": "accessibility",
    "answer": "Yes — use <table>/<thead>/<th>/<tbody>/<tr>/<td> for full screen reader support"
  },
  {
    "question_id": "q12",
    "component": "CoverLettersPage",
    "topic": "i18n",
    "answer": "Yes — add Hebrew for: 'Cover Letters', 'All Cover Letters', 'Company', 'Job Title', 'Date', 'Status', 'Action', 'View', 'Ready', empty state text, error state text"
  },
  {
    "question_id": "q13",
    "component": "CoverLettersPage",
    "topic": "shared_component",
    "answer": "Same PageHeader component — reuse the existing PageHeader with credits already wired in, no new component needed"
  },
  {
    "question_id": "q14",
    "component": "CoverLettersPage",
    "topic": "shared_component",
    "answer": "Same UserMenu component — reuse the existing UserMenu, no changes needed for this page"
  }
]
```

---

### Component 2: CoverLettersListTable
File: components/CoverLettersListTable/CoverLettersListTable.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23
Route: /cover-letters

**Diff analysis (cover-letters new_components_needed):**
```
"CoverLettersListTable — table listing all cover letters across applications with columns:
Company, Job Title, Date, Status, Action (View link)"
```

**API contract:**
- Endpoint: GET /cover-letters
- company_name and job_title are top-level fields in each cover letter object (no extra fetch needed) — per gap-answers q15

**Gap answers — cover-letters:**
```json
[
  {"question_id": "q1", "component": "CoverLettersListTable", "topic": "loading_state", "answer": "Skeleton rows (3 placeholder rows with shimmer)"},
  {"question_id": "q2", "component": "CoverLettersListTable", "topic": "error_state", "answer": "Inline error message inside the table card with a Retry button"},
  {"question_id": "q3", "component": "CoverLettersListTable", "topic": "empty_state", "answer": "Table headers visible with centered 'No cover letters yet' text"},
  {"question_id": "q4", "component": "CoverLettersListTable", "topic": "hover_state", "answer": "Row background highlight + 'View' text becomes underlined"},
  {"question_id": "q5", "component": "CoverLettersListTable", "topic": "edge_case", "answer": "Yes — alternate between white and very light gray/cream"},
  {"question_id": "q6", "component": "CoverLettersListTable", "topic": "responsive", "answer": "Stack into card layout (one card per cover letter)"},
  {"question_id": "q7", "component": "CoverLettersListTable", "topic": "edge_case", "answer": "Client-side sorting on all columns + search input for filtering"},
  {"question_id": "q8", "component": "CoverLettersListTable", "topic": "edge_case", "answer": "View navigates to existing /applications/[id]/cover-letter route"},
  {"question_id": "q9", "component": "CoverLettersListTable", "topic": "edge_case", "answer": "Status states: Ready (green), Processing (blue), Failed (red) — matches existing artifact status pattern"}
]
```

---

### Component 3: TailoredCVsPage
File: app/tailored-cvs/page.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23
Route: /tailored-cvs (new route)

**Contract verification entry (/tailored-cvs AppSidebar):**
```json
{
  "route": "/tailored-cvs",
  "component": "AppSidebar",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Add 'Tailored CVs' nav item with active state styling (orange left border accent, bold text) — navigation structure change only; no backend data required",
  "in_scope": true
}
```
Note: AppSidebar is already specced in Batch B — the above confirms it applies here.
TailoredCVsPage itself has no contract verification entry (new component).

**Diff analysis (tailored-cvs new_components_needed):**
```
"TailoredCVsPage — top-level page at /tailored-cvs with header bar (title + credits + user dropdown)
and 'All Tailored CVs' table card"
```

**Gap answers — tailored-cvs:**
```json
[
  {
    "question_id": "q7",
    "component": "TailoredCVsPage",
    "topic": "sidebar_icon",
    "answer": "Document with pencil/edit icon (to distinguish from Base CVs)"
  }
]
```
All other page-level decisions (header component, UserMenu reuse, i18n) follow the same pattern as CoverLettersPage above.

---

### Component 4: TailoredCVsListTable
File: components/TailoredCVsListTable/TailoredCVsListTable.tsx (new)
Tier: feature
Change type: new
Today's date: 2026-05-23
Route: /tailored-cvs

**Diff analysis (tailored-cvs new_components_needed):**
```
"TailoredCVsListTable — table listing all tailored CVs across applications with columns:
Title, Language, Last Updated, Status, Action (View link)"
```

**API contract:**
- Endpoint: GET /cv-tailorings
- Title: original base CV filename with suffix (per gap-answers q1)
- Language: inherited from base CV record (per gap-answers q2)

**Gap answers — tailored-cvs (unique decisions):**
```json
[
  {
    "question_id": "q1",
    "component": "TailoredCVsListTable",
    "topic": "data_mapping",
    "answer": "Title = original base CV filename with suffix (from GET /cv-tailorings response)"
  },
  {
    "question_id": "q2",
    "component": "TailoredCVsListTable",
    "topic": "data_mapping",
    "answer": "Language = inherited from base CV record"
  },
  {
    "question_id": "q3",
    "component": "TailoredCVsListTable",
    "topic": "status_states",
    "answer": "Status states: Ready (green), Processing (blue), Failed (red), Edited (blue — reuse --state-processing #3B82F6)"
  },
  {
    "question_id": "q4",
    "component": "TailoredCVsListTable",
    "topic": "status_token",
    "answer": "Edited badge: reuse --state-processing (#3B82F6) blue — confirmed applies cross-route"
  },
  {
    "question_id": "q5",
    "component": "TailoredCVsListTable",
    "topic": "navigation",
    "answer": "View navigates to existing /applications/[id]/cv-tailored route"
  },
  {
    "question_id": "q6",
    "component": "TailoredCVsListTable",
    "topic": "empty_state",
    "answer": "'No tailored CVs yet. Create one from an application.' with link to /applications"
  },
  {
    "question_id": "q8",
    "component": "TailoredCVsListTable",
    "topic": "date_format",
    "answer": "Match existing table date format, locale-aware via Intl.DateTimeFormat"
  }
]
```

All other behaviors (loading, error, hover, zebra, responsive, sort, search, a11y, i18n) follow the cross-cutting pattern defined above.

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the four spec markdowns, back-to-back.
