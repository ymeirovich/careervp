---
spec_id: FE-UI-002
title: "Upgrade ProgressBar — add visible label row and rounded ends"
priority: high
status: implemented
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-29
route: /applications/[id] (change applies to all routes)
component_file: src/frontend/components/ui/ProgressBar.tsx
tier: ui-primitive
---

## Problem Statement
**Current behavior:** ProgressBar renders a thin h-2 (8px) bar with rounded ends and an sr-only label. There is no visible text showing "Progress" or the percentage value — only screen readers receive the label. The bar already has `rounded-full` on both track and fill.
**Required behavior:** ProgressBar gains a `showLabel` boolean prop. When `showLabel` is true, a visible label row renders above the bar with "Progress" text left-aligned and the percentage value (e.g. "85%") right-aligned. The bar height (h-2) and rounded ends remain unchanged per q16. The existing `aria-valuenow`, `aria-label`, and sr-only span are preserved alongside the visible label per q8. The `error` color variant at `value={100}` is used for failed-state rendering per q18.
**User impact:** Users see real-time progress percentage during module processing without relying on assistive technology, improving feedback clarity for sighted users.

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json
**Gap answers source:** docs/upgrade/gap-answers/applications-hub.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/ui/ProgressBar.tsx
**Page file(s):** Currently not imported by any page — will be consumed by ModuleCard (components/ModuleCard/ModuleCard.tsx) per parent spec
**Tier:** ui-primitive — cascade risk: high
**API dependencies:** none — receives `value` prop from parent
**Imports this component:** none currently (ModuleCard will import per its own spec)

## Fix Plan
**Files to modify:**
- `src/frontend/components/ui/ProgressBar.tsx` — add `showLabel?: boolean` prop to `ProgressBarProps`; when `showLabel` is true, render a `<div>` row above the bar track containing a left-aligned "Progress" text span and a right-aligned `{clamped}%` text span

**Behavior changes:**
1. New optional `showLabel` prop (default `false`) on ProgressBar — backward-compatible
2. When `showLabel={true}`: render a flex row above the bar with:
   - Left: `<span>` containing "Progress" (text-sm text-text-secondary)
   - Right: `<span>` containing `{clamped}%` (text-sm font-medium text-text-primary)
3. Existing `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`, and sr-only span remain unchanged
4. Bar height stays h-2, rounded-full stays — no dimensional changes per q16
5. Error color variant at value=100 already works for failed-state rendering (no change needed, just documented per q18)

**Non-goals (explicitly out of scope):**
- Changing bar height (confirmed h-2 stays per q16)
- Adding animation or transition to the label
- Changing the color map or adding new color variants
- i18n of the "Progress" label (Hebrew translation is a separate cross-cutting concern)
- ModuleCard integration (parent component spec's responsibility)

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [x] AC-001: Given ProgressBar with `value={85}` and `showLabel={true}`, when rendered, then a visible text element containing "Progress" appears left-aligned above the bar
- [x] AC-002: Given ProgressBar with `value={85}` and `showLabel={true}`, when rendered, then a visible text element containing "85%" appears right-aligned above the bar
- [x] AC-003: Given ProgressBar with `value={65}` and `showLabel={true}`, when rendered, then the percentage text reads "65%"
- [x] AC-004: Given ProgressBar with `value={0}` and `showLabel={true}`, when rendered, then the percentage text reads "0%"
- [x] AC-005: Given ProgressBar with `value={100}` and `showLabel={true}`, when rendered, then the percentage text reads "100%"
- [x] AC-006: Given ProgressBar with `showLabel` omitted, when rendered, then no visible "Progress" or percentage text elements are present — backward compatibility
- [x] AC-007: Given ProgressBar with `showLabel={false}`, when rendered, then no visible "Progress" or percentage text elements are present
- [x] AC-008: Given ProgressBar with `showLabel={true}` and `label="Generating CV"`, when rendered, then the `aria-label` attribute still reads "Generating CV" and the sr-only span still contains "Generating CV: {value}%"
- [x] AC-009: Given ProgressBar with `value={100}` and `color="error"`, when rendered, then the bar fill uses the `bg-state-error` class (existing behavior — regression guard for failed-state rendering per q18)
- [x] AC-010: Given ProgressBar with `value={50}` and `showLabel={true}`, when the `role="progressbar"` element is inspected, then `aria-valuenow` equals 50 (existing ARIA preserved alongside visible label per q8)
- [x] AC-011: Given ProgressBar with `value={150}` and `showLabel={true}`, when rendered, then the percentage text reads "100%" and `aria-valuenow` equals 100 (clamping applied to visible label)
- [x] AC-012: Given ProgressBar with `value={-5}` and `showLabel={true}`, when rendered, then the percentage text reads "0%" and `aria-valuenow` equals 0 (clamping applied to visible label)

## States to Handle
default (no label) | with-label | zero-value | full-value | over-100-clamped | negative-clamped | error-color | warning-color | primary-color

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

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- Existing test suite passes without modification
- ProgressBar without `showLabel` renders identically to current (AC-006, AC-007 enforce this)
- ARIA attributes remain present and correct regardless of `showLabel` value

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/ui/ProgressBar.tsx:TBD | src/frontend/tests/ui/unit/ProgressBar.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | ModuleCard tests fail after ProgressBar change | Revert ProgressBar.tsx, investigate cascade |

## Design Notes
- The "Progress" label text is hardcoded in English. If Hebrew i18n is required for this label, a follow-up spec or cross-cutting i18n pass should replace the hardcoded string with a translation key. This spec does not block on i18n.
- q17 confirmed the label row is rendered inside ProgressBar (not externally by ModuleCard), making it reusable across contexts.
- The error-color at 100% (q18) already works with existing props (`value={100} color="error"`) — no code change needed, but AC-009 serves as a regression guard.
