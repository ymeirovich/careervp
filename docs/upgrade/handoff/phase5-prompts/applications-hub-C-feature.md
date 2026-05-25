# Phase 5 — Batch C: Feature Tier (applications-hub route)
# Components: ModuleCard (modify), JobDetailHeader (new)
# Model: Opus | New conversation per batch
# Paste this entire file as your first message

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write TWO complete upgrade specs — one for ModuleCard (modify) and one for JobDetailHeader (new component) — both scoped to route /applications/[id].

THINK before writing each spec:
1. What does the component currently do? (from component map)
2. What visual changes are required? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable?
6. What are the regression risks? ModuleCard is used on ALL module sub-routes — changes cascade.

THEN produce BOTH specs in sequence using this exact format:

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
tier: feature

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
**Tier:** feature — cascade risk: low (unless ModuleCard — then medium, used across all module sub-routes)
**API dependencies:** {list endpoints}
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for:
- Every visual change from diff analysis (not blocked)
- Every gap interview answer (loading, error, empty, hover, etc.)
- Keyboard navigation and ARIA (FE_A11Y)
- Hebrew translations for all new i18n strings
- Responsive behaviour per gap answers

## States to Handle
notStarted | processing | ready | complete | edited | failed | final | stale | timeout | hover | focus | disabled

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- No visual regression on ModuleCard variants not targeted by this spec
- Existing test suite passes without modification (tests/ui/unit/, tests/unit/)
- No regression on module sub-routes (/vpr, /cover-letter, /cv-tailored, /gap-analysis, /interview-prep, /company-research)

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec to in_progress |
| RT-002 | New non-2xx response on affected API endpoint | Block deploy, investigate before re-promoting |

## Design Notes
- {unresolved ambiguities requiring human decision}
---

STOP: Output the two specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: ModuleCard
File: components/ModuleCard/ModuleCard.tsx
Tier: feature
Change type: modify
Today's date: 2026-05-23

**Contract verification entry (/applications/[id]):**
```json
{
  "route": "/applications/[id]",
  "component": "ModuleCard",
  "change_type": "modify",
  "backend_classification": "yes",
  "resolution": "Progress percentage for ProgressBar comes from GET /vpr/{id}/status, GET /cover-letter/{id}/status, GET /interview-prep/{id}/status, GET /cv-tailoring/{id}/status — all return progress data; status badge state (processing/complete/failed) derived from the same polling responses",
  "in_scope": true
}
```

**Diff analysis entry (applications-hub):**
```json
{
  "component": "ModuleCard",
  "file": "components/ModuleCard/ModuleCard.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Major changes: (1) All states now show a status badge (not just edited/stale/final). (2) Processing state shows ProgressBar with percentage instead of inline spinner. (3) Failed state shows red progress bar + 'Failed X minutes ago' text. (4) Secondary actions render as plain text links rather than ghost buttons. (5) Card has more vertical padding and larger title text. (6) Description/context lines shown for ready/complete/edited states.",
  "interaction_states_visible": ["notStarted", "processing", "ready", "complete", "edited", "failed", "final"],
  "interaction_states_needed_but_not_shown": ["stale", "timeout", "hover", "disabled"],
  "backend_data_required": "progress percentage value for processing state — must come from status polling endpoints",
  "backend_available": "yes — GET /vpr/{id}/status, GET /cover-letter/{id}/status, GET /interview-prep/{id}/status, GET /cv-tailoring/{id}/status return progress data"
}
```

**Diff analysis: layout changes affecting ModuleCard:**
```json
[
  {
    "description": "ModuleCard now shows a visible ProgressBar component with percentage label (e.g., 'Progress 85%', 'Progress 65%') during processing state, replacing the current inline spinner + text approach",
    "affects_component": "ModuleCard",
    "change_type": "structure"
  },
  {
    "description": "ModuleCard in processing state shows italicized status text above the progress bar (e.g., 'Still processing...', 'Generating...') — current shows spinner icon + text inline",
    "affects_component": "ModuleCard",
    "change_type": "structure"
  },
  {
    "description": "ModuleCard in failed state shows a thick red progress bar filling roughly full width, plus 'Failed X minutes ago' timestamp text — current shows only 'Generation failed. Please retry.' text",
    "affects_component": "ModuleCard",
    "change_type": "structure"
  },
  {
    "description": "Status badges now appear on ALL module cards for every state (Complete, Ready, Failed, Processing, Generating, Final, Edited, Active) — current only shows badges for edited, stale, and final states",
    "affects_component": "ModuleCard",
    "change_type": "addition"
  },
  {
    "description": "Cover Letter card secondary actions 'Regenerate' and 'Download' appear as plain text links (not ghost buttons) beside the primary 'View' CTA",
    "affects_component": "ModuleCard",
    "change_type": "structure"
  },
  {
    "description": "Value Proposition Report card secondary actions 'Export' and 'History' appear as plain text links beside the primary 'View' CTA — current secondary actions render as ghost buttons",
    "affects_component": "ModuleCard",
    "change_type": "structure"
  },
  {
    "description": "Module card title font appears slightly larger than current text-base — may need to increase to --text-card-title (1.25rem)",
    "affects_component": "ModuleCard",
    "change_type": "spacing"
  },
  {
    "description": "Card description text ('Review your responses to identified skill gaps', 'Your cover letter has been generated and is ready for review', etc.) — current ModuleCard uses subtitle prop; these appear as descriptive context lines not present in the current notStarted/processing states",
    "affects_component": "ModuleCard",
    "change_type": "addition"
  }
]
```

