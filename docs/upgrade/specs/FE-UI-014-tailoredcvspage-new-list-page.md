---
spec_id: FE-UI-014
title: "TailoredCVsPage — new list page"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /tailored-cvs
component_file: src/frontend/app/tailored-cvs/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** The route /tailored-cvs does not exist. Tailored CVs are only accessible within individual application views. The CV Center page currently groups base and tailored CVs together without a dedicated tailored-only view.
**Required behavior:** A new page at /tailored-cvs renders inside the existing AppShell (AppSidebar + AppHeader already specced in Batch B). The page reuses the existing PageHeader component (with credits display) and UserMenu component. Below the header, it renders a TailoredCVsListTable (FE-UI-015) inside a card container with "All Tailored CVs" sub-heading. The page fetches tailored CV data from GET /cv-tailorings and passes loading/error/data state down to the table component.
**User impact:** Users can see all their tailored CVs in a single dedicated view, separated from base CVs, improving navigation clarity.

## Evidence
**Mockup files:** Tailored CVs View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/tailored-cvs.json
**Gap answers source:** docs/upgrade/gap-answers/tailored-cvs.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/tailored-cvs/page.tsx
**Page file(s):** src/frontend/app/tailored-cvs/page.tsx (is the page)
**Tier:** feature — cascade risk: low (new route, no existing component to break)
**API dependencies:** GET /cv-tailorings
**Imports this component:** AppShell (layout), PageHeader, UserMenu, TailoredCVsListTable (FE-UI-015)

## Fix Plan
**Files to modify:**
- `src/frontend/app/tailored-cvs/page.tsx` — create new page component that fetches GET /cv-tailorings, manages loading/error state, and renders PageHeader + TailoredCVsListTable
- i18n translation files — add Hebrew keys for page title "Tailored CVs" and sub-heading "All Tailored CVs"

**Behavior changes:**
- New route /tailored-cvs becomes navigable
- Page renders PageHeader (with credits) and UserMenu — both reused, no changes needed
- Data fetching: calls GET /cv-tailorings, passes result array + isLoading + error + onRetry to TailoredCVsListTable
- AppSidebar nav item for "Tailored CVs" (with document-with-pencil icon per gap-answer q7) is handled by FE-UI-003 (Batch B) — not duplicated here

**Non-goals (explicitly out of scope):**
- AppSidebar restructuring (already specced in Batch B, FE-UI-003)
- AppHeader changes (already specced in Batch B, FE-UI-004)
- CV Center page modifications (separate route, separate spec if needed)
- Server-side pagination
- New API endpoints (GET /cv-tailorings already exists)

**Rollback plan:** Remove route file — no database or API changes

## Acceptance Criteria

### Page Structure
- [ ] AC-001: Given a user navigates to /tailored-cvs, when the page loads, then the PageHeader component renders with the title "Tailored CVs" and credits display
- [ ] AC-002: Given a user navigates to /tailored-cvs, when the page loads, then a TailoredCVsListTable component is rendered inside a card container below the header with sub-heading "All Tailored CVs"
- [ ] AC-003: Given the GET /cv-tailorings request is in flight, when the page renders, then `isLoading=true` is passed to TailoredCVsListTable
- [ ] AC-004: Given the GET /cv-tailorings request fails, when the page renders, then `error` is passed to TailoredCVsListTable and `onRetry` triggers a re-fetch
- [ ] AC-005: Given the GET /cv-tailorings request succeeds, when the page renders, then the response array is passed as `tailoredCvs` prop to TailoredCVsListTable

### i18n
- [ ] AC-006: Given locale is `he`, when the page renders, then the page title "Tailored CVs" and sub-heading "All Tailored CVs" render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | Data loaded successfully | Render PageHeader + TailoredCVsListTable with data |
| loading | GET /cv-tailorings in flight | Pass isLoading=true to table |
| error | GET /cv-tailorings fails | Pass error + onRetry to table |
| empty | GET /cv-tailorings returns [] | Pass empty array to table (table handles empty state) |

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | unit | pre_merge | false |
| AC-003 | unit | pre_merge | false |
| AC-004 | unit | pre_merge | false |
| AC-005 | unit | pre_merge | false |
| AC-006 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No regression on any existing route
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/tailored-cvs/page.tsx:TBD | tests/ui/unit/TailoredCVsPage.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove route file, re-open spec |

## Design Notes
- Structurally identical to FE-UI-012 (CoverLettersPage) — same page shell pattern, different API endpoint and child table component.
- Sidebar icon for this route is "document with pencil/edit" to distinguish from Base CVs (per gap-answer q7). This is implemented in FE-UI-003 (AppSidebar), not in this page component.
