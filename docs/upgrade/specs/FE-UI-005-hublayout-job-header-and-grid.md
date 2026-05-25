---
spec_id: FE-UI-005
title: "Upgrade HubLayout — add JobDetailHeader slot and adjust module grid to 2-column default"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]
component_file: src/frontend/components/layout/HubLayout.tsx
tier: layout
---

## Problem Statement
**Current behavior:** HubLayout renders a flex column containing conditional banners (blocked, stale, error) followed by `children`. It has no job detail section — the page title, company name, job URL, and job description are not displayed anywhere on the hub page. The module card grid is defined in the page file (`app/applications/[id]/page.tsx`) as `grid-cols-1 md:grid-cols-2 xl:grid-cols-3`.
**Required behavior:** HubLayout accepts new props for job details (title, company, jobUrl, jobDescription) and renders a JobDetailHeader section above the banners and children. The JobDetailHeader shows: a "← Back" link navigating to `/applications`, the job title as a large heading, the company name as subtitle text, a "View Job Posting ↗" orange link opening the job URL in a new tab with `rel="noopener noreferrer"`, and the job description truncated at 3 lines with a "Show more"/"Show less" inline toggle. The module grid in the page file retains `xl:grid-cols-3` (per gap answer q19) but no other grid changes are needed in HubLayout itself — the grid definition stays in the page file.
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
- `src/frontend/components/layout/HubLayout.tsx` — extend HubLayoutProps with optional job detail fields (jobTitle, companyName, jobUrl, jobDescription, applicationId), render JobDetailHeader section above existing banner/children content when job details are present
- `src/frontend/app/applications/[id]/page.tsx` — pass job detail fields from the useApplicationHub hook response to HubLayout props

**Behavior changes:**
1. HubLayoutProps gains optional fields: `jobTitle?: string`, `companyName?: string`, `jobUrl?: string`, `jobDescription?: string`
2. When `jobTitle` is provided, HubLayout renders a job detail section above the banners containing:
   - "← Back" link (`<Link href="/applications">`) at the top
   - Job title as an `<h2>` with large heading styles
   - Company name as secondary text below the title
   - "View Job Posting ↗" as an anchor tag with `href={jobUrl}`, `target="_blank"`, `rel="noopener noreferrer"`, styled with orange/primary-action color — only rendered when `jobUrl` is a non-empty string
   - Job description paragraph truncated to 3 CSS lines (`line-clamp-3`), with a "Show more" button that expands to full text and changes label to "Show less"
3. When `jobTitle` is not provided (undefined or empty), the job detail section is not rendered — HubLayout behaves identically to today
4. The page file passes job detail data from the hub state to HubLayout
5. The module grid definition in the page file (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3`) is NOT changed (per gap answer q19)

**Non-goals (explicitly out of scope):**
- Creating a standalone JobDetailHeader component file (that is Batch C, feature tier — this spec wires the slot inline within HubLayout)
- Changing the module card grid breakpoints (xl:grid-cols-3 is preserved per q19)
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
- Module grid breakpoints remain unchanged (grid-cols-1 md:grid-cols-2 xl:grid-cols-3)

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-008 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-009 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/app/applications/[id]/page.tsx:TBD | tests/ui/integration/HubLayout.test.tsx | integration | pre_merge | pending |
| AC-013 | src/frontend/components/layout/HubLayout.tsx:TBD | tests/ui/unit/HubLayout.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file and page file changes, re-open spec to in_progress |
| RT-002 | Layout regression on any route using this layout component | Block deploy, investigate |
| RT-003 | GET /applications/{id} response does not include expected job detail fields (job_title, company_name, job_url, job_description) | Render HubLayout without job details (graceful fallback via AC-010), file backend bug |

## Design Notes
- This spec wires the job detail section inline within HubLayout rather than extracting a separate JobDetailHeader component. A future Batch C spec will extract JobDetailHeader as a standalone feature-tier component — at that point, the inline rendering here will be replaced by a `<JobDetailHeader />` import. This avoids blocking the layout spec on the feature component spec.
- The "← Back" link uses Next.js `<Link>` for client-side navigation to `/applications` (the jobs list page).
- The "View Job Posting ↗" link uses `target="_blank"` with `rel="noopener noreferrer"` per gap answer q9 — this is a security requirement for external links.
- The 3-line truncation uses Tailwind's `line-clamp-3` utility (requires `@tailwindcss/line-clamp` plugin or Tailwind v3.3+ which includes it natively). The implementer should verify the plugin is available.
- The `xl:grid-cols-3` breakpoint in the page file is explicitly preserved per gap answer q19. The screenshots only showed 2 columns because they did not capture XL viewport widths.
- The page file (`app/applications/[id]/page.tsx`) must extract job detail fields from the `hubState` or `useApplicationHub` hook response. The exact field names in the API response (e.g., `job_title` vs `jobTitle`) should be verified against the backend response shape during implementation.
