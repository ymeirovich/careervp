# Phase 5 — Batch B: Layout Tier (applications-hub route)
# Components: AppSidebar, AppHeader, HubLayout
# Model: Opus | New conversation per batch
# Paste this entire file as your first message

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write THREE complete upgrade specs — one each for AppSidebar, AppHeader, and HubLayout — scoped to changes visible on route /applications/[id].

THINK before writing each spec:
1. What does the component currently do?
2. What visual changes are required? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks?

THEN produce ALL THREE specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "Upgrade {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]
component_file: {FILE_PATH}
tier: layout

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** Job Application Hub page-top.png, Job Application Hub page-middle.png, Job Application Hub page-bottom.png
**Diff analysis source:** docs/upgrade/diff-analysis/applications-hub.json
**Gap answers source:** docs/upgrade/gap-answers/applications-hub.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** layout — cascade risk: medium
**API dependencies:** {list endpoints}
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

## States to Handle
default | loading | error | empty | hover | focus | disabled | {others}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on components outside this spec's scope
- No layout shifts on routes not targeted by this spec
- Existing test suite passes without modification

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | Layout regression on any route using this layout component | Block deploy, investigate |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output the three specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: AppSidebar
File: components/layout/AppSidebar.tsx
Tier: layout
Today's date: 2026-05-23
Note: This component appears on ALL routes. The spec scope is the shared sidebar redesign — write it once here, mark it as applying globally.

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "AppSidebar",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Navigation structure change only (7 items, updated icons, active state styling) — no backend data required",
  "in_scope": true
}
```

**Also appears on /dashboard, /applications, /cover-letters, /tailored-cvs (all cosmetic, same change):**
- /dashboard: "Nav restructure: 'CV Center' split into 'Base CVs', 'Tailored CVs', 'Cover Letters' (7 items total), icon updates, active state styling"
- /applications: "Applications nav item active state styling only"
- /cover-letters: "Add 'Cover Letters' nav item (envelope icon) and split 'CV Center' into 'Base CVs' / 'Tailored CVs'"
- /tailored-cvs: "Add 'Tailored CVs' nav item with active state styling (orange left border accent, bold text)"
- All: in_scope: true, no backend data required

**Diff analysis entry (applications-hub):**
```json
{
  "component": "AppSidebar",
  "file": "components/layout/AppSidebar.tsx",
  "tier": "layout",
  "change_type": "modify",
  "visual_description": "Same sidebar changes already captured in dashboard analysis. 7 nav items: Dashboard, Applications, Base CVs, Tailored CVs, Cover Letters, Billing, Settings.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": [],
  "backend_data_required": "none",
  "backend_available": "yes"
}
```

**Prior gap answer (from dashboard route, applies to all routes):**
```json
{
  "from_route": "/dashboard",
  "question_id": "q9",
  "component": "AppSidebar",
  "topic": "responsive",
  "answer": "Collapse to icon-only rail on tablet, hamburger overlay on mobile",
  "applies_here": "Same sidebar on all routes — already answered"
}
```

---

### Component 2: AppHeader
File: components/layout/AppHeader.tsx
Tier: layout
Today's date: 2026-05-23

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "AppHeader",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Credits label format change only ('Credits: X / Y') — data already sourced from existing usage endpoint; no new API fields required",
  "in_scope": true
}
```

**Also appears on /dashboard (same change):**
```json
{
  "route": "/dashboard",
  "component": "AppHeader",
  "change_type": "modify",
  "backend_classification": "cosmetic",
  "resolution": "Credits format change to 'Credits: X / Y' and account dropdown additions (Help link, Log out, Upgrade navigation) — all client-side; no new backend data required",
  "in_scope": true
}
```

**Diff analysis entry (applications-hub):**
```json
{
  "component": "AppHeader",
  "file": "components/layout/AppHeader.tsx",
  "tier": "layout",
  "change_type": "modify",
  "visual_description": "Shows 'Job Application Hub' as page title, 'Credits: 1 / 3' counter, and account dropdown showing 'Lisi'. Same structure as dashboard analysis.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": [],
  "backend_data_required": "none",
  "backend_available": "yes"
}
```

---

### Component 3: HubLayout
File: components/layout/HubLayout.tsx
Tier: layout
Today's date: 2026-05-23

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "HubLayout",
  "change_type": "modify",
  "backend_classification": "yes",
  "resolution": "Job title, company name, job_url, and job description all available from GET /applications/{application_id} response",
  "in_scope": true
}
```

**Diff analysis entry (applications-hub):**
```json
{
  "component": "HubLayout",
  "file": "components/layout/HubLayout.tsx",
  "tier": "layout",
  "change_type": "modify",
  "visual_description": "Current renders children in a flex column with banners. Screenshot shows a job details header section (back link, title, company, job posting link, description) above the module grid. Grid is 2 columns instead of current 1/2/3 responsive grid. HubLayout or a new wrapper must include the job header.",
  "interaction_states_visible": ["default"],
  "interaction_states_needed_but_not_shown": ["stale_banner", "error_banner", "blocked_banner"],
  "backend_data_required": "Job title, company name, job URL, job description — from GET /applications/{id} response",
  "backend_available": "yes"
}
```

**Diff analysis: layout changes relevant to HubLayout:**
```json
[
  {
    "description": "New job details header section at top of page: '← Back' link, job title (large heading), company name (subtitle text), 'View Job Posting ↗' orange link, truncated job description with 'Show more' expandable toggle — this section does not exist in current hub page",
    "affects_component": "unknown",
    "change_type": "new-component"
  },
  {
    "description": "Module cards laid out in a 2-column grid (not the current 3-column grid on xl breakpoints). Cards are wider and taller with more internal spacing",
    "affects_component": "HubLayout",
    "change_type": "structure"
  }
]
```

**Gap answers relevant to HubLayout (applications-hub.json):**
```json
[
  {
    "question_id": "q4",
    "component": "JobDetailHeader",
    "topic": "edge_case",
    "question": "How should long job descriptions be handled in the Job Detail Header's 'Show more' toggle?",
    "answer": "Truncate at 3 lines, expand inline on click",
    "applies_to_shared_component": false
  },
  {
    "question_id": "q9",
    "component": "JobDetailHeader",
    "topic": "edge_case",
    "question": "Should the 'View Job Posting ↗' link open the external job URL in a new tab?",
    "answer": "Yes — new tab with rel='noopener noreferrer'",
    "applies_to_shared_component": false
  },
  {
    "question_id": "q19",
    "component": "ModuleCard",
    "topic": "responsive",
    "question": "The current module grid uses xl:grid-cols-3 (3 columns on XL screens) but all screenshots show 2 columns. Should xl:grid-cols-3 be removed to cap the grid at 2 columns at all desktop viewport sizes?",
    "answer": "Keep xl:grid-cols-3 — do not remove the 3-column breakpoint. Screenshots may not cover XL viewport widths, but the 3-column layout should be preserved for very wide screens.",
    "applies_to_shared_component": false
  }
]
```

**New components needed (from diff analysis):**
```
JobDetailHeader — card section showing job title, company name, Active badge, 'View Job Posting ↗' link,
truncated description with 'Show more' toggle, and '← Back' navigation link.
Note: HubLayout owns the JobDetailHeader slot — include its wiring in the HubLayout spec.
A separate spec for JobDetailHeader will be written in Batch C (feature tier).
```

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the three spec markdowns, back-to-back.
