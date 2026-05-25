# Phase 5 — Spec Writing
**Model:** Opus
**When:** After Phase 4 contract verification is complete
**Run:** One component per conversation, or batch components of the same tier together
**Order:** tokens.css changes → ui-primitive tier → layout tier → feature tier

---

## How to Use

1. Open a new conversation
2. Paste the prompt below with placeholders filled
3. Paste the relevant diff-analysis entry, gap-answers, and contract-verification entry for this component

---

## Prompt

```
ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec file. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.

TASK: Write a complete upgrade spec for {COMPONENT_NAME} on route {ROUTE}.

THINK before writing:
1. What does the component currently do? (from component map)
2. What visual changes are required? (from diff analysis)
3. What functional gaps were resolved? (from gap answers)
4. Are any changes BLOCKED by contract verification? (exclude them entirely)
5. What makes each AC machine-verifiable? (can it be asserted in a test?)
6. What are the regression risks? (what currently works that must keep working?)

THEN produce the spec in this exact format:

---
spec_id: FE-UI-{N}
title: "Upgrade {COMPONENT_NAME} — {one-line description of change}"
priority: high | medium | low
status: draft
owner: frontend
created_at: {today}
updated_at: {today}
route: {ROUTE}
component_file: {FILE_PATH}
tier: ui-primitive | layout | feature | shared

## Problem Statement
**Current behavior:** (what the component does and looks like now)
**Required behavior:** (what it must do and look like after upgrade)
**User impact:** (what the user experiences differently)

## Evidence
**Mockup files:** {screenshot filenames}
**Diff analysis source:** docs/upgrade/diff-analysis/{route-slug}.json
**Gap answers source:** docs/upgrade/gap-answers/{route-slug}.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** {all pages that import this component}
**Tier:** {tier} — cascade risk: {high if ui-primitive/shared, medium if layout, low if feature}
**API dependencies:** {list endpoints this component's data flows from}
**Imports this component:** {list all page files from component-map.json}

## Fix Plan
**Files to modify:**
- {exact file paths, one per line}

**Behavior changes:**
- {bullet: what changes, be specific}

**Non-goals (explicitly out of scope):**
- {anything excluded, especially BLOCKED items from contract verification}

**Rollback plan:** Revert {component file} to prior version — no database or API changes

## Acceptance Criteria
(Each AC must be machine-verifiable — no "should look correct" or "should feel responsive")

- [ ] AC-001: Given [state], when [action], then [exact observable outcome]
- [ ] AC-002: ...

Include ACs for:
- Every visual change from diff analysis (not blocked)
- Every gap interview answer (loading state, error state, empty state, etc.)
- Keyboard navigation and ARIA (frontend_spec rule FE_A11Y)
- Hebrew string translation if new i18n strings introduced
- Responsive behaviour if gap answer specified a layout change

## States to Handle
(list all — check each has a corresponding AC)
- default |  loading | error | empty | hover | focus | disabled | {others from gap answers}

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |
| AC-002 | integration | pre_merge | false |
| AC-003 | live | post_deploy | true |

verification_type options: static | unit | integration | contract | live
blocking_gate options: pre_merge | pre_deploy | post_deploy

## Baseline & Regression Budget
**blocked_regressions:**
- No new non-2xx responses on API calls used by this component
- No visual regression on components outside this spec's scope
- Existing test suite passes without modification (tests/ui/unit/, tests/unit/)

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
(Values that could not be determined from the screenshot — require human decision before implementation)
- Color: {token name} — desired value unknown, needs design decision
- {other ambiguities from diff analysis}
---

## CONTEXT

Component: {COMPONENT_NAME}
File: {FILE_PATH}
Tier: {TIER}
Today's date: {DATE}

Diff analysis entry (paste from docs/upgrade/diff-analysis/{route-slug}.json):
{PASTE component_changes ENTRY FOR THIS COMPONENT}

Gap answers (paste from docs/upgrade/gap-answers/{route-slug}.json):
{PASTE RELEVANT ENTRIES}

Contract verification entry (paste from docs/upgrade/contract-verification.json):
{PASTE RESULTS ENTRY FOR THIS COMPONENT — blocked items must be excluded from spec}

Component map entry:
- If component-map.json is in project knowledge: write "see component-map.json, route: {ROUTE}"
- If using Claude Code: paste the JSON object where "route" == "{ROUTE}"
- For shared components (ErrorBoundary, Spinner, Button): also paste shared_component_summary entry for this component, plus all page entries that list it in their "components" array

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the spec markdown.
```

---

## Batching Guide

Group components by tier for efficiency. Suggested batches:

| Batch | Components | Why |
|---|---|---|
| 0 | tokens.css changes only | Must precede all component specs |
| 1 | ErrorBoundary, Spinner, Button | Shared — highest cascade risk |
| 2 | AppSidebar (new nav items) | Layout — affects every page |
| 3 | HubLayout, AppHeader | Layout tier |
| 4 | ModuleCard (all 6 module variants) | Feature — hub page focus |
| 5 | ExportDropdown | Feature — 4 module pages |
| 6 | Dashboard components | StatsRow, JobsTable, UsageGate, NewApplicationModal |
| 7 | New page components | Applications list, Cover Letters list, Tailored CVs list |
| 8 | Gap analysis components | Rich textbox, question counter |
| 9 | Billing + Settings components | Lowest cascade risk |

Run one batch per conversation. Batch 0 (token changes) produces a spec for `styles/tokens.css` modifications — treat it as a single component spec for the design token file.
