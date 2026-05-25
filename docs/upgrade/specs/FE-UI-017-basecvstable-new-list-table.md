---
spec_id: FE-UI-017
title: "new BaseCVsTable — multi-CV data table with sorting and status badges"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cv-center
component_file: src/frontend/components/BaseCVsTable/BaseCVsTable.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No component exists to display multiple base CVs in a table. The /cv-center page currently supports only a single CV via a form/preview flow.
**Required behavior:** A new BaseCVsTable component renders a data table with merged columns (per gap-answer q6): File Name, Upload Date, Language, Last Updated, Status, Used In, Actions. The Actions column contains "Set as Default", "Delete", and "View" controls. The component follows the established list-table pattern: skeleton loading (3 rows), inline error + retry, empty state with visible headers and CTA, semantic `<table>` markup, client-side sorting on all columns (default: newest first by Last Updated), row hover highlight with View underline, responsive card layout on mobile, and Hebrew i18n. Status uses Badge component (FE-UI-001) with mapping: Ready (green/success), Processing (blue/info), Failed (red/destructive). "View" navigates to /cv-center/[cvId] (gap-answer q5).
**User impact:** Users gain a scannable, sortable overview of all uploaded base CVs with status visibility, quick actions (set default, delete, view), and a clear path to upload new CVs.

## Evidence
**Mockup files:** Base CVs View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/cv-center.json
**Gap answers source:** docs/upgrade/gap-answers/cv-center.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/BaseCVsTable/BaseCVsTable.tsx
**Page file(s):** src/frontend/app/cv-center/page.tsx (FE-UI-016)
**Tier:** feature — cascade risk: low (new component, no existing component to break)
**API dependencies:** GET /users/me/cv (File Name = full_name field rendered as display title; Language = language field; Last Updated = updated_at field; Status = status field if present, else default "Ready")
**Imports this component:** app/cv-center/page.tsx (FE-UI-016)

## Fix Plan
**Files to modify:**
- `src/frontend/components/BaseCVsTable/BaseCVsTable.tsx` — create new table component with 7 columns (File Name, Upload Date, Language, Last Updated, Status, Used In, Actions), semantic `<table>` markup, skeleton loading (3 rows), inline error + retry, empty state with CTA, row hover states, client-side sorting, responsive card layout, badge mapping (3 statuses with fallback), View/Set as Default/Delete actions
- `src/frontend/components/BaseCVsTable/index.ts` — barrel export
- i18n translation files — add Hebrew keys for: "File Name", "Upload Date", "Language", "Last Updated", "Status", "Used In", "Actions", "View", "Set as Default", "Delete", "Ready", "Processing", "Failed", "No primary CVs uploaded yet", "+ Upload New CV" (empty state CTA), error message text, retry button text

**Behavior changes:**
- New component renders a 7-column table: File Name, Upload Date, Language, Last Updated, Status, Used In, Actions
- File Name column displays `full_name` from GET /users/me/cv response (per contract verification: "Title derived from full_name field")
- Upload Date column displays the creation/upload timestamp
- Language column displays `language` field directly
- Last Updated column uses locale-aware formatting via `Intl.DateTimeFormat`
- Status badge mapping: Ready → Badge variant `success` (green), Processing → Badge variant `info` (blue), Failed → Badge variant `destructive` (red). If status field is absent from API response, default to "Ready"
- Used In column displays the count or list of applications using this base CV
- Actions column: "Set as Default" button, "Delete" button, "View" text link navigating to `/cv-center/[cvId]`
- Client-side sorting on all columns; default sort by Last Updated descending (most recent first)
- Rows use zebra striping: odd `bg-white`, even `bg-surface-subtle`
- Hover: row background highlight + "View" text underline
- Loading: 3 skeleton shimmer rows
- Error: inline message + Retry button inside table card
- Empty: table headers visible, centered "No primary CVs uploaded yet" text + "+ Upload New CV" CTA button
- Responsive (<768px): collapse to card layout, one card per CV

**Non-goals (explicitly out of scope):**
- Server-side pagination
- Inline editing of CVs from the table
- Bulk selection or bulk actions
- CV preview/modal from this table
- File upload handling (owned by ChooseBaseCVModal FE-UI-011)
- Actual delete confirmation modal (can use window.confirm or a simple modal — not specced here)
- Actual "Set as Default" API call implementation (button must render and call `onSetDefault(cvId)` prop)

