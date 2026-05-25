---
spec_id: FE-UI-011
title: "Create ChooseBaseCVModal — shared CV picker with choice and upload-only modes"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/new (choice mode) + /cv-center (upload-only mode)
component_file: src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx
tier: feature
---

## Problem Statement
**Current behavior:** No ChooseBaseCVModal exists. The NewApplicationModal has no CV selection step. The CV Center page (cv-center/page.tsx) has its own inline "Create CV" button but no modal for choosing between uploaded and generated CVs, and no file-upload modal for the base CV table.
**Required behavior:** A new shared ChooseBaseCVModal component with two modes controlled by a `showChoices` prop. When `showChoices=true` (default, used from NewApplicationPage): the modal displays "Choose Base CV" title, a list/table of existing CVs to pick from, "Select uploaded CV" and "Select generated CV" category buttons, an "OR" divider, and an "Upload New CV" section with file input. When `showChoices=false` (used from BaseCVsTable "+ Upload New CV" button on cv-center): the modal displays "Upload Base CV" title with only the file input and Upload button — no choice buttons. Both modes have an X close icon in the top-right corner, focus trap, Escape-to-dismiss, and aria-describedby for subtitle text.
**User impact:** Users can select an existing CV or upload a new one before creating an application, and can upload CVs directly from the CV Center — both through a consistent, accessible modal experience.

