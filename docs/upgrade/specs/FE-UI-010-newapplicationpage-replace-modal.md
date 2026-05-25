---
spec_id: FE-UI-010
title: "Replace NewApplicationModal — full-page form with back navigation and CV picker"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/new (new route, replaces modal on /dashboard)
component_file: src/frontend/app/applications/new/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** NewApplicationModal is a modal dialog rendered inline on the dashboard page. It contains four fields (Job Title, Company Name, Job Description, Job URL), a Cancel button, and a Create Application button. The modal opens via state toggle on the dashboard, submits via POST /jobs, and navigates to `/applications/{job_id}` on success. There is no "Choose Base CV" step, no back navigation, and no page-level layout. Errors display as inline `<p>` text below the form fields.
**Required behavior:** NewApplicationModal is removed and replaced by a dedicated full-page form at `/applications/new`. The page has a "← Back" link returning to the dashboard, a single-column card layout containing the same four fields (Job Title, Company Name, Job Description, Job URL), plus a "Choose Base CV" section showing the currently selected CV filename and a "Change" button that opens ChooseBaseCVModal (FE-UI-011). Cancel and "Create Application" buttons remain at the bottom. During submission, the button text changes to "Creating..." with disabled state. Errors display as a banner at the top of the form card. The form submits to the existing POST /jobs endpoint. The dashboard's "+ New Application" button changes from opening a modal to navigating to `/applications/new`.
**User impact:** Users get a less cramped, full-page form for creating applications with the ability to select a base CV before submission, improving the application creation workflow.

## Evidence
**Mockup files:** New Application Form.png, New Application-Job Description textbox edit.png, New Application Form-Choose Base CV Modal.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/applications/new/page.tsx (new)
**Page file(s):** src/frontend/app/applications/new/page.tsx (self — it is the page), src/frontend/app/dashboard/page.tsx (navigation source)
**Tier:** feature — cascade risk: low (new page, replaces modal; dashboard page updated to navigate instead of opening modal)
**API dependencies:** POST /jobs (existing, verified in Swagger)
**Imports this component:** N/A (it is a Next.js page route, not imported as a component). Dashboard page navigates to this route via `router.push`.

## Fix Plan
**Files to modify:**
- `src/frontend/app/applications/new/page.tsx` — create new page with full-page form, back navigation, Choose Base CV section, loading/error/disabled states
- `src/frontend/app/dashboard/page.tsx` — remove NewApplicationModal import and state; change "+ New Application" button onClick to `router.push('/applications/new')`; remove modal render
- `src/frontend/components/NewApplicationModal/NewApplicationModal.tsx` — delete file (replaced by page)
- i18n translation files — add Hebrew keys for "← Back", "Choose Base CV", "Base CV", "Change", "Creating...", error banner text, and all form labels

**Behavior changes:**
- "+ New Application" on dashboard navigates to `/applications/new` instead of opening a modal
- Form is a full page with card layout instead of a modal overlay
- "← Back" link at top navigates to `/dashboard`
- "Choose Base CV" section added below form fields showing selected CV filename + "Change" button
- Submit button text changes to "Creating..." and disables during submission (was spinner icon via `isLoading` prop on Button)
- Error state changes from inline `<p>` to banner at top of form card
- All required fields must be filled before Create Application enables (Job Title, Company Name, Job Description required; Job URL optional)

**Non-goals (explicitly out of scope):**
- New API endpoints — POST /jobs is unchanged
- File upload directly on this page (handled by ChooseBaseCVModal)
- Auto-save or draft persistence
- AccountDropdownMenu (owned by AppHeader spec FE-UI-004)
- Rich text editing for Job Description

**Rollback plan:** Revert NewApplicationPage to NewApplicationModal pattern — no database or API changes. Restore modal file, revert dashboard page.tsx to open modal.

## Acceptance Criteria

### Layout & Navigation
- [ ] AC-001: Given a user on the dashboard, when they click "+ New Application", then the browser navigates to `/applications/new` (no modal opens)
- [ ] AC-002: Given the `/applications/new` page is rendered, when the user views the page, then a "← Back" link/button is visible at the top of the page
- [ ] AC-003: Given the user clicks "← Back", when on `/applications/new`, then the browser navigates to `/dashboard`
- [ ] AC-004: Given the page is rendered, when inspected, then the form is contained within a single-column card (max-width constraint, centered) — not a modal overlay

### Form Fields
- [ ] AC-005: Given the page is rendered, when the user views the form, then four fields are visible: Job Title (text input, required), Company Name (text input, required), Job Description (textarea, required), Job URL (text input, optional)
- [ ] AC-006: Given all required fields are empty, when the form is rendered, then the "Create Application" button is disabled
- [ ] AC-007: Given all required fields (Job Title, Company Name, Job Description) have non-empty values, when the form is rendered, then the "Create Application" button is enabled

### Choose Base CV Section
- [ ] AC-008: Given the page is rendered, when the user views the form, then a "Base CV" section is visible below the form fields showing the selected CV filename (or a placeholder if none selected) and a "Change" button
- [ ] AC-009: Given the user clicks "Change" in the Base CV section, when ChooseBaseCVModal is not open, then ChooseBaseCVModal opens with `showChoices=true`
- [ ] AC-010: Given ChooseBaseCVModal returns a selected CV, when the modal closes, then the Base CV section updates to show the newly selected CV filename