**Rollback plan:** Remove component file and directory — no database or API changes

## Acceptance Criteria

### Visual — Table Structure
- [ ] AC-001: Given BaseCVsTable receives a populated `cvs` array, when rendered, then the markup uses semantic `<table>` with `<thead>`, `<th scope="col">`, `<tbody>`, `<tr>`, and `<td>` elements
- [ ] AC-002: Given BaseCVsTable renders, when data is present, then 7 columns are displayed in order: File Name, Upload Date, Language, Last Updated, Status, Used In, Actions
- [ ] AC-003: Given multiple CV rows, when rendered, then rows alternate between `bg-white` (odd) and `bg-surface-subtle` (even) backgrounds

### Visual — Data Mapping
- [ ] AC-004: Given a base CV object from GET /users/me/cv, when rendered, then the File Name column displays the `full_name` field value
- [ ] AC-005: Given a base CV object from GET /users/me/cv, when rendered, then the Upload Date column displays a locale-aware formatted date
- [ ] AC-006: Given a base CV object from GET /users/me/cv, when rendered, then the Language column displays the `language` field value
- [ ] AC-007: Given a base CV object from GET /users/me/cv, when rendered, then the Last Updated column displays a locale-aware formatted date using `Intl.DateTimeFormat`

### Visual — Badges
- [ ] AC-008: Given a base CV with status "ready" (or status field absent), when rendered, then the Badge displays with variant `success` (green) and label "Ready"
- [ ] AC-009: Given a base CV with status "processing", when rendered, then the Badge displays with variant `info` (blue)
- [ ] AC-010: Given a base CV with status "failed", when rendered, then the Badge displays with variant `destructive` (red)

### Visual — Actions Column
- [ ] AC-011: Given any CV row, when rendered, then the Actions column contains a "View" text element that is bold
- [ ] AC-012: Given any CV row, when rendered, then the Actions column contains a "Set as Default" actionable element
- [ ] AC-013: Given any CV row, when rendered, then the Actions column contains a "Delete" actionable element

### Interaction — Sorting
- [ ] AC-014: Given the table renders with data, when no user sort action has occurred, then rows are sorted by Last Updated descending (most recent first)
- [ ] AC-015: Given the user clicks any column header, when the column was unsorted, then rows sort ascending by that column and an ascending indicator is shown on the `<th>`
- [ ] AC-016: Given the user clicks the same column header again, when it was ascending, then sort toggles to descending
- [ ] AC-017: Given the user clicks a different column header, when another column was actively sorted, then the new column becomes the active sort column ascending and the previous column's indicator clears

### Interaction — Hover
- [ ] AC-018: Given any CV row, when the user hovers over the row, then the row background changes to a visible highlight color
- [ ] AC-019: Given any CV row, when the user hovers over the row, then the "View" text gains an underline decoration

### Interaction — Navigation
- [ ] AC-020: Given any CV row, when the user clicks "View", then navigation occurs to `/cv-center/[cvId]` where `cvId` is the CV's identifier

### Interaction — Actions
- [ ] AC-021: Given any CV row, when the user clicks "Set as Default", then the `onSetDefault` callback prop is called with the CV's identifier
- [ ] AC-022: Given any CV row, when the user clicks "Delete", then the `onDelete` callback prop is called with the CV's identifier

### States
- [ ] AC-023: Given `isLoading` is true, when rendered, then 3 skeleton placeholder rows with shimmer animation are shown (no real data rows)
- [ ] AC-024: Given `error` is truthy, when rendered, then an inline error message and a "Retry" button are shown inside the table card, and clicking Retry calls `onRetry`
- [ ] AC-025: Given `cvs` is an empty array and `isLoading` is false, when rendered, then table headers are visible with centered text "No primary CVs uploaded yet" and a "+ Upload New CV" CTA button below
- [ ] AC-026: Given the empty state is rendered, when the user clicks "+ Upload New CV" CTA, then the `onUploadNew` callback prop is called

### Responsive
- [ ] AC-027: Given viewport width < 768px, when rendered, then the table collapses to a vertical card layout with one card per CV showing all seven fields stacked

### Accessibility
- [ ] AC-028: Given the table is rendered, when inspected, then each `<th>` has `scope="col"` attribute
- [ ] AC-029: Given the user presses Enter or Space on a focused column header, then sorting toggles — equivalent to click
- [ ] AC-030: Given sort is active on a column, when inspected, then the `<th>` has `aria-sort` set to `"ascending"` or `"descending"`

