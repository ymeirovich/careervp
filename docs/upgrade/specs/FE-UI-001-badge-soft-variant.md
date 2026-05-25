---
spec_id: FE-UI-001
title: "Upgrade Badge — add soft/outlined rendering variant"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id] (change applies to all routes)
component_file: src/frontend/components/ui/Badge.tsx
tier: ui-primitive
---

## Problem Statement
**Current behavior:** Badge renders all variants (success, warning, error, info, final, edited) as solid-fill backgrounds with white text. There is no outlined or soft-fill rendering mode.
**Required behavior:** Badge accepts a `soft` boolean prop. When `soft` is true, Badge renders with a tinted background and matching-color text instead of solid fill. The semantic color mapping changes: green-tinted for terminal success states (Complete, Final, Edited), blue-tinted for in-progress states (Generating, Processing), gray/neutral-tinted for idle states (Ready, Active), and solid red (unchanged) for failure (Failed). When `soft` is false or omitted, Badge renders identically to today.
**User impact:** Status badges across the application gain visual hierarchy — soft badges for routine states reduce visual noise, while solid red for failures retains high urgency.

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json
**Gap answers source:** docs/upgrade/gap-answers/applications-hub.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/ui/Badge.tsx
**Page file(s):** src/frontend/components/ModuleCard/ModuleCard.tsx, src/frontend/components/dashboard/JobsTable.tsx
**Tier:** ui-primitive — cascade risk: high
**API dependencies:** none
**Imports this component:** StatusBadge (components/ui/StatusBadge.tsx), ModuleCard (components/ModuleCard/ModuleCard.tsx), JobsTable (components/dashboard/JobsTable.tsx), Badge.stories.tsx, StatusBadge.stories.tsx, Badge.figma.tsx

## Fix Plan
**Files to modify:**
- `src/frontend/components/ui/Badge.tsx` — add `soft?: boolean` prop to `BadgeProps`; add `softVariantStyles` map with tinted-bg + colored-text classes for each variant; select style map based on `soft` prop
- `src/frontend/components/ui/StatusBadge.tsx` — pass `soft` prop through to Badge (add `soft?: boolean` to `StatusBadgeProps`)

**Behavior changes:**
1. New optional `soft` prop (default `false`) on Badge — backward-compatible
2. When `soft={true}`:
   - `success` variant: `bg-green-50 text-green-700 border border-green-200`
   - `final` variant: `bg-green-50 text-green-700 border border-green-200`
   - `edited` variant: `bg-green-50 text-green-700 border border-green-200`
   - `info` variant: `bg-blue-50 text-blue-700 border border-blue-200`
   - `warning` variant: `bg-amber-50 text-amber-700 border border-amber-200`
   - `neutral` variant: `bg-gray-50 text-gray-700 border border-gray-200`
   - `stale` variant: `bg-amber-50 text-amber-700 border border-amber-200`
   - `error` variant: unchanged — remains `bg-state-error text-white` (solid red, per mockup)
3. StatusBadge gains optional `soft` prop forwarded to Badge

**Non-goals (explicitly out of scope):**
- Changing the existing solid variant styles
- Adding new `BadgeVariant` enum values (e.g. "draft", "archived" — those are separate route specs)
- Changing Badge sizing, padding, or typography
- Modifying ModuleCard or JobsTable to consume `soft` (that is the parent component spec's responsibility)

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given Badge with `variant="success"` and `soft={true}`, when rendered, then the element has a green-tinted background class (bg-green-50), green text class (text-green-700), and a green border class (border-green-200)
- [ ] AC-002: Given Badge with `variant="info"` and `soft={true}`, when rendered, then the element has a blue-tinted background class (bg-blue-50), blue text class (text-blue-700), and a blue border class (border-blue-200)
- [ ] AC-003: Given Badge with `variant="error"` and `soft={true}`, when rendered, then the element retains solid styling — bg-state-error and text-white (no soft override for error)
- [ ] AC-004: Given Badge with `variant="final"` and `soft={true}`, when rendered, then the element uses the same green-tinted soft classes as `success` soft
- [ ] AC-005: Given Badge with `variant="edited"` and `soft={true}`, when rendered, then the element uses the same green-tinted soft classes as `success` soft
- [ ] AC-006: Given Badge with `variant="neutral"` and `soft={true}`, when rendered, then the element has a gray-tinted background (bg-gray-50), gray text (text-gray-700), and gray border (border-gray-200)
- [ ] AC-007: Given Badge with `variant="warning"` and `soft={true}`, when rendered, then the element has an amber-tinted background (bg-amber-50), amber text (text-amber-700), and amber border (border-amber-200)
- [ ] AC-008: Given Badge with `variant="success"` and `soft` omitted, when rendered, then the element retains the current solid style (bg-state-active text-white) — backward compatibility
- [ ] AC-009: Given Badge with any variant and `soft={false}`, when rendered, then the element uses the existing solid variant style — identical to omitting `soft`
- [ ] AC-010: Given StatusBadge with `soft={true}`, when rendered, then the inner Badge element receives `soft={true}`
- [ ] AC-011: Given Badge with `soft={true}` and `variant="stale"`, when rendered, then the element uses amber-tinted soft classes matching `warning` soft
- [ ] AC-012: Given Badge with `soft={true}`, when the `soft` prop type is inspected, then it is `boolean | undefined` (optional, defaults to false)

## States to Handle
default | soft-success | soft-info | soft-error (same as solid) | soft-warning | soft-neutral | soft-final | soft-edited | soft-stale

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
- All existing solid-variant Badge usages render identically (AC-008, AC-009 enforce this)

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/ui/StatusBadge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/ui/Badge.tsx:TBD | tests/ui/unit/Badge.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | Existing ModuleCard or JobsTable tests fail after Badge change | Revert Badge.tsx and StatusBadge.tsx, investigate cascade |

## Design Notes
- The exact Tailwind color classes (bg-green-50, text-green-700, border-green-200, etc.) are best-fit interpretations of the mockup. If the project uses a custom design-token palette that maps differently, the implementer should substitute the closest semantic token equivalents while preserving the soft-tinted visual intent.
- q15 gap answer maps Ready→gray/neutral and Edited→green. The diff analysis described Ready as "same green soft" — the gap answer (q15) is authoritative as it was a direct clarification. StatusBadge currently maps `ready→success`; the parent spec (StatusBadge or ModuleCard) is responsible for changing that mapping to `neutral` when `soft` is used.