## Evidence
**Mockup files:** New Application Form-Choose Base CV Modal.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json + docs/upgrade/diff-analysis/cv-center.json (new_components_needed)
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json + docs/upgrade/gap-answers/cv-center.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx (new)
**Page file(s):** src/frontend/app/applications/new/page.tsx (imports with showChoices=true), src/frontend/app/cv-center/page.tsx (imports with showChoices=false, future — when BaseCVsTable is added)
**Tier:** feature — cascade risk: low (new component, no existing consumers to break)
**API dependencies:** GET /users/me/cv (existing, verified in Swagger — fetches user's base CVs for the selection list)
**Imports this component:** app/applications/new/page.tsx (FE-UI-010), app/cv-center/page.tsx (future BaseCVsTable integration)

## Fix Plan
**Files to modify:**
- `src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx` — create new component with dual-mode behavior, CV list, file upload, accessibility, close handling
- `src/frontend/components/ChooseBaseCVModal/index.ts` — barrel export
- i18n translation files — add Hebrew keys for "Choose Base CV", "Upload Base CV", "Select uploaded CV", "Select generated CV", "Upload New CV", "OR", "Upload", "No CVs available", subtitle text

**Behavior changes:**
- New component — no existing behavior modified
- When `showChoices=true`: renders full choice UI with CV list, category buttons, OR divider, and upload section
- When `showChoices=false`: renders upload-only UI with file input and Upload button
- Both modes: X close icon, focus trap, Escape dismissal, aria-describedby

**Non-goals (explicitly out of scope):**
- CV parsing or content preview within the modal
- Drag-and-drop file upload
- Multi-file upload
- Inline CV editing
- Generated CV creation workflow (the "Select generated CV" button opens a separate flow — this spec only covers the button and its callback, not what happens after selection)
- BaseCVsTable component itself (separate spec)

**Rollback plan:** Delete ChooseBaseCVModal component files — no database or API changes. Consumers (NewApplicationPage) fall back to no CV selection step.

## Acceptance Criteria

### Render Guard
- [ ] AC-001: Given `isOpen` is false, when the component is rendered, then no modal markup is present in the DOM

### Choice Mode (showChoices=true)
- [ ] AC-002: Given `isOpen=true` and `showChoices=true`, when the modal renders, then the heading text is "Choose Base CV"
- [ ] AC-003: Given `isOpen=true` and `showChoices=true`, when the modal renders, then a "Select uploaded CV" button and a "Select generated CV" button are both visible
- [ ] AC-004: Given `isOpen=true` and `showChoices=true`, when the modal renders, then an "OR" divider text is visible between the choice buttons section and the upload section
- [ ] AC-005: Given `isOpen=true` and `showChoices=true`, when the modal renders, then a list/table of existing CVs is displayed within the modal for selection
- [ ] AC-006: Given the user clicks "Select uploaded CV", when uploaded CVs exist, then the `onSelectCV` callback fires with the selected uploaded CV data
- [ ] AC-007: Given the user clicks "Select generated CV", when generated CVs exist, then the `onSelectCV` callback fires with the selected generated CV data

### Upload-Only Mode (showChoices=false)
- [ ] AC-008: Given `isOpen=true` and `showChoices=false`, when the modal renders, then the heading text is "Upload Base CV"
- [ ] AC-009: Given `isOpen=true` and `showChoices=false`, when the modal renders, then "Select uploaded CV" and "Select generated CV" buttons are NOT present in the DOM
- [ ] AC-010: Given `isOpen=true` and `showChoices=false`, when the modal renders, then a file input and an "Upload" button are visible

### File Upload Behavior
- [ ] AC-011: Given no file has been selected, when the modal renders in either mode, then the "Upload" button is disabled
- [ ] AC-012: Given the user selects a file via the file input, when the file is chosen, then the selected filename is displayed in the modal and the "Upload" button becomes enabled
- [ ] AC-013: Given the user clicks the "Upload New CV" button/area, when clicked, then the OS file picker opens directly (no intermediate step)
- [ ] AC-014: Given a file is selected and the user clicks "Upload", when the upload completes, then `onUpload` callback fires with the file data

### Empty State
- [ ] AC-015: Given `showChoices=true` and the user has no existing CVs (uploaded or generated), when the modal renders, then both "Select uploaded CV" and "Select generated CV" buttons are disabled
- [ ] AC-016: Given `showChoices=true` and no CVs exist, when the modal renders, then the "Upload New CV" section is visually highlighted (e.g., border emphasis or background change) to guide the user

### Close Behavior
- [ ] AC-017: Given the modal is open, when the user clicks the X close icon in the top-right corner, then `onClose` callback fires and the modal is removed from the DOM
- [ ] AC-018: Given the modal is open, when the user presses the Escape key, then `onClose` callback fires and the modal is removed from the DOM
- [ ] AC-019: Given the modal is open, when the user clicks the backdrop overlay outside the modal card, then `onClose` callback fires

### Accessibility
- [ ] AC-020: Given the modal is open, when inspected, then the modal container has `role="dialog"` and `aria-modal="true"`
- [ ] AC-021: Given the modal is open, when inspected, then `aria-labelledby` references the heading element ID and `aria-describedby` references the subtitle text element ID
- [ ] AC-022: Given the modal is open, when the user presses Tab, then focus is trapped within the modal — focus does not leave the modal boundary
- [ ] AC-023: Given the modal opens, when it becomes visible, then focus moves to the first focusable element inside the modal (X close button or first interactive element)
- [ ] AC-024: Given the modal has buttons, when inspected, then disabled buttons follow the existing design system disabled pattern (opacity reduction, `cursor-not-allowed`, `aria-disabled="true"` or `disabled` attribute)

### i18n
- [ ] AC-025: Given locale is `he`, when the modal renders in choice mode, then all strings render in Hebrew: "Choose Base CV" ("בחר קורות חיים בסיסיים"), "Select uploaded CV" ("בחר קורות חיים שהועלו"), "Select generated CV" ("בחר קורות חיים שנוצרו"), "Upload New CV" ("העלה קורות חיים חדשים"), "OR" ("או")
- [ ] AC-026: Given locale is `he`, when the modal renders in upload-only mode, then "Upload Base CV" ("העלה קורות חיים בסיסיים") and "Upload" ("העלה") render in Hebrew

### Responsive
- [ ] AC-027: Given viewport width < 768px, when the modal is open, then the modal card takes near-full width with appropriate margins (no horizontal overflow or clipping)

### Data Model
- [ ] AC-028: Given the component receives CV data, when distinguishing uploaded CVs from generated CVs, then it treats them as distinct data types — generated CVs (TailoredCV from VPR/tailoring flow) are separate from uploaded base CVs

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default (choice) | `isOpen=true`, `showChoices=true`, CVs exist | Full UI with enabled choice buttons, CV list, upload section |
| default (upload-only) | `isOpen=true`, `showChoices=false` | Upload-only UI with file input + disabled Upload button |
| empty | `showChoices=true`, no CVs exist | Choice buttons disabled, upload section highlighted |
| file-selected | User picks a file via file input | Filename displayed, Upload button enabled |
| hover | Mouse over choice buttons or Upload button | Standard hover state per design system |
| focus | Keyboard focus on interactive elements | Visible focus ring per design system |
| disabled | Buttons disabled (empty state or no file selected) | Existing design system disabled pattern (opacity, cursor) |
| closed | `isOpen=false` | No DOM output |

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
- Existing ChangeBaseCVModal test file (tests/ui/unit/ChangeBaseCVModal.test.tsx) tests against a canvas-app export — new tests must provide equivalent or greater coverage for the ChooseBaseCVModal component
- GET /users/me/cv endpoint contract unchanged — response shape used to populate CV list
- CV Center page (cv-center/page.tsx) must continue to function — ChooseBaseCVModal is additive, not replacing existing CV Center functionality

**allowed_deltas:**
- New component added to the codebase — no existing files modified (except future consumers adding imports)
- New i18n keys added to translation files

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-016 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-017 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-018 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-019 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-020 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-021 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-022 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-023 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-024 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-025 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-026 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-027 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |
| AC-028 | src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx:TBD | tests/ui/unit/ChooseBaseCVModal.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Delete ChooseBaseCVModal component, remove imports from consumers, re-open spec |
| RT-002 | GET /users/me/cv returns unexpected shape breaking CV list render | Verify API contract, add defensive parsing, block deploy if schema changed |
| RT-003 | Focus trap causes keyboard navigation to break in consuming pages | Disable focus trap temporarily, investigate z-index or portal conflicts |

## Design Notes
- **CV list rendering in choice mode:** Gap answer q7 (dashboard) specifies "Shows a list/table of existing CVs to pick from within the same modal." The exact list layout (table rows vs. card list) is not specified in mockups. Implementer should match the visual style of existing tables in the app (e.g., simple rows with CV name + upload date). The list is populated from GET /users/me/cv response.
- **Generated CVs as distinct type:** Gap answer q14 (cv-center) clarifies that generated CVs (TailoredCV from VPR/tailoring flow) are a separate data model from uploaded base CVs. The "Select generated CV" button should filter/display only generated CVs, and "Select uploaded CV" should filter/display only uploaded base CVs. The API endpoint or filtering strategy for generated CVs is TBD — if GET /users/me/cv does not return generated CVs, the "Select generated CV" button should be disabled with appropriate messaging until the API supports it.
- **Disabled button pattern:** Gap answer q15 (cv-center) specifies "Match the existing disabled pattern already defined for buttons in the design system." Do not introduce new disabled styling — use the existing Button component's disabled prop or the equivalent opacity/cursor pattern used elsewhere in the codebase.
- **Upload button always enabled:** Gap answer q16 (dashboard) clarifies the "Upload New CV" button/area is always enabled and directly opens the OS file picker. However, the "Upload" submit button (that confirms the upload after file selection) is disabled until a file is selected (per AC-011). These are different buttons — the file picker trigger vs. the upload confirmation.
- **X close icon:** Gap answer q17 (cv-center) confirms an X close icon in the top-right corner of the modal. This is in addition to Escape-to-dismiss and backdrop click.
- **Existing test file:** tests/ui/unit/ChangeBaseCVModal.test.tsx exists and tests a "ChangeBaseCVModal" component from a canvas-app. The new ChooseBaseCVModal tests should be written in a new test file (tests/ui/unit/ChooseBaseCVModal.test.tsx) testing the actual component directly. The old test file may be kept for reference but is not blocking.
- **Naming:** The mockup and gap answers use "Choose Base CV" for choice mode and "Upload Base CV" for upload-only mode. The component is named ChooseBaseCVModal (not ChangeBaseCVModal) to match the mockup terminology. The existing ChangeBaseCVModal test file uses the old naming convention.
