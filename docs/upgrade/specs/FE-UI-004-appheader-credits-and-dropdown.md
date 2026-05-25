---
spec_id: FE-UI-004
title: "Upgrade AppHeader — credits label format and account dropdown menu items"
priority: medium
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id] (change applies to all routes)
component_file: src/frontend/components/layout/AppHeader.tsx
tier: layout
---

## Problem Statement
**Current behavior:** AppHeader displays credits as `"{used} / {total} applications"` (e.g., "0 / 3 applications") or "Unlimited". The account button shows the user name and a chevron but has no dropdown menu — clicking it does nothing.
**Required behavior:** Credits display changes to `"Credits: {used} / {total}"` (e.g., "Credits: 1 / 3"). The account button opens a dropdown menu containing three items: "Help" (navigates to help/support), "Log out" (red text, triggers sign-out), and an "Upgrade" button (orange filled, navigates to `/billing`). The PAGE_TITLES map must also include entries for the new routes (`/tailored-cvs` → "Tailored CVs", `/cover-letters` → "Cover Letters", `/cv-center` → "Base CVs").
**User impact:** Users can access account management actions (help, logout, upgrade) directly from the header on any page, and the credits label is clearer with the explicit "Credits:" prefix.

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/dashboard.json (AppHeader component_changes, layout_changes for credits and dropdown)
**Gap answers source:** docs/upgrade/gap-answers/dashboard.json (q4: Upgrade navigates to /billing)

## Architecture & Ownership Map
**Component file:** src/frontend/components/layout/AppHeader.tsx
**Page file(s):** src/frontend/components/layout/AppShell.tsx (imports AppHeader), src/frontend/app/dashboard/layout.tsx (imports AppShell)
**Tier:** layout — cascade risk: medium (appears on every authenticated route via AppShell)
**API dependencies:** none (credits data already passed as props from AppShell; logout uses existing auth context)
**Imports this component:** AppShell (components/layout/AppShell.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/components/layout/AppHeader.tsx` — change credits label format, add dropdown menu component with Help/Log out/Upgrade items, update PAGE_TITLES map with new route entries

**Behavior changes:**
1. Credits label format changes from `"{used} / {total} applications"` to `"Credits: {used} / {total}"`. When `isUnlimited` is true, display remains `"Unlimited"`.
2. Account button becomes a toggle for a dropdown menu. Clicking opens the menu; clicking again or clicking outside closes it.
3. Dropdown menu items:
   - "Help" — plain text link (navigates to `/settings` or a help section, TBD by implementer)
   - "Log out" — red text, triggers sign-out flow via auth context
   - "Upgrade" — orange filled button style, navigates to `/billing`
4. PAGE_TITLES map updated:
   - `/cv-center` → "Base CVs" (renamed from "CV Center")
   - `/tailored-cvs` → "Tailored CVs" (new entry)
   - `/cover-letters` → "Cover Letters" (new entry)

**Non-goals (explicitly out of scope):**
- Changing the page title rendering logic or typography
- Adding notification badges or icons to the header
- Implementing the actual sign-out logic (consumed from existing AuthContext)
- Changing header height or horizontal layout

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given AppHeader with `creditsUsed=1`, `creditsTotal=3`, and `isUnlimited=false`, when rendered, then the credits element contains the text "Credits: 1 / 3"
- [ ] AC-002: Given AppHeader with `creditsUsed=0`, `creditsTotal=3`, and `isUnlimited=false`, when rendered, then the credits element contains the text "Credits: 0 / 3"
- [ ] AC-003: Given AppHeader with `isUnlimited=true`, when rendered, then the credits element contains the text "Unlimited"
- [ ] AC-004: Given AppHeader is rendered with the account button visible, when the account button is clicked, then a dropdown menu appears containing items with text "Help", "Log out", and "Upgrade"
- [ ] AC-005: Given the account dropdown is open, when the "Log out" item is inspected, then it has red text styling (text-state-error or equivalent red color class)
- [ ] AC-006: Given the account dropdown is open, when the "Upgrade" button is inspected, then it has orange filled styling (bg-primary-action text-white or equivalent)
- [ ] AC-007: Given the account dropdown is open, when the "Upgrade" button is clicked, then the router navigates to `/billing`
- [ ] AC-008: Given the account dropdown is open, when the user clicks outside the dropdown, then the dropdown closes
- [ ] AC-009: Given the current pathname is `/cv-center`, when AppHeader renders, then the page title displays "Base CVs"
- [ ] AC-010: Given the current pathname is `/tailored-cvs`, when AppHeader renders, then the page title displays "Tailored CVs"
- [ ] AC-011: Given the current pathname is `/cover-letters`, when AppHeader renders, then the page title displays "Cover Letters"
- [ ] AC-012: Given the current pathname is `/applications/123`, when AppHeader renders, then the page title displays "Job Application Hub"
- [ ] AC-013: Given AppHeader is rendered and no credits text containing "applications" is searched for, then no element with text matching the pattern "{N} / {N} applications" exists

## States to Handle
default | dropdown-open | dropdown-closed | hover (account button) | hover (dropdown items)

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
| AC-008 | integration | pre_merge | false |
| AC-009 | unit | pre_merge | false |
| AC-010 | unit | pre_merge | false |
| AC-011 | unit | pre_merge | false |
| AC-012 | unit | pre_merge | false |
| AC-013 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- No layout shifts on routes not targeted by this spec
- Existing test suite passes without modification
- Header height and horizontal alignment remain unchanged

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/integration/AppHeader.dropdown.test.tsx | integration | pre_merge | pending |
| AC-009 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/components/layout/AppHeader.tsx:TBD | tests/ui/unit/AppHeader.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | Layout regression on any route using this layout component | Block deploy, investigate |
| RT-003 | Account dropdown menu fails to close on outside click, causing overlay issues | Hotfix click-outside handler, re-verify AC-008 |

## Design Notes
- The "Help" link destination is not explicitly specified in the gap answers or diff analysis. The implementer should link to `/settings` (support section) or an external help URL — confirm with design before implementation.
- The "Log out" action should call the existing sign-out function from AuthContext. The implementer should verify the exact method name (e.g., `signOut()`, `logout()`).
- The dropdown should use `role="menu"` with `role="menuitem"` children for accessibility, and support keyboard navigation (Escape to close, arrow keys to traverse items).
- The PAGE_TITLES entry for `/applications/[id]` should resolve dynamically to "Job Application Hub" — the current fallback to "CareerVP" for unmatched paths should be preserved, but the `/applications/[id]` pattern needs explicit handling since `usePathname()` returns the full path (e.g., `/applications/abc123`), not the route pattern.
