---
spec_id: FE-UI-008
title: "Upgrade JobsTable — dual-mode (dashboard widget + applications full-list)"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /dashboard + /applications
component_file: src/frontend/components/dashboard/JobsTable.tsx
tier: feature
---

## Problem Statement
**Current behavior:** JobsTable renders a single "Most Recent Jobs" widget with a "View All" link, muted gray column headers, a ghost-button "View" action, uniform `neutral` Badge variant for both Draft and Archived statuses, and no alternating row backgrounds. The /applications page redirects to /dashboard — there is no full-list view. The component has no loading, error, hover, sorting, or search states.
**Required behavior:** JobsTable accepts a `mode` prop (`"dashboard"` | `"full-list"`). In dashboard mode, it retains the "Most Recent Jobs" heading and "View All" link but adopts updated badge styles (Draft → `soft` orange-tinted, Archived → `soft` muted-gray), bold text-link "View" action, and alternating row backgrounds. In full-list mode (/applications), the heading becomes "My Jobs", the "View All" link is hidden, column headers use `--color-primary-action` orange text, client-side sorting on all columns is enabled, a search input filters by job title, and the full job list is displayed. Both modes share loading (skeleton rows), error (inline retry), empty, hover (row highlight + "View" underline), responsive (card stack on mobile), and accessibility (semantic `<table>`) behaviors.
**User impact:** Users gain a dedicated full-list view at /applications with sorting and search, while the dashboard widget gets visual polish — without duplicating the component.

## Evidence
**Mockup files:** Dashboard View page.png, Applications View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json + docs/upgrade/diff-analysis/applications.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json + docs/upgrade/gap-answers/applications.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/dashboard/JobsTable.tsx
**Page file(s):** src/frontend/app/dashboard/page.tsx, src/frontend/app/applications/page.tsx
**Tier:** feature — cascade risk: medium (used on two routes)
**API dependencies:** GET /jobs (returns full job list; dashboard slices to recent N client-side)
**Imports this component:** app/dashboard/page.tsx, app/applications/page.tsx (new consumer)

## Fix Plan
**Files to modify:**
- `src/frontend/components/dashboard/JobsTable.tsx` — add `mode` prop, badge variant mapping, semantic `<table>`, alternating rows, bold text-link View, loading/error/empty/hover states, column header color per mode, client-side sorting, search input (full-list only), responsive card layout, ARIA attributes
- `src/frontend/app/applications/page.tsx` — replace redirect with actual page rendering JobsTable in `full-list` mode with "My Jobs" heading
- `src/frontend/app/dashboard/page.tsx` — pass `mode="dashboard"` to JobsTable (explicit, even if default)
- i18n translation files — add Hebrew keys for "My Jobs", "No applications yet", column headers, sort labels, search placeholder, error/retry text

