---
spec_id: FE-UI-015
title: "TailoredCVsListTable — new list table"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /tailored-cvs
component_file: src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No component exists to display all tailored CVs in a consolidated table. Tailored CVs are only viewable within individual application contexts.
**Required behavior:** A new TailoredCVsListTable component renders a table with columns: Title, Language, Last Updated, Status, Action (View link). The component follows the established list-page pattern: skeleton loading (3 rows), inline error + retry, empty state with visible headers and CTA, zebra striping, semantic `<table>` markup, client-side sort on all columns, search input above the table, card-stack on mobile, row hover highlight with View underline, and Hebrew i18n. Status badges map: Ready (green), Processing (blue), Failed (red), Edited (blue — reuses `--state-processing` #3B82F6). The empty state includes a link to /applications.
**User impact:** Users gain a scannable, sortable, searchable overview of all tailored CVs across applications, with a fourth status ("Edited") that distinguishes manually-modified CVs.

## Evidence
**Mockup files:** Tailored CVs View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/tailored-cvs.json
**Gap answers source:** docs/upgrade/gap-answers/tailored-cvs.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx
**Page file(s):** src/frontend/app/tailored-cvs/page.tsx
**Tier:** feature — cascade risk: low (new component, no existing component to break)
**API dependencies:** GET /cv-tailorings (Title = base CV filename with suffix; Language = inherited from base CV record)
**Imports this component:** app/tailored-cvs/page.tsx (FE-UI-014)

## Fix Plan
**Files to modify:**
- `src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx` — create new table component with columns (Title, Language, Last Updated, Status, Action), semantic `<table>` markup, skeleton loading, inline error + retry, empty state with CTA link, zebra striping, hover states, client-side sorting, search input, responsive card layout, badge mapping (4 statuses), View link
- i18n translation files — add Hebrew keys for: "Title", "Language", "Last Updated", "Status", "Action", "View", "Ready", "Processing", "Failed", "Edited", "No tailored CVs yet. Create one from an application.", "No matching tailored CVs", error message text, retry button text, search placeholder

**Behavior changes:**
- New component renders a 5-column table (Title, Language, Last Updated, Status, Action)
- Title column displays the original base CV filename with suffix (from GET /cv-tailorings response, per gap-answer q1)
- Language column displays language inherited from the base CV record (per gap-answer q2)
- Last Updated column uses locale-aware formatting via `Intl.DateTimeFormat` (per gap-answer q8)
- Status badge mapping: Ready → Badge variant `success` (green), Processing → Badge variant `info` (blue / #3B82F6), Failed → Badge variant `destructive` (red), Edited → Badge variant `info` (blue / #3B82F6 — reuses `--state-processing` per gap-answer q4)
- "View" action is a text link (bold, underline on hover) navigating to `/applications/[applicationId]/cv-tailored`
- Client-side sorting on all 5 columns; default sort by Last Updated descending (most recent first)
- Search input filters by Title and Language (case-insensitive)
- Rows alternate `bg-white` (odd) / `bg-surface-subtle` (even)
- Hover: row background highlight + "View" text underline
- Loading: 3 skeleton shimmer rows
- Error: inline message + Retry button inside table card
- Empty: table headers visible, centered "No tailored CVs yet. Create one from an application." with "application" as a link to /applications
- Responsive (<768px): collapse to card layout, one card per tailored CV

**Non-goals (explicitly out of scope):**
- Server-side pagination
- Inline editing of tailored CVs
- Bulk actions or selection
- CV preview/modal from this table
- Base CV information beyond Title suffix and Language

**Rollback plan:** Remove component file — no database or API changes

## Acceptance Criteria

### Visual — Table Structure
- [ ] AC-001: Given TailoredCVsListTable receives a populated `tailoredCvs` array, when rendered, then the markup uses semantic `<table>` with `<thead>`, `<th scope="col">`, `<tbody>`, `<tr>`, and `<td>` elements
- [ ] AC-002: Given TailoredCVsListTable renders, when data is present, then 5 columns are displayed in order: Title, Language, Last Updated, Status, Action
- [ ] AC-003: Given multiple tailored CV rows, when rendered, then rows alternate between `bg-white` (odd) and `bg-surface-subtle` (even) backgrounds

### Visual — Data Mapping
- [ ] AC-004: Given a tailored CV object from GET /cv-tailorings, when rendered, then the Title column displays the base CV filename with suffix from the response
- [ ] AC-005: Given a tailored CV object from GET /cv-tailorings, when rendered, then the Language column displays the language value inherited from the base CV record
- [ ] AC-006: Given a tailored CV object, when rendered, then the Last Updated column displays a locale-aware formatted date using `Intl.DateTimeFormat`

### Visual — Badges
- [ ] AC-007: Given a tailored CV with status "ready", when rendered, then the Badge displays with variant `success` (green)
- [ ] AC-008: Given a tailored CV with status "processing", when rendered, then the Badge displays with variant `info` (blue, #3B82F6)
- [ ] AC-009: Given a tailored CV with status "failed", when rendered, then the Badge displays with variant `destructive` (red)
- [ ] AC-010: Given a tailored CV with status "edited", when rendered, then the Badge displays with variant `info` (blue, #3B82F6 — same color as Processing)

### Visual — View Action
- [ ] AC-011: Given any tailored CV row, when rendered, then the "View" action is a bold text element (not a ghost Button component)

### Interaction — Sorting
- [ ] AC-012: Given the table renders with data, when no user sort action has occurred, then rows are sorted by Last Updated descending (most recent first)
- [ ] AC-013: Given the user clicks any column header, when the column was unsorted, then rows sort ascending by that column and an ascending indicator is shown on the `<th>`
- [ ] AC-014: Given the user clicks the same column header again, when it was ascending, then sort toggles to descending
- [ ] AC-015: Given the user clicks a different column header, when another column was actively sorted, then the new column becomes the active sort column ascending and the previous column's indicator clears

### Interaction — Search
- [ ] AC-016: Given the user types a search term in the search input, when there are tailored CVs with Title or Language containing that term (case-insensitive), then only matching rows are displayed
- [ ] AC-017: Given the search input is non-empty, when no tailored CVs match the filter, then the table displays "No matching tailored CVs" (not the primary empty state)

### Interaction — Hover
- [ ] AC-018: Given any tailored CV row, when the user hovers over the row, then the row background changes to a visible highlight color
- [ ] AC-019: Given any tailored CV row, when the user hovers over the row, then the "View" text gains an underline decoration

### Interaction — Navigation
- [ ] AC-020: Given any tailored CV row, when the user clicks "View", then navigation occurs to `/applications/[applicationId]/cv-tailored`

### States
- [ ] AC-021: Given `isLoading` is true, when rendered, then 3 skeleton placeholder rows with shimmer animation are shown (no real data rows)
- [ ] AC-022: Given `error` is truthy, when rendered, then an inline error message and a "Retry" button are shown inside the table card, and clicking Retry calls `onRetry`
- [ ] AC-023: Given `tailoredCvs` is an empty array and `isLoading` is false, when rendered, then table headers are visible with centered text "No tailored CVs yet. Create one from an application." where "application" is a link navigating to /applications

### Responsive
- [ ] AC-024: Given viewport width < 768px, when rendered, then the table collapses to a vertical card layout with one card per tailored CV showing all five fields stacked

### Accessibility
- [ ] AC-025: Given the table is rendered, when inspected, then each `<th>` has `scope="col"` attribute
- [ ] AC-026: Given the user presses Enter or Space on a focused column header, then sorting toggles — equivalent to click
- [ ] AC-027: Given sort is active on a column, when inspected, then the `<th>` has `aria-sort` set to `"ascending"` or `"descending"`

### i18n
- [ ] AC-028: Given locale is `he`, when rendered, then column headers ("Title", "Language", "Last Updated", "Status", "Action"), "View" text, badge labels ("Ready", "Processing", "Failed", "Edited"), empty state text, error text, retry text, and search placeholder all render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | tailoredCvs array populated, no loading/error | Render data rows with zebra striping |
| loading | `isLoading` prop true | 3 skeleton shimmer rows |
| error | `error` prop truthy | Inline error message + Retry button |
| empty | tailoredCvs array empty, not loading | Table headers + "No tailored CVs yet..." with CTA link |
| empty-search | search yields 0 results | "No matching tailored CVs" message |
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

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on any existing route
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-025 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-026 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-027 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |
| AC-028 | src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx:TBD | tests/ui/unit/TailoredCVsListTable.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove component file, re-open spec |

## Design Notes
- **View navigation target:** `/applications/[applicationId]/cv-tailored` — this route already exists (per gap-answer q5).
- **Edited vs Processing badge color:** Both use `info` variant (blue, #3B82F6). They are distinguished by label text only ("Edited" vs "Processing"), not by color. This is a confirmed cross-route decision per gap-answer q3 and q4.
- **Title field:** The original base CV filename with a suffix — this is a single field from the GET /cv-tailorings response, not a computed join (per gap-answer q1).
- **Language field:** Inherited from the base CV record and included in the GET /cv-tailorings response — no secondary fetch needed (per gap-answer q2).
- **Empty state CTA:** "Create one from an application." with "application" linking to /applications. This differs from CoverLettersListTable (FE-UI-013) which has no CTA link in its empty state (per gap-answer q6).
- **Search scope:** filters across both Title and Language columns simultaneously.
- **Sort default:** Last Updated descending (most recent first), consistent with the established pattern.
