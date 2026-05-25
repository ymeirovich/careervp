---
spec_id: FE-UI-016
title: "replace CVCenterContent — single-CV form to multi-CV table listing page"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /cv-center
component_file: src/frontend/app/cv-center/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** The /cv-center page renders CVCenterContent which is a single-CV flow: it loads one CV via `useCV()`, displays CVForm (create/edit) or CVPreview (read-only) with TagInput for skills and languages. The page header reads "CV Center" with an "Edit CV" button. There is no concept of multiple base CVs — only one CV can exist at a time.
**Required behavior:** The entire CVCenterContent component is replaced. The page header becomes "Base CVs" (matching the header bar text from the mockup). Below the header, a card container displays "All Base CVs" sub-heading on the left and a "+ Upload New CV" orange button on the right. The card body renders the new BaseCVsTable component (FE-UI-017). The page fetches base CV data from GET /users/me/cv (which returns a list) and passes loading/error/data state down to BaseCVsTable. The "+ Upload New CV" button opens ChooseBaseCVModal in upload-only mode (showChoices=false), specced separately in FE-UI-011 (Batch F). CVForm, CVPreview, and TagInput are removed from this file — they are relocated to the /cv-center/[cvId] detail route (gap-answer q18), accessible via the table's "View" action.
**User impact:** Users can see all their uploaded base CVs at a glance in a scannable table, upload new CVs, and navigate to individual CVs for viewing/editing — replacing the previous single-CV limitation.

## Evidence
**Mockup files:** Base CVs View page.png, Base CV New Upload modal.png
**Diff analysis source:** docs/upgrade/diff-analysis/cv-center.json
**Gap answers source:** docs/upgrade/gap-answers/cv-center.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/cv-center/page.tsx
**Page file(s):** src/frontend/app/cv-center/page.tsx (is the page)
**Tier:** feature — cascade risk: medium (replaces existing page content, but CVForm/CVPreview are relocated not deleted)
**API dependencies:** GET /users/me/cv (returns list of base CVs with fields: full_name, language, updated_at, and optionally status)
**Imports this component:** AppShell (layout), ErrorBoundary (existing), BaseCVsTable (FE-UI-017), ChooseBaseCVModal (FE-UI-011)

## Fix Plan
**Files to modify:**
- `src/frontend/app/cv-center/page.tsx` — replace CVCenterContent body: remove CVForm, CVPreview, TagInput definitions and single-CV state machine (ViewMode). Replace with page that fetches GET /users/me/cv (list), renders page header "Base CVs", card container with "All Base CVs" sub-heading + "+ Upload New CV" button, and BaseCVsTable. Add modal state for ChooseBaseCVModal (upload-only).
- `src/frontend/app/cv-center/[cvId]/page.tsx` — new detail route to receive relocated CVForm + CVPreview + TagInput (out of scope for THIS spec — documented as dependency)
- i18n translation files — add Hebrew keys for: "Base CVs", "All Base CVs", "+ Upload New CV"

**Behavior changes:**
- Page header text changes from "CV Center" to "Base CVs"
- "Edit CV" button removed from header; replaced by "+ Upload New CV" orange button inside card header row
- Single-CV form/preview/create flow removed entirely from this page
- Data fetching changes from single-CV `useCV()` hook to list-based GET /users/me/cv
- BaseCVsTable component renders inside card body (delegated to FE-UI-017)
- "+ Upload New CV" button opens ChooseBaseCVModal with `showChoices=false` (upload-only mode)
- ErrorBoundary wrapper retained around the page content

**Non-goals (explicitly out of scope):**
- BaseCVsTable implementation (FE-UI-017)
- ChooseBaseCVModal implementation (FE-UI-011)
- /cv-center/[cvId] detail route creation (separate spec)
- AppSidebar label change to "Primary CVs" (owned by FE-UI-003, gap-answer q16)
- Server-side pagination
- New API endpoints

**Rollback plan:** Revert page.tsx to previous CVCenterContent — no database or API changes

## Acceptance Criteria

### Page Structure
- [ ] AC-001: Given a user navigates to /cv-center, when the page loads, then a page header element renders with the text "Base CVs"
- [ ] AC-002: Given a user navigates to /cv-center, when the page loads, then a card container renders below the header containing a sub-heading row with "All Base CVs" text on the left
- [ ] AC-003: Given a user navigates to /cv-center, when the page loads, then the sub-heading row contains a button labeled "+ Upload New CV" with orange background (`bg-primary-action`) on the right
- [ ] AC-004: Given a user navigates to /cv-center, when the page loads, then a BaseCVsTable component is rendered inside the card container below the sub-heading row

