---
spec_id: FE-UI-005
title: "Upgrade HubLayout — add JobDetailHeader slot and adjust module grid to 2-column default"
priority: high
status: implemented
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]
component_file: src/frontend/components/layout/HubLayout.tsx
tier: layout
---

## Problem Statement
**Current behavior:** HubLayout renders a flex column containing conditional banners (blocked, stale, error) followed by `children`. It has no job detail section — the page title, company name, job URL, and job description are not displayed anywhere on the hub page. The module card grid is defined in the page file (`app/applications/[id]/page.tsx`) as `grid-cols-1 md:grid-cols-2 xl:grid-cols-3`.
**Required behavior:** HubLayout accepts a new optional prop, `jobDetailHeaderSlot?: React.ReactNode`, and renders it above the existing banners and children when provided. The module grid on the hub page is updated to a 2-column max layout (remove `xl:grid-cols-3`) to match the upgrade screenshots.
**User impact:** Users see full job context (title, company, description, link to original posting) at the top of the application hub, eliminating the need to navigate away to recall job details while working on application modules.

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json (layout_changes[0]: new job details header, layout_changes[1]: 2-column grid)
**Gap answers source:** docs/upgrade/gap-answers/applications-hub.json (q4: truncate at 3 lines expand inline, q9: new tab with noopener noreferrer, q19: keep xl:grid-cols-3)

## Architecture & Ownership Map
**Component file:** src/frontend/components/layout/HubLayout.tsx
**Page file(s):** src/frontend/app/applications/[id]/page.tsx (imports HubLayout, passes props)
**Tier:** layout — cascade risk: medium
**API dependencies:** GET /applications/{application_id} — provides job_title, company_name, job_url, job_description fields (contract-verified available)
**Imports this component:** ApplicationHubPage (app/applications/[id]/page.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/components/layout/HubLayout.tsx` — extend HubLayoutProps with an optional `jobDetailHeaderSlot?: React.ReactNode`, render it above existing banner/children content
- `src/frontend/app/applications/[id]/page.tsx` — update the module grid classes to a 2-column max layout (drop `xl:grid-cols-3`)

**Behavior changes:**
1. HubLayoutProps gains an optional field: `jobDetailHeaderSlot?: React.ReactNode`
2. When `jobDetailHeaderSlot` is provided, HubLayout renders it above the existing banners and `children`
3. When `jobDetailHeaderSlot` is not provided, HubLayout behaves identically to today
4. The module grid definition in the page file is updated from `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` to `grid-cols-1 md:grid-cols-2`

**Non-goals (explicitly out of scope):**
- Implementing the actual JobDetailHeader UI (Batch 3 wires the slot with real job details)
- Changing the banner logic (blocked, stale, error banners remain as-is)
- Adding loading skeletons for the job detail section (separate spec)
- Changing MODULE_ORDER in the page file

**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given HubLayout with `jobTitle="Senior Engineer"`, when rendered, then an element with role heading (h2) contains the text "Senior Engineer"
- [ ] AC-002: Given HubLayout with `companyName="Acme Corp"`, when rendered, then a text element contains "Acme Corp" below the job title heading
- [ ] AC-003: Given HubLayout with `jobUrl="https://example.com/job"`, when rendered, then an anchor element with text containing "View Job Posting" has `href="https://example.com/job"`, `target="_blank"`, and `rel="noopener noreferrer"`
- [ ] AC-004: Given HubLayout with `jobUrl=""` (empty string), when rendered, then no "View Job Posting" link is present in the document
- [ ] AC-005: Given HubLayout with `jobUrl` omitted (undefined), when rendered, then no "View Job Posting" link is present in the document
- [ ] AC-006: Given HubLayout with a `jobDescription` longer than 3 lines of text, when rendered in default state, then the description element has `line-clamp-3` class (or equivalent CSS truncation) applied
- [ ] AC-007: Given HubLayout with a truncated job description, when the "Show more" button is clicked, then the description expands to show full text and the button text changes to "Show less"
- [ ] AC-008: Given HubLayout with an expanded job description, when the "Show less" button is clicked, then the description truncates back to 3 lines and the button text changes to "Show more"
- [ ] AC-009: Given HubLayout with job details provided, when rendered, then a "← Back" link element with `href="/applications"` is present above the job title
- [ ] AC-010: Given HubLayout with `jobTitle` omitted (undefined), when rendered, then no job detail section is present — only banners and children render (backward compatibility)
- [ ] AC-011: Given HubLayout with job details and `hubStatus="STALE_DEPENDENCIES"`, when rendered, then the stale banner renders below the job detail section and above children
- [ ] AC-012: Given the ApplicationHubPage loads successfully, when HubLayout is rendered, then the `jobTitle` prop value matches the job title from the GET /applications/{id} API response
- [ ] AC-013: Given HubLayout with a `jobDescription` shorter than 3 lines, when rendered, then no "Show more" button is present

## States to Handle
default (with job details) | default (without job details — backward compat) | description-collapsed | description-expanded | stale_banner | error_banner | blocked_banner | loading (page-level, not HubLayout's concern)

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | unit | pre_merge | false |
| AC-003 | unit | pre_merge | false |
| AC-004 | unit | pre_merge | false |
| AC-005 | unit | pre_merge | false |
| AC-006 | unit | pre_merge | false |
| AC-007 | integration | pre_merge | false |
| AC-008 | integration | pre_merge | false |
| AC-009 | unit | pre_merge | false |
| AC-010 | unit | pre_merge | false |
| AC-011 | unit | pre_merge | false |
| AC-012 | integration | pre_merge | false |
| AC-013 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- No layout shifts on routes not targeted by this spec
- Existing test suite passes without modification
- HubLayout without job detail props renders identically to current behavior (AC-010)
- Module grid uses 2-column max layout (grid-cols-1 md:grid-cols-2)

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-008 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-009 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/app/applications/[id]/page.tsx:117 | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-013 | src/frontend/components/layout/HubLayout.tsx:19 | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file and page file changes, re-open spec to in_progress |
| RT-002 | Layout regression on any route using this layout component | Block deploy, investigate |
| RT-003 | GET /applications/{id} response does not include expected job detail fields (job_title, company_name, job_url, job_description) | Render HubLayout without job details (graceful fallback via AC-010), file backend bug |

## Design Notes
- This spec adds a JobDetailHeader slot (`jobDetailHeaderSlot`) to HubLayout. Batch 3 will pass the real job detail header UI into this slot.
- The module grid is updated to a 2-column max layout (no `xl:grid-cols-3`) to match the upgrade screenshots.