**Behavior changes:**
- Badge variant for Draft changes from `neutral` to a new soft orange-tinted variant (depends on FE-UI-001 `soft` prop with `warning` variant, or a dedicated `draft` variant rendering `bg-[#FED7AA] text-[#9A3412]`)
- Badge variant for Archived changes from `neutral` to a muted gray variant (`bg-[#D1D5DB] text-[#374151]` or `soft` + `neutral`)
- "View" action changes from `<Button variant="ghost">` to `<button>` / `<a>` styled as bold dark text link
- Column header text color is mode-dependent: `text-text-muted` (#6B7280 gray-500) on dashboard, `text-primary-action` (#F97316) on full-list
- Rows gain alternating `bg-white` / `bg-surface-subtle` backgrounds
- Hover state: row background highlight + "View" text underline
- Markup migrates from `<div>` grid to semantic `<table>/<thead>/<th>/<tbody>/<tr>/<td>`
- Loading state: 3 skeleton shimmer rows
- Error state: inline message + Retry button inside table card
- Empty state (full-list): table headers visible, centered "No applications yet" + "+ New Application" CTA
- Responsive (<768px): table collapses to stacked card layout (one card per job)
- Full-list mode adds: search input above table (filters by job title), clickable column headers for client-side sorting (all 5 columns), full job list (no truncation)

**Non-goals (explicitly out of scope):**
- Server-side pagination (V1 max ~50 jobs — all rendered client-side)
- New API endpoints or backend changes (GET /jobs already returns all required fields)
- Drag-and-drop row reordering
- Bulk selection or batch actions
- Column visibility toggles

**Rollback plan:** Revert component file to prior version — no database or API changes. Applications page reverts to redirect.

## Acceptance Criteria

### Visual — Both Modes
- [ ] AC-001: Given JobsTable renders in any mode, when the component mounts, then the markup uses semantic `<table>` with `<thead>`, `<th scope="col">`, `<tbody>`, `<tr>`, and `<td>` elements
- [ ] AC-002: Given a job with status "draft", when rendered, then the Badge displays with background color `#FED7AA` (orange-200) and dark text — visually distinct from Active and Archived
- [ ] AC-003: Given a job with status "archived", when rendered, then the Badge displays with background color `#D1D5DB` (gray-300) and dark text — visually distinct from Active and Draft
- [ ] AC-004: Given a job with status "active", when rendered, then the Badge renders with variant `success` (green background, white text) — unchanged from current
- [ ] AC-005: Given any job row, when rendered, then the "View" action is a bold (`font-bold`) text element (not a ghost Button component), and clicking it calls `onViewJob(jobId)`
- [ ] AC-006: Given multiple job rows, when rendered, then rows alternate between `bg-white` (odd) and `bg-surface-subtle` (even) backgrounds
- [ ] AC-007: Given viewport width < 768px, when rendered, then the table collapses to a vertical card layout with one card per job showing all five fields stacked

### Visual — Dashboard Mode
- [ ] AC-008: Given `mode="dashboard"`, when rendered, then column header text uses color `#6B7280` (gray-500 / `text-text-muted`)
- [ ] AC-009: Given `mode="dashboard"`, when rendered, then the heading reads "Most Recent Jobs" and a "View All" link is visible
- [ ] AC-010: Given `mode="dashboard"`, when rendered, then no search input is present above the table
- [ ] AC-011: Given `mode="dashboard"`, when rendered, then column headers are not clickable and no sort indicators are displayed

### Visual — Full-List Mode
- [ ] AC-012: Given `mode="full-list"`, when rendered, then column header text uses color `#F97316` (`--color-primary-action` / `text-primary-action`)
- [ ] AC-013: Given `mode="full-list"`, when rendered, then the heading reads "My Jobs" and no "View All" link is present
- [ ] AC-014: Given `mode="full-list"`, when rendered, then a search input is rendered above the table with a placeholder indicating job title filtering
- [ ] AC-015: Given `mode="full-list"`, when rendered, then all five column headers are clickable and display a sort direction indicator on the active sort column
- [ ] AC-016: Given `mode="full-list"` and the "+ New Application" button, when clicked, then `onNewApplication` callback fires

### Interaction — Sorting (Full-List Only)
- [ ] AC-017: Given `mode="full-list"` and the user clicks the "Job Title" column header, when the column was unsorted, then rows sort alphabetically ascending by job title and an ascending indicator is shown
- [ ] AC-018: Given `mode="full-list"` and the user clicks the same column header again, when it was ascending, then sort toggles to descending
- [ ] AC-019: Given `mode="full-list"` and the user clicks a different column header, when another column was actively sorted, then the new column becomes the active sort column ascending and the previous column's indicator clears

### Interaction — Search (Full-List Only)
- [ ] AC-020: Given `mode="full-list"` and the user types "eng" in the search input, when there are jobs with titles containing "eng" (case-insensitive), then only matching rows are displayed
- [ ] AC-021: Given `mode="full-list"` and the search input is non-empty, when no jobs match the filter, then the empty state displays "No matching jobs" (not the "No applications yet" empty state)

### Interaction — Hover
- [ ] AC-022: Given any job row in any mode, when the user hovers over the row, then the row background changes to a visible highlight color
- [ ] AC-023: Given any job row in any mode, when the user hovers over the row, then the "View" text gains an underline decoration

### States
- [ ] AC-024: Given `isLoading` is true, when rendered, then 3 skeleton placeholder rows with shimmer animation are shown (no real data rows)
- [ ] AC-025: Given `error` is truthy, when rendered, then an inline error message and a "Retry" button are shown inside the table card, and clicking Retry calls `onRetry`
- [ ] AC-026: Given `jobs` is an empty array and `isLoading` is false, when `mode="full-list"`, then table headers are visible with centered "No applications yet" text and a prominent "+ New Application" CTA button
- [ ] AC-027: Given `jobs` is an empty array and `isLoading` is false, when `mode="dashboard"`, then table headers are visible with centered "No applications yet. Click + New Application to get started." text

### Accessibility
- [ ] AC-028: Given the table is rendered, when inspected, then each `<th>` has `scope="col"` attribute
- [ ] AC-029: Given `mode="full-list"` and the user presses Enter or Space on a focused column header, then sorting toggles — equivalent to click
- [ ] AC-030: Given sort is active on a column, when inspected, then the `<th>` has `aria-sort` set to `"ascending"` or `"descending"`

### i18n
- [ ] AC-031: Given locale is `he`, when rendered in dashboard mode, then "Most Recent Jobs", "View All", column headers, empty state text, and "View" action render in Hebrew
- [ ] AC-032: Given locale is `he`, when rendered in full-list mode, then "My Jobs", column headers, search placeholder, sort labels, empty state text, and "View" action render in Hebrew

### Navigation
- [ ] AC-033: Given any job row, when the user clicks "View", then navigation occurs to `/applications/[jobId]`

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | jobs array populated, no loading/error | Render data rows |
| loading | `isLoading` prop true | 3 skeleton shimmer rows |
| error | `error` prop truthy | Inline error message + Retry button |
| empty | jobs array empty, not loading | "No applications yet" + CTA |
| empty-search | full-list mode, search yields 0 results | "No matching jobs" message |
| hover | mouse over row | Row highlight + View underline |

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
| AC-032 | unit | pre_merge | false |
| AC-033 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on dashboard widget mode when full-list mode props are added — dashboard must render identically to current behavior (minus the intentional visual changes in this spec)
- Existing test suite passes without modification (tests that assert ghost Button for "View" will need updating as part of this spec's implementation)
- /applications/[id] sub-routes (vpr, cover-letter, etc.) continue to function — only /applications root page changes

**allowed_deltas:**
- Badge visual appearance for Draft and Archived statuses changes intentionally
- "View" action element type changes from Button to text link
- Column header color may change per mode
- Row backgrounds gain alternating stripes

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-025 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-026 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-027 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-028 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-029 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-030 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-031 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-032 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |
| AC-033 | src/frontend/components/dashboard/JobsTable.tsx:TBD | tests/ui/unit/JobsTable.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert JobsTable.tsx + applications/page.tsx, re-open spec to in_progress |
| RT-002 | Dashboard page renders incorrectly after JobsTable upgrade | Revert JobsTable.tsx, verify dashboard page.tsx still passes mode="dashboard" |
| RT-003 | /applications/[id] sub-routes break after page.tsx change | Revert applications/page.tsx to redirect, investigate layout conflict |

## Design Notes
- **Column header color discrepancy is intentional per gap answers:** dashboard uses gray-500 (#6B7280, gap-answer q17), full-list uses primary-action orange (#F97316, gap-answer q16). The `mode` prop controls which color applies. Implementer should not "normalize" this — it is a deliberate design decision.
- **Badge variant for Draft/Archived:** depends on FE-UI-001 (Badge `soft` prop). If FE-UI-001 is not yet merged, implement Draft/Archived badge colors using direct className overrides (`bg-[#FED7AA]`, `bg-[#D1D5DB]`) as a temporary measure, then refactor to `soft` variant once FE-UI-001 lands.
- **Sort default:** full-list mode defaults to sorting by "Updated" column descending (latest first), matching gap-answer q2 "default sorted latest application first."
- **Search debounce:** not specified in gap answers. Recommend 200ms debounce on search input to avoid excessive re-renders, but this is an implementation detail — ACs test final filtered state, not intermediate renders.
- **Responsive breakpoint:** 768px is derived from gap-answer q10 "stack into card layout." Exact breakpoint is an implementation detail; AC-007 tests the behavior below 768px.