### i18n
- [ ] AC-031: Given locale is `he`, when rendered, then column headers ("File Name", "Upload Date", "Language", "Last Updated", "Status", "Used In", "Actions"), action labels ("View", "Set as Default", "Delete"), badge labels ("Ready", "Processing", "Failed"), empty state text, error text, and retry text all render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | cvs array populated, no loading/error | Render data rows with zebra striping |
| loading | `isLoading` prop true | 3 skeleton shimmer rows |
| error | `error` prop truthy | Inline error message + Retry button |
| empty | cvs array empty, not loading | Table headers + "No primary CVs uploaded yet" with CTA |
| hover | mouse over row | Row highlight + View underline |
| focus | keyboard focus on column header | Visible focus ring, Enter/Space toggles sort |

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
| AC-013 | unit | pre_merge | false |
| AC-014 | unit | pre_merge | false |
| AC-015 | unit | pre_merge | false |
| AC-016 | unit | pre_merge | false |
| AC-017 | unit | pre_merge | false |
| AC-018 | unit | pre_merge | false |
| AC-019 | unit | pre_merge | false |
| AC-020 | unit | pre_merge | false |
| AC-021 | unit | pre_merge | false |
| AC-022 | unit | pre_merge | false |
| AC-023 | unit | pre_merge | false |
| AC-024 | unit | pre_merge | false |
| AC-025 | unit | pre_merge | false |
| AC-026 | unit | pre_merge | false |
| AC-027 | unit | pre_merge | false |
| AC-028 | unit | pre_merge | false |
| AC-029 | unit | pre_merge | false |
| AC-030 | unit | pre_merge | false |
| AC-031 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on any existing route
- Existing test suite (tests/ui/unit/BaseCVsTable.test.tsx) passes or is updated to match new component interface
- CVForm and CVPreview accessible at /cv-center/[cvId] (not deleted, moved — verified by FE-UI-016)

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-025 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-026 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-027 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-028 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-029 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-030 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |
| AC-031 | src/frontend/components/BaseCVsTable/BaseCVsTable.tsx:TBD | tests/ui/unit/BaseCVsTable.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove component file, re-open spec |
| RT-002 | New non-2xx response on GET /users/me/cv | Block deploy, investigate API contract |

## Design Notes
- **Status field conflict (MUST RESOLVE BEFORE IMPLEMENTATION):** Contract verification says status is "derived client-side as constant 'Ready'" — no backend field exists. Gap-answer q13 says the backend includes (or will include) a `status` field. AC-008 is written to handle both cases: if the `status` field is present in the API response, use its value for badge mapping; if absent, default to "Ready". Developer must confirm with backend team which is correct before implementation. If backend confirms no status field, remove Processing and Failed badge ACs (AC-009, AC-010) from the test suite.
- **Column merge (gap-answer q6):** The merged column set (File Name, Upload Date, Language, Last Updated, Status, Used In, Actions) combines both the mockup screenshot columns and the diff-analysis columns. "Used In" shows how many applications reference this base CV — if the API does not return this field, render as "—" and flag for backend.
- **Upload Date vs Last Updated:** Two date columns — Upload Date is the creation timestamp (when the CV was first uploaded), Last Updated is the modification timestamp. If the API only returns `updated_at`, use it for Last Updated and leave Upload Date as the CV creation date (or `updated_at` if no separate field exists).
- **"Set as Default" action:** The callback prop `onSetDefault(cvId)` is called — the parent page (FE-UI-016) owns the API call. No default indicator badge is specced in the mockup; if needed later, it would be a separate spec amendment.
- **"Delete" action:** The callback prop `onDelete(cvId)` is called — the parent page (FE-UI-016) owns confirmation and the API call. This spec only requires the button to exist and call the prop.
- **View navigation target:** `/cv-center/[cvId]` — this route must be created as part of the CVForm/CVPreview relocation (gap-answer q18). If the route does not exist at implementation time, the View link will 404 — this is expected and will be resolved by the detail route spec.
- **Existing test file:** `tests/ui/unit/BaseCVsTable.test.tsx` already exists in the repo. It must be updated to match the new component interface defined in this spec.
- **Badge component dependency:** Status badges use the Badge component from FE-UI-001 (Batch A). If FE-UI-001 is not yet implemented, use inline styled `<span>` elements matching the same color tokens as a temporary measure.