### Submission — Loading State
- [ ] AC-011: Given all required fields are filled and the user clicks "Create Application", when the POST /jobs request is in flight, then the button text changes to "Creating..." and the button is disabled
- [ ] AC-012: Given submission is in flight, when the user views the form, then all form inputs and the Cancel button are disabled
- [ ] AC-013: Given the POST /jobs request succeeds, when the response returns, then the browser navigates to `/applications/{job_id}`

### Submission — Error State
- [ ] AC-014: Given the POST /jobs request fails, when the error response is received, then an error banner appears at the top of the form card with the error message
- [ ] AC-015: Given an error banner is displayed, when the user modifies any form field, then the error banner is dismissed

### Cancel
- [ ] AC-016: Given the user clicks "Cancel", when on the form page, then the browser navigates to `/dashboard` without submitting the form

### Accessibility
- [ ] AC-017: Given the page is rendered, when inspected, then each form input has an associated `<label>` element via `htmlFor`/`id` pairing
- [ ] AC-018: Given the page is rendered, when inspected, then the form element has `role="form"` or is a `<form>` element, and required fields are marked with `aria-required="true"` or `required` attribute
- [ ] AC-019: Given the error banner is displayed, when inspected, then it has `role="alert"` so screen readers announce it
- [ ] AC-020: Given the user presses Tab through the form, when navigating, then focus order follows visual top-to-bottom order: Back link → Job Title → Company Name → Job Description → Job URL → Base CV Change button → Cancel → Create Application

### i18n
- [ ] AC-021: Given locale is `he`, when the page is rendered, then all static strings render in Hebrew: "← Back" ("← חזרה"), "Choose Base CV" ("בחר קורות חיים בסיסיים"), "Change" ("שנה"), "Creating..." ("יוצר..."), form labels, button labels, and error banner text
- [ ] AC-022: Given locale is `he`, when the page is rendered, then the layout direction is RTL

### Responsive
- [ ] AC-023: Given viewport width < 768px, when the page is rendered, then the form card spans full width with appropriate padding (no horizontal overflow)

### Cleanup
- [ ] AC-024: Given the NewApplicationModal component file exists at `components/NewApplicationModal/NewApplicationModal.tsx`, when this spec is implemented, then the file is deleted and no import references to NewApplicationModal remain in the codebase

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | Page loads, no submission in progress | Form fields editable, Create Application button disabled until required fields filled |
| loading | POST /jobs in flight | Button text "Creating...", all inputs + Cancel disabled |
| error | POST /jobs returns non-2xx | Error banner at top of form card with message, form re-enabled |
| disabled | Required fields incomplete | Create Application button disabled |
| submitting | Between click and response | Same as loading |

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
- Existing NewApplicationModal unit tests (tests/ui/unit/NewApplicationForm.test.tsx) must be migrated to test NewApplicationPage — existing tests must not be deleted without replacement coverage
- POST /jobs endpoint contract unchanged — same request body shape `{ title, company_name, description, url? }`
- Dashboard page must still render correctly without NewApplicationModal — no visual regressions on StatsRow, JobsTable, or EmptyState
- Navigation to `/applications/{id}` after creation must still work

**allowed_deltas:**
- NewApplicationModal component file deleted
- Dashboard page no longer renders a modal overlay
- "+ New Application" button navigates instead of toggling modal state

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/app/dashboard/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/app/applications/new/page.tsx:TBD | tests/ui/unit/NewApplicationPage.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert to NewApplicationModal pattern, restore deleted modal file, re-open spec |
| RT-002 | New non-2xx response on POST /jobs that did not occur before | Block deploy, investigate request body shape mismatch |
| RT-003 | Navigation from dashboard to `/applications/new` returns 404 | Verify Next.js route file exists at `app/applications/new/page.tsx`, check build output |
| RT-004 | Post-creation redirect to `/applications/{id}` fails | Verify POST /jobs response still includes `job_id` field, check router.push call |

## Design Notes
- **Base CV section default state:** On initial page load, if the user has no CVs, the Base CV section should show placeholder text (e.g., "No CV selected") with the "Change" button still active. The ChooseBaseCVModal (FE-UI-011) handles the empty-CV-list edge case internally.
- **Base CV is optional for form submission:** The mockup shows a Base CV section, but the existing POST /jobs endpoint does not accept a `cv_id` field. The selected CV may be stored in component state for use in subsequent steps (VPR generation), or the field may need a backend addition in a future iteration. For V1, the Base CV section is a UI-only selection that persists in local state — it does not block form submission.
- **"Creating..." vs spinner:** Gap answer q5 specifies button text changes to "Creating..." with disabled state. This replaces the current `isLoading` spinner pattern on the Button component. Implementer should use plain text replacement, not the Button's `isLoading` prop.
- **Error banner placement:** Gap answer q6 specifies "Error banner at top of the form card" — this is inside the card, above the first form field, not above the card itself.
- **Existing test migration:** tests/ui/unit/NewApplicationForm.test.tsx currently tests against a canvas-app App component. These tests should be rewritten to test NewApplicationPage directly using React Testing Library. The old test file can be deleted only after equivalent coverage exists in the new test file.
