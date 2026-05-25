---
spec_id: FE-UI-003
title: "Upgrade AppSidebar — restructure navigation from 5 to 7 items with updated icons and active state"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id] (change applies to all routes)
component_file: src/frontend/components/layout/AppSidebar.tsx
tier: layout
---

## Problem Statement
**Current behavior:** AppSidebar renders 5 navigation items: Dashboard (LayoutDashboard), Applications (Briefcase), CV Center (FileText), Billing (CreditCard), Settings (SettingsIcon). The "CV Center" item is a single entry linking to `/cv-center`. Active state applies `bg-surface-selected text-text-primary` background fill. On tablet and mobile viewports the sidebar remains fixed at 220px — no responsive collapse.
**Required behavior:** AppSidebar renders 7 navigation items: Dashboard, Applications, Base CVs, Tailored CVs, Cover Letters, Billing, Settings. The single "CV Center" entry is removed and replaced by three separate entries: "Base CVs" (`/cv-center`, icon: FileText), "Tailored CVs" (`/tailored-cvs`, icon: FilePen), and "Cover Letters" (`/cover-letters`, icon: Mail). Active state styling adds an orange left border accent and orange icon color alongside bold text. On tablet viewports (md breakpoint) the sidebar collapses to an icon-only rail; on mobile viewports (below md) it becomes a hamburger-triggered overlay.
**User impact:** Users gain direct navigation to tailored CVs and cover letters without navigating through the CV Center hub, reducing clicks for the most common post-application workflows.

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json, docs/upgrade/diff-analysis/dashboard.json
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json (q9 responsive, q18 icons), docs/upgrade/gap-answers/applications-hub.json (prior_answers_applied)

## Architecture & Ownership Map
**Component file:** src/frontend/components/layout/AppSidebar.tsx
**Page file(s):** src/frontend/components/layout/AppShell.tsx (imports AppSidebar), src/frontend/app/dashboard/layout.tsx (imports AppShell)
**Tier:** layout — cascade risk: medium (appears on every authenticated route via AppShell)
**API dependencies:** none
**Imports this component:** AppShell (components/layout/AppShell.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/components/layout/AppSidebar.tsx` — replace NAV_ITEMS array (5→7 items), add FilePen and Mail icon imports from lucide-react, update active state classes to include orange left border accent and orange icon tint, add responsive collapse behavior (icon-only rail on md, hamburger overlay below md)

**Behavior changes:**
1. NAV_ITEMS changes from 5 entries to 7 entries:
   - Dashboard → `/dashboard` (LayoutDashboard) — unchanged
   - Applications → `/applications` (Briefcase) — unchanged
   - Base CVs → `/cv-center` (FileText) — replaces "CV Center", same route
   - Tailored CVs → `/tailored-cvs` (FilePen) — new entry
   - Cover Letters → `/cover-letters` (Mail) — new entry
   - Billing → `/billing` (CreditCard) — unchanged
   - Settings → `/settings` (SettingsIcon) — unchanged
2. Active state styling: active nav item gets `border-l-3 border-primary-action` (orange left accent), icon receives `text-primary-action` (orange), label remains `text-text-primary font-bold`
3. Responsive: sidebar collapses to icon-only rail (no labels, narrower width) at tablet breakpoint (md), and renders as a hamburger-triggered overlay drawer below md

**Non-goals (explicitly out of scope):**
- Creating the `/tailored-cvs` or `/cover-letters` route pages (separate specs)
- Changing the CareerVP logo/branding section at the top of the sidebar
- Changing sidebar width on desktop (remains 220px)
- Adding badge counts or notification indicators to nav items

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given AppSidebar is rendered, when the nav item list is inspected, then exactly 7 items are present with labels in order: Dashboard, Applications, Base CVs, Tailored CVs, Cover Letters, Billing, Settings
- [ ] AC-002: Given AppSidebar is rendered, when the "Base CVs" nav item is inspected, then its href is `/cv-center` and its icon is the Lucide `FileText` icon
- [ ] AC-003: Given AppSidebar is rendered, when the "Tailored CVs" nav item is inspected, then its href is `/tailored-cvs` and its icon is the Lucide `FilePen` icon
- [ ] AC-004: Given AppSidebar is rendered, when the "Cover Letters" nav item is inspected, then its href is `/cover-letters` and its icon is the Lucide `Mail` icon
- [ ] AC-005: Given the current pathname is `/applications/123`, when AppSidebar renders, then the "Applications" nav item has an orange left border (border-primary-action) and its icon has orange color (text-primary-action)
- [ ] AC-006: Given the current pathname is `/cv-center`, when AppSidebar renders, then the "Base CVs" nav item has the active state styling (orange left border + orange icon)
- [ ] AC-007: Given the current pathname is `/tailored-cvs`, when AppSidebar renders, then the "Tailored CVs" nav item has the active state styling (orange left border + orange icon)
- [ ] AC-008: Given the current pathname is `/cover-letters`, when AppSidebar renders, then the "Cover Letters" nav item has the active state styling (orange left border + orange icon)
- [ ] AC-009: Given the current pathname is `/dashboard`, when AppSidebar renders, then exactly one nav item (Dashboard) has active state styling, and the remaining 6 items have inactive styling
- [ ] AC-010: Given a viewport width below the md breakpoint (< 768px), when the page renders, then the sidebar is hidden by default and a hamburger button is visible that toggles the sidebar as an overlay
- [ ] AC-011: Given a viewport width at the md breakpoint (768px–1023px), when the page renders, then the sidebar renders as an icon-only rail without text labels
- [ ] AC-012: Given a viewport width at or above the lg breakpoint (≥ 1024px), when the page renders, then the sidebar renders at full 220px width with both icons and text labels
- [ ] AC-013: Given AppSidebar is rendered, when no "CV Center" nav item label is searched for, then no element with text "CV Center" exists in the sidebar

## States to Handle
default | active (per nav item) | hover | mobile-collapsed | tablet-rail | desktop-expanded

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
| AC-010 | integration | pre_merge | false |
| AC-011 | integration | pre_merge | false |
| AC-012 | integration | pre_merge | false |
| AC-013 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- No layout shifts on routes not targeted by this spec
- Existing test suite passes without modification
- AppShell layout (sidebar + main content area) remains structurally intact at desktop widths

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/integration/AppSidebar.responsive.test.tsx | integration | pre_merge | pending |
| AC-011 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/integration/AppSidebar.responsive.test.tsx | integration | pre_merge | pending |
| AC-012 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/integration/AppSidebar.responsive.test.tsx | integration | pre_merge | pending |
| AC-013 | src/frontend/components/layout/AppSidebar.tsx:TBD | tests/ui/unit/AppSidebar.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | Layout regression on any route using this layout component | Block deploy, investigate |
| RT-003 | Navigation to `/tailored-cvs` or `/cover-letters` returns 404 because route pages do not yet exist | Defer responsive nav testing until route pages are created; sidebar links themselves are still valid |

## Design Notes
- The "Base CVs" item reuses the existing `/cv-center` route — no new page is needed for that entry. The `/tailored-cvs` and `/cover-letters` routes require new page components (separate specs).
- The hamburger overlay on mobile and icon-only rail on tablet are new responsive behaviors. The current sidebar has no responsive handling — this is a net-new capability.
- The exact orange border width for active state (`border-l-3` vs `border-l-2`) should match the mockup; implementer should verify against screenshots. The token `border-primary-action` maps to the existing `--color-primary-action` CSS variable.
- The Cover Letters icon is `Mail` from lucide-react (envelope icon), matching the "envelope icon" described in the diff analysis.