**Gap answers relevant to ModuleCard (all from applications-hub.json):**
```json
[
  {
    "question_id": "q1",
    "component": "ModuleCard",
    "topic": "loading_state",
    "answer": "Skeleton cards (6 placeholder cards matching card shape with shimmer)"
  },
  {
    "question_id": "q2",
    "component": "ModuleCard",
    "topic": "error_state",
    "answer": "Error banner above the card grid with a Retry button (inline)"
  },
  {
    "question_id": "q3",
    "component": "ModuleCard",
    "topic": "hover_state",
    "answer": "Light background tint change"
  },
  {
    "question_id": "q5",
    "component": "ModuleCard",
    "topic": "responsive",
    "answer": "2 columns on desktop, 1 column on mobile (below md breakpoint)"
  },
  {
    "question_id": "q6",
    "component": "ModuleCard",
    "topic": "edge_case",
    "answer": "'Progress' label on left + percentage on right (as shown in screenshots)"
  },
  {
    "question_id": "q7",
    "component": "ModuleCard",
    "topic": "edge_case",
    "answer": "Computed client-side from a 'failedAt' timestamp in the GET /applications/{id} response"
  },
  {
    "question_id": "q8",
    "component": "ModuleCard",
    "topic": "accessibility",
    "answer": "Keep both — aria attributes for screen readers + visible label for sighted users"
  },
  {
    "question_id": "q11",
    "component": "ModuleCard",
    "topic": "i18n",
    "answer": "Yes — add Hebrew translations for all new strings"
  },
  {
    "question_id": "q12",
    "component": "ModuleCard",
    "topic": "edge_case",
    "answer": "Underline on hover"
  },
  {
    "question_id": "q13",
    "component": "ModuleCard",
    "topic": "edge_case",
    "answer": "Screenshot artifact — keep existing module display names: Gap Analysis, Value Proposition Report, etc."
  },
  {
    "question_id": "q14",
    "component": "ModuleCard",
    "topic": "edge_case",
    "answer": "Same as current order — VPR → Cover Letter → CV Tailoring → Gap Analysis → Interview Prep → Company Research. No reordering required."
  },
  {
    "question_id": "q19",
    "component": "ModuleCard",
    "topic": "responsive",
    "answer": "Keep xl:grid-cols-3 — do not remove the 3-column breakpoint."
  }
]
```

**New i18n strings needed (Hebrew required per q11):**
- 'View Job Posting' / 'Show more' / 'Show less'
- 'Progress' (label prefix)
- 'Failed X minutes ago' (relative timestamp pattern)
- 'Still processing...' / 'Generating...'
- Context description lines per module state (ready, complete, edited)

---

### Component 2: JobDetailHeader (NEW COMPONENT)
File: components/JobDetailHeader/JobDetailHeader.tsx (to be created)
Tier: feature
Change type: new
Today's date: 2026-05-23

**Contract verification:** No entry — this is a new component, not in scope of existing blocked items. All data sourced from GET /applications/{id} which is already verified as available (see HubLayout contract entry).

**Source from diff analysis new_components_needed:**
```
"JobDetailHeader — card section showing job title, company name, Active badge,
'View Job Posting ↗' link, truncated description with 'Show more' toggle,
and '← Back' navigation link"
```

**Diff analysis: layout changes for JobDetailHeader:**
```json
{
  "description": "New job details header section at top of page: '← Back' link, job title (large heading), company name (subtitle text), 'View Job Posting ↗' orange link, truncated job description with 'Show more' expandable toggle — this section does not exist in current hub page",
  "affects_component": "unknown",
  "change_type": "new-component"
}
```

**Gap answers relevant to JobDetailHeader:**
```json
[
  {
    "question_id": "q4",
    "component": "JobDetailHeader",
    "topic": "edge_case",
    "question": "How should long job descriptions be handled in the Job Detail Header's 'Show more' toggle?",
    "answer": "Truncate at 3 lines, expand inline on click"
  },
  {
    "question_id": "q9",
    "component": "JobDetailHeader",
    "topic": "edge_case",
    "question": "Should the 'View Job Posting ↗' link open the external job URL in a new tab?",
    "answer": "Yes — new tab with rel='noopener noreferrer'"
  }
]
```

**Backend data contract (from HubLayout contract verification):**
- Job title: GET /applications/{application_id} response
- Company name: GET /applications/{application_id} response
- job_url: GET /applications/{application_id} response
- Job description: GET /applications/{application_id} response

**No blocked items for this component.**

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the two spec markdowns, back-to-back.
