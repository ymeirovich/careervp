---
spec_id: FE-UI-012
title: "CoverLettersPage — new list page"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cover-letters
component_file: src/frontend/app/cover-letters/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** The route /cover-letters does not exist. There is no page or component for viewing all cover letters across applications in one place. Users must navigate into each individual application to find its cover letter.
**Required behavior:** A new page at /cover-letters renders inside the existing AppShell (AppSidebar + AppHeader already specced in Batch B). The page reuses the existing PageHeader component (with credits display already wired in) and the existing UserMenu component. Below the header, it renders a CoverLettersListTable (FE-UI-013) inside a card container. The page fetches cover letter data from GET /cover-letters and passes loading/error/data state down to the table component.
**User impact:** Users can see all their cover letters in a single consolidated view, improving discoverability and workflow efficiency.

## Evidence
**Mockup files:** Cover Letters View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/cover-letters.json
**Gap answers source:** docs/upgrade/gap-answers/cover-letters.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/cover-letters/page.tsx
**Page file(s):** src/frontend/app/cover-letters/page.tsx (is the page)
**Tier:** feature — cascade risk: low (new route, no existing component to break)
**API dependencies:** GET /cover-letters
**Imports this component:** AppShell (layout), PageHeader, UserMenu, CoverLettersListTable (FE-UI-013)

## Fix Plan
**Files to modify:**
- `src/frontend/app/cover-letters/page.tsx` — create new page component that fetches GET /cover-letters, manages loading/error state, and renders PageHeader + CoverLettersListTable
- i18n translation files — add Hebrew keys for page title "Cover Letters" and sub-heading "All Cover Letters"

**Behavior changes:**
- New route /cover-letters becomes navigable
- Page renders PageHeader (with credits) and UserMenu — both reused, no changes needed to those components
- Data fetching: calls GET /cover-letters, passes result array + isLoading + error + onRetry to CoverLettersListTable
- AppSidebar nav item for "Cover Letters" is handled by FE-UI-003 (Batch B) — not duplicated here

**Non-goals (explicitly out of scope):**
- AppSidebar restructuring (already specced in Batch B, FE-UI-003)
- AppHeader changes (already specced in Batch B, FE-UI-004)
- Server-side pagination (V1 scale does not require it)
- New API endpoints (GET /cover-letters already exists)

**Rollback plan:** Remove route file — no database or API changes

## Acceptance Criteria

### Page Structure
- [ ] AC-001: Given a user navigates to /cover-letters, when the page loads, then the PageHeader component renders with the title "Cover Letters" and credits display
- [ ] AC-002: Given a user navigates to /cover-letters, when the page loads, then a CoverLettersListTable component is rendered inside a card container below the header
- [ ] AC-003: Given the GET /cover-letters request is in flight, when the page renders, then `isLoading=true` is passed to CoverLettersListTable
- [ ] AC-004: Given the GET /cover-letters request fails, when the page renders, then `error` is passed to CoverLettersListTable and `onRetry` triggers a re-fetch
- [ ] AC-005: Given the GET /cover-letters request succeeds, when the page renders, then the response array is passed as `coverLetters` prop to CoverLettersListTable

### i18n
- [ ] AC-006: Given locale is `he`, when the page renders, then the page title "Cover Letters" and sub-heading "All Cover Letters" render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | Data loaded successfully | Render PageHeader + CoverLettersListTable with data |
| loading | GET /cover-letters in flight | Pass isLoading=true to table |
| error | GET /cover-letters fails | Pass error + onRetry to table |
| empty | GET /cover-letters returns [] | Pass empty array to table (table handles empty state) |

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
| AC-001 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/cover-letters/page.tsx:TBD | tests/ui/unit/CoverLettersPage.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Remove route file, re-open spec |

## Design Notes
- PageHeader and UserMenu are reused as-is per gap-answers q13 and q14 — no new shared components needed for this page.
- Sidebar nav item addition is covered by FE-UI-003 (AppSidebar Batch B spec). This spec does not duplicate that concern.
