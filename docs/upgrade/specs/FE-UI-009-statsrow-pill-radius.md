---
spec_id: FE-UI-009
title: "Upgrade StatsRow — increase pill corner radius and add loading skeleton"
priority: low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /dashboard
component_file: src/frontend/components/dashboard/StatsRow.tsx
tier: feature
---

## Problem Statement
**Current behavior:** StatsRow renders three stat pills (Plan, Credits Remaining, Status) with `rounded-lg` corner radius. There is no loading state — the component either renders with data or not at all.
**Required behavior:** Pill corner radius increases to `rounded-xl` for a softer, more modern appearance. A loading state renders skeleton placeholders matching the pill shape with shimmer animation when data is not yet available.
**User impact:** Minor visual polish — pills appear slightly rounder, matching the updated design language. Loading skeleton prevents layout shift when dashboard data is fetching.

## Evidence
**Mockup files:** Dashboard View page.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/dashboard/StatsRow.tsx
**Page file(s):** src/frontend/app/dashboard/page.tsx
**Tier:** feature — cascade risk: low (single route consumer)
**API dependencies:** none (data passed via props from parent)
**Imports this component:** app/dashboard/page.tsx

## Fix Plan
**Files to modify:**
- `src/frontend/components/dashboard/StatsRow.tsx` — change `rounded-lg` to `rounded-xl` on all three pill containers; add `isLoading` prop; render skeleton placeholders when loading

**Behavior changes:**
- Pill corner radius increases from `rounded-lg` (8px) to `rounded-xl` (12px)
- New `isLoading` boolean prop: when true, renders 3 skeleton pill placeholders with shimmer animation matching pill dimensions; when false/omitted, renders normally (backward compatible)

**Non-goals (explicitly out of scope):**
- Content or layout changes to StatsRow (format, order, spacing unchanged)
- Color changes to pills
- New stat pills or removal of existing ones
- Interactive behaviors (pills remain non-interactive)

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given StatsRow renders with data, when inspected, then each pill container has Tailwind class `rounded-xl` (not `rounded-lg`)
- [ ] AC-002: Given `isLoading` is true, when rendered, then 3 skeleton placeholder elements are shown matching the pill shape (`rounded-xl`, same width/height as data pills)
- [ ] AC-003: Given `isLoading` is true, when rendered, then skeleton placeholders display a shimmer/pulse animation (Tailwind `animate-pulse` or equivalent)
- [ ] AC-004: Given `isLoading` is true, when rendered, then no data text (Plan, Credits, Status values) is visible
- [ ] AC-005: Given `isLoading` is false or omitted, when rendered with valid props, then StatsRow renders identically to current behavior except for the increased corner radius
- [ ] AC-006: Given locale is `he`, when rendered, then all existing translated strings ("Plan", "Credits Remaining", "Status", "Active", "Inactive") continue to render in Hebrew — no new i18n keys required

## States to Handle
| State | Trigger | Behavior |
|-------|---------|----------|
| default | props populated, isLoading false/omitted | Render three data pills with rounded-xl |
| loading | isLoading true | 3 skeleton pill placeholders with shimmer |

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
- Existing StatsRow rendering (Plan, Credits, Status values and layout) must not change beyond corner radius
- Dashboard page layout unaffected — StatsRow occupies same space

**allowed_deltas:**
- Pill corner radius increases from rounded-lg to rounded-xl (intentional)
- New skeleton state renders when isLoading is true (additive)

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/dashboard/StatsRow.tsx:TBD | tests/ui/unit/StatsRow.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert StatsRow.tsx, re-open spec to in_progress |

## Design Notes
- **Corner radius value:** `rounded-xl` maps to `border-radius: 0.75rem` (12px) in default Tailwind config. The diff analysis says "slightly rounder" — `rounded-xl` is one step up from current `rounded-lg` (8px). If the design intent is `rounded-2xl` (16px) or `rounded-full`, this spec should be updated after mockup clarification.
- **Skeleton dimensions:** skeleton placeholders should match the rendered pill width. Since pill width is content-driven, skeletons should use a fixed representative width (e.g., `w-32` for Plan, `w-40` for Credits, `w-28` for Status) to prevent layout shift.