### Data Flow
- [ ] AC-005: Given the GET /users/me/cv request is in flight, when the page renders, then `isLoading=true` is passed to BaseCVsTable
- [ ] AC-006: Given the GET /users/me/cv request fails, when the page renders, then `error` is passed to BaseCVsTable and `onRetry` triggers a re-fetch of GET /users/me/cv
- [ ] AC-007: Given the GET /users/me/cv request succeeds, when the page renders, then the response array is passed as the `cvs` prop to BaseCVsTable

### Upload Flow
- [ ] AC-008: Given the page is rendered, when the user clicks "+ Upload New CV", then ChooseBaseCVModal opens with `showChoices=false` (upload-only mode)
- [ ] AC-009: Given ChooseBaseCVModal is open in upload-only mode, when the user completes an upload successfully, then the modal closes and GET /users/me/cv is re-fetched to refresh the table

### Removed Content
- [ ] AC-010: Given the page is rendered, when the DOM is inspected, then no CVForm component, CVPreview component, or TagInput component is rendered on this page
- [ ] AC-011: Given the page is rendered, when the DOM is inspected, then no "Edit CV" button, "Create CV" button, or ViewMode state machine exists on this page

### Error Boundary
- [ ] AC-012: Given the page is rendered, when inspected, then CVCenterContent is wrapped in an ErrorBoundary with `cloudwatchKey="cv-center-page"`

### i18n
- [ ] AC-013: Given locale is `he`, when the page renders, then "Base CVs" header, "All Base CVs" sub-heading, and "+ Upload New CV" button label render in Hebrew

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | GET /users/me/cv returns populated array | Render BaseCVsTable with data |
| loading | GET /users/me/cv in flight | Pass `isLoading=true` to BaseCVsTable |
| error | GET /users/me/cv fails | Pass `error` + `onRetry` to BaseCVsTable |
| empty | GET /users/me/cv returns empty array | Pass empty array to BaseCVsTable (empty state handled by FE-UI-017) |
| upload-modal-open | User clicks "+ Upload New CV" | ChooseBaseCVModal rendered with showChoices=false |

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

## Baseline & Regression Budget
**blocked_regressions:**
- CVForm and CVPreview accessible at /cv-center/[cvId] (not deleted, moved to detail route per gap-answer q18)
- No regression on any route that links to /cv-center
- Existing test suite passes without modification
- ErrorBoundary wrapper with `cloudwatchKey="cv-center-page"` retained

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/app/cv-center/page.tsx:TBD | tests/ui/unit/CVCenterContent.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert to previous CVCenterContent, re-open spec |
| RT-002 | New non-2xx response on GET /users/me/cv | Block deploy, investigate |
| RT-003 | CVForm or CVPreview inaccessible at /cv-center/[cvId] after deploy | Block deploy, verify detail route exists |

## Design Notes
- **Status field conflict:** Contract verification says status is "derived client-side as constant 'Ready'" (no backend field). Gap-answer q13 says "Backend field — the GET /users/me/cv response includes (or will include) a 'status' field". This spec does NOT own status rendering (that is BaseCVsTable FE-UI-017's concern), but the data-fetch layer should pass through whatever fields the API returns. Developer should confirm with backend whether `status` is present in GET /users/me/cv response before implementation.
- **Sidebar label:** Gap-answer q16 specifies the sidebar label changes to "Primary CVs" — this is owned by FE-UI-003 (AppSidebar spec, Batch B), not this spec.
- **CVForm relocation:** CVForm, CVPreview, and TagInput are moved to /cv-center/[cvId] per gap-answer q18. A separate spec for the detail route is required but out of scope here. This spec only removes them from the listing page.
- **useCV hook replacement:** The current `useCV()` hook fetches a single CV. This page will need a new hook or direct fetch that returns a list from GET /users/me/cv. The existing `useCV()` hook may be retained for the /cv-center/[cvId] detail route.
- **ChooseBaseCVModal dependency:** The "+ Upload New CV" button depends on ChooseBaseCVModal (FE-UI-011, Batch F). If FE-UI-011 is not yet implemented, the button can render but the modal will be a no-op until that spec is complete.
