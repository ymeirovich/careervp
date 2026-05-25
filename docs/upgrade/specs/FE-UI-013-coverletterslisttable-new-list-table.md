---
spec_id: FE-UI-013
title: "CoverLettersListTable — new list table"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cover-letters
component_file: src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No component exists to display all cover letters in a consolidated table. Users must navigate into each individual application to access its cover letter.
**Required behavior:** A new CoverLettersListTable component renders a table with columns: Company, Job Title, Date, Status, Action (View link). The component follows the established list-page pattern: skeleton loading (3 rows), inline error + retry, empty state with visible headers, zebra striping, semantic `<table>` markup, client-side sort on all columns, search input above the table, card-stack on mobile, row hover highlight with View underline, and Hebrew i18n. Status badges use the existing artifact status pattern: Ready (green), Processing (blue), Failed (red).
**User impact:** Users gain a scannable, sortable, searchable overview of all cover letters across applications.

## Evidence
**Mockup files:** Cover Letters View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/cover-letters.json
**Gap answers source:** docs/upgrade/gap-answers/cover-letters.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx
**Page file(s):** src/frontend/app/cover-letters/page.tsx
**Tier:** feature — cascade risk: low (new component, no existing component to break)
**API dependencies:** GET /cover-letters (company_name and job_title are top-level fields — no extra fetch needed)
**Imports this component:** app/cover-letters/page.tsx (FE-UI-012)

## Fix Plan
**Files to modify:**
- `src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx` — create new table component with columns (Company, Job Title, Date, Status, Action), semantic `<table>` markup, skeleton loading, inline error + retry, empty state, zebra striping, hover states, client-side sorting, search input, responsive card layout, badge mapping, View link
- i18n translation files — add Hebrew keys for: "Company", "Job Title", "Date", "Status", "Action", "View", "Ready", "Processing", "Failed", "No cover letters yet", "No matching cover letters", error message text, retry button text, search placeholder

**Behavior changes:**
- New component renders a 5-column table (Company, Job Title, Date, Status, Action)
- Status badge mapping: Ready → Badge variant `success` (green), Processing → Badge variant `info` (blue), Failed → Badge variant `destructive` (red)
- "View" action is a text link (bold, underline on hover) navigating to `/applications/[applicationId]/cover-letter`
- Date column uses locale-aware formatting via `Intl.DateTimeFormat`
- Client-side sorting on all 5 columns; default sort by Date descending (most recent first)
- Search input filters by Company and Job Title (case-insensitive)
- Rows alternate `bg-white` (odd) / `bg-surface-subtle` (even)
- Hover: row background highlight + "View" text underline
- Loading: 3 skeleton shimmer rows
- Error: inline message + Retry button inside table card
- Empty: table headers visible, centered "No cover letters yet" text
- Responsive (<768px): collapse to card layout, one card per cover letter

**Non-goals (explicitly out of scope):**
- Server-side pagination
- Inline editing of cover letters
- Bulk actions or selection
- Cover letter preview/modal from this table

**Rollback plan:** Remove component file — no database or API changes

## Acceptance Criteria

### Visual — Table Structure
- [ ] AC-001: Given CoverLettersListTable receives a populated `coverLetters` array, when rendered, then the markup uses semantic `<table>` with `<thead>`, `<th scope="col">`, `<tbody>`, `<tr>`, and `<td>` elements
- [ ] AC-002: Given CoverLettersListTable renders, when data is present, then 5 columns are displayed in order: Company, Job Title, Date, Status, Action
- [ ] AC-003: Given multiple cover letter rows, when rendered, then rows alternate between `bg-white` (odd) and `bg-surface-subtle` (even) backgrounds

### Visual — Badges
- [ ] AC-004: Given a cover letter with status "ready", when rendered, then the Badge displays with variant `success` (green)
- [ ] AC-005: Given a cover letter with status "processing", when rendered, then the Badge displays with variant `info` (blue)
- [ ] AC-006: Given a cover letter with status "failed", when rendered, then the Badge displays with variant `destructive` (red)

### Visual — View Action
- [ ] AC-007: Given any cover letter row, when rendered, then the "View" action is a bold text element (not a ghost Button component)

### Interaction — Sorting
- [ ] AC-008: Given the table renders with data, when no user sort action has occurred, then rows are sorted by Date descending (most recent first)
- [ ] AC-009: Given the user clicks any column header, when the column was unsorted, then rows sort ascending by that column and an ascending indicator is shown on the `<th>`
- [ ] AC-010: Given the user clicks the same column header again, when it was ascending, then sort toggles to descending
- [ ] AC-011: Given the user clicks a different column header, when another column was actively sorted, then the new column becomes the active sort column ascending and the previous column's indicator clears

### Interaction — Search
- [ ] AC-012: Given the user types "acme" in the search input, when there are cover letters with Company or Job Title containing "acme" (case-insensitive), then only matching rows are displayed
- [ ] AC-013: Given the search input is non-empty, when no cover letters match the filter, then the table displays "No matching cover letters" (not the primary empty state)

### Interaction — Hover
- [ ] AC-014: Given any cover letter row, when the user hovers over the row, then the row background changes to a visible highlight color
- [ ] AC-015: Given any cover letter row, when the user hovers over the row, then the "View" text gains an underline decoration

### Interaction — Navigation
- [ ] AC-016: Given any cover letter row, when the user clicks "View", then navigation occurs to `/applications/[applicationId]/cover-letter`

### States
- [ ] AC-017: Given `isLoading` is true, when rendered, then 3 skeleton placeholder rows with shimmer animation are shown (no real data rows)
- [ ] AC-018: Given `error` is truthy, when rendered, then an inline error message and a "Retry" button are shown inside the table card, and clicking Retry calls `onRetry`
- [ ] AC-019: Given `coverLetters` is an empty array and `isLoading` is false, when rendered, then table headers are visible with centered "No cover letters yet" text

### Responsive
- [ ] AC-020: Given viewport width < 768px, when rendered, then the table collapses to a vertical card layout with one card per cover letter showing all five fields stacked

### Accessibility
- [ ] AC-021: Given the table is rendered, when inspected, then each `<th>` has `scope="col"` attribute
- [ ] AC-022: Given the user presses Enter or Space on a focused column header, then sorting toggles — equivalent to click
- [ ] AC-023: Given sort is active on a column, when inspected, then the `<th>` has `aria-sort` set to `"ascending"` or `"descending"`

### i18n
- [ ] AC-024: Given locale is `he`, when rendered, then column headers ("Company", "Job Title", "Date", "Status", "Action"), "View" text, badge labels ("Ready", "Processing", "Failed"), empty state text, error text, retry text, and search placeholder all render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | coverLetters array populated, no loading/error | Render data rows with zebra striping |
| loading | `isLoading` prop true | 3 skeleton shimmer rows |
| error | `error` prop truthy | Inline error message + Retry button |
| empty | coverLetters array empty, not loading | Table headers + "No cover letters yet" |
| empty-search | search yields 0 results | "No matching cover letters" message |
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

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on any existing route
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx:TBD | tests/ui/unit/CoverLettersListTable.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove component file, re-open spec |

## Design Notes
- **View navigation target:** `/applications/[applicationId]/cover-letter` — this route already exists. The `applicationId` comes from the cover letter object returned by GET /cover-letters (per gap-answer q8).
- **company_name and job_title** are top-level fields in the GET /cover-letters response — no secondary fetch or join is needed (per gap-answer q15).
- **Search scope:** filters across both Company and Job Title columns simultaneously for maximum usability.
- **Sort default:** Date descending (most recent first), consistent with the established pattern in FE-UI-008.
