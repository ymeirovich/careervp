# Phase 5 — Batch I: Gap Analysis
# Components: GapAnalysisContent (modify), GapQuestionCard (new), RichTextEditor (new)
# Model: Opus | New conversation per batch
# Route: /applications/[id]/gap-analysis

---

ROLE: Senior frontend spec author writing a UI upgrade spec conforming to spec_best_practices.yaml.
OUTPUT: Markdown spec files — one per component. No prose outside the spec format.
MODEL NOTE: Use careful reasoning — spec quality determines implementation correctness.
COMPLEXITY NOTE: GapAnalysisContent is a major restructure (per-question editing, rich text, removal of global edit bar). GapQuestionCard and RichTextEditor are tightly coupled. Write all three specs before finalizing any — they share state and props contracts that must be consistent.

TASK: Write THREE complete upgrade specs — GapAnalysisContent (modify), GapQuestionCard (new), RichTextEditor (new).

THINK before writing each spec:
1. GapAnalysisContent: What global state changes? Progress bar, per-question editing, removal of sticky header, removal of Generate button, impact badges moved to collapsed section.
2. GapQuestionCard: What per-question state machine exists? (unanswered → editing → saved → editing again). What props does it need from GapAnalysisContent?
3. RichTextEditor: TipTap, toolbar B/I/U/bullet/numbered list, Markdown storage, paste stripping, ARIA. How does it communicate content to GapQuestionCard?
4. Multi-editor guard: what happens when one editor is open and the user clicks 'Answer' on another? (prompt to save or discard)
5. What is BLOCKED? Nothing blocked from contract verification for this route.

THEN produce ALL THREE specs in sequence using this exact format:

---
spec_id: FE-UI-{N}
title: "{modify/new} {COMPONENT_NAME} — {one-line description}"
priority: high | medium | low
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]/gap-analysis
component_file: {FILE_PATH}
tier: feature

## Problem Statement
**Current behavior:** ...
**Required behavior:** ...
**User impact:** ...

## Evidence
**Mockup files:** gap analysis questionnaire form.png, gap analysis questionnaire form continued.png, gap analysis questionnaire form question counter read state.png, gap analysis questionnaire form-rich textbox edit.png, gap analysis questionnaire form-rich textbox edit 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/gap-analysis.json
**Gap answers source:** docs/upgrade/gap-answers/gap-analysis.json

## Architecture & Ownership Map
**Component file:** {path}
**Page file(s):** app/applications/[id]/gap-analysis/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses, GET /applications/{id}
**Imports this component:** {from component-map.json}

## Fix Plan
**Files to modify:** ...
**Behavior changes:** ...
**Non-goals (explicitly out of scope):** ...
**Rollback plan:** Revert page/component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given ..., when ..., then ...

Include ACs for loading, error, empty states; per-question state machine; multi-editor guard; keyboard/ARIA; Hebrew i18n; responsive.

## States to Handle
(for GapAnalysisContent) loading | error | empty | read | saving
(for GapQuestionCard) unanswered | editing | saving | saved | error
(for RichTextEditor) empty | has-content | focused | paste

## Verification Contract
| requirement_id | verification_type | blocking_gate | artifact_required |
|---|---|---|---|
| AC-001 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /jobs/{jobId}/gap-responses accepts both plain text (legacy) and Markdown (new) — note: flag if API change needed
- Existing responses display correctly after upgrade (existing plain text renders cleanly in TipTap)
- No regression on hub page (/applications/[id]) that links to this route

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | {file}:TBD | tests/ui/unit/{ComponentName}.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx response on POST /jobs/{jobId}/gap-responses | Block deploy, investigate |

## Design Notes
- {unresolved ambiguities}
---

STOP: Output all three specs back-to-back with no prose between them.

---

## CONTEXT

### Component 1: GapAnalysisContent
File: app/applications/[id]/gap-analysis/page.tsx
Tier: feature
Change type: modify (major restructure)
Today's date: 2026-05-23

**Contract verification entry:**
```json
{
  "route": "/applications/[id]/gap-analysis",
  "component": "GapAnalysisContent",
  "change_type": "modify",
  "backend_classification": "yes",
  "resolution": "Questions from GET /jobs/{jobId}/gap-questions; per-question save via POST /jobs/{jobId}/gap-responses; application context (back link, breadcrumb) from GET /applications/{id} — all three endpoints exist in Swagger",
  "in_scope": true
}
```

**Diff analysis entry:**
```json
{
  "component": "GapAnalysisContent",
  "file": "app/applications/[id]/gap-analysis/page.tsx",
  "tier": "feature",
  "change_type": "modify",
  "visual_description": "Major restructure: page title larger, subtitle changed, progress bar added, back link replaces back button, global edit/save bar removed in favor of per-question editing, impact badges and destination radios removed from primary UI (moved to collapsed section per gap answers), generate button not shown",
  "interaction_states_visible": ["read state with answered questions", "read state with unanswered questions", "edit state with rich text editor", "edit state with save button"],
  "interaction_states_needed_but_not_shown": ["loading state", "error state", "saving state", "empty state", "generating state"],
  "backend_data_required": "GET /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses, GET /applications/{id}",
  "backend_available": "yes"
}
```

**Diff analysis layout changes:**
```json
[
  {"description": "Page title 'Gap Analysis Questions' is now larger/bold", "change_type": "spacing"},
  {"description": "Subtitle text changed to 'Answer some questions to fill in gaps between your CV and this role'", "change_type": "spacing"},
  {"description": "Progress bar added below subtitle showing 'X out of Y answered' with orange fill", "change_type": "addition"},
  {"description": "'← Back' link added at top-left above subtitle, replacing '← Back to Hub' button in top-right action bar", "change_type": "structure"},
  {"description": "The sticky header bar with global Edit/Save/Cancel buttons is removed — editing is now per-question", "change_type": "removal"},
  {"description": "'Generate Questions' button is not visible — removed (questions pre-generated)", "change_type": "removal"},
  {"description": "Impact/Probability badges and CV_IMPACT/INTERVIEW_MVP_ONLY radio buttons NOT visible — moved to collapsed/advanced section per gap answers", "change_type": "removal"},
  {"description": "Question cards use rounded-xl (--radius-card: 16px) borders with subtle shadow", "change_type": "spacing"}
]
```

**Gap answers — gap-analysis:**
```json
[
  {"question_id": "q1", "component": "GapAnalysisContent", "topic": "loading_state", "answer": "Skeleton cards (3-4 placeholder question cards with shimmer)"},
  {"question_id": "q2", "component": "GapAnalysisContent", "topic": "error_state", "answer": "Inline error banner above question list with Retry button"},
  {
    "question_id": "q3",
    "component": "GapAnalysisContent",
    "topic": "empty_state",
    "answer": "Gap questions pre-generated on application submit. If no questions: show message directing user back to hub to retry. 'There was an error, contact site administrator.' No 'Generate Questions' button anywhere."
  },
  {"question_id": "q8", "component": "GapAnalysisContent", "topic": "responsive", "answer": "Same layout, full-width cards stacked vertically"},
  {"question_id": "q11", "component": "GapAnalysisContent", "topic": "i18n", "answer": "Yes — Hebrew translations for: 'Gap Analysis Questions', 'Answer some questions to fill in gaps...', 'X out of Y answered', 'Answer', 'Edit', 'Save', '← Back'"},
  {"question_id": "q14", "component": "GapAnalysisContent", "topic": "empty_state", "answer": "No 'Generate Questions' button anywhere. Empty state directs back to hub."},
  {"question_id": "q13", "component": "AppHeader", "topic": "credits_display", "answer": "Trial-plan application credits only. Call GET /users/me/usage → applications.used / (used + remaining). isUnlimited=true shows 'Unlimited' for paid subscribers. (AppHeader spec in Batch B owns this AC.)"}
]
```

---

### Component 2: GapQuestionCard (new)
File: components/GapQuestionCard/GapQuestionCard.tsx (new)
Tier: feature
Change type: new (extracts per-question card from GapAnalysisContent questions.map loop)
Today's date: 2026-05-23

**Diff analysis layout changes for GapQuestionCard:**
```json
[
  {"description": "Each question card shows question number and text on left with 'Answer' button (orange solid) on right when unanswered, or 'Edit' button (outlined) when already answered", "change_type": "structure"},
  {"description": "Answered questions display saved answer text below question in a light-background block", "change_type": "structure"},
  {"description": "Edit mode shows rich text editor (toolbar with B, I, U, bullet list, numbered list) instead of plain textarea", "change_type": "structure"},
  {"description": "Save button in edit mode is orange with floppy disk icon, positioned inline to the right", "change_type": "structure"},
  {"description": "Impact/Probability badges: read-only display badges showing LLM-assigned values, visible in collapsed header row", "change_type": "structure"},
  {"description": "CV_IMPACT/INTERVIEW_MVP_ONLY radios: moved to collapsed/advanced section, default sends CV_IMPACT if user never opened section", "change_type": "structure"}
]
```

**Gap answers — gap-analysis:**
```json
[
  {"question_id": "q6", "component": "GapQuestionCard", "topic": "edge_case", "answer": "Save only the current question's answer (individual POST per question)"},
  {"question_id": "q7", "component": "GapQuestionCard", "topic": "edge_case", "answer": "Keep both destination radios and impact/probability badges but show in a collapsed/advanced section"},
  {"question_id": "q10", "component": "GapQuestionCard", "topic": "accessibility", "answer": "Toolbar buttons get aria-labels; editor gets aria-labelledby pointing to question text"},
  {"question_id": "q12", "component": "GapQuestionCard", "topic": "edge_case", "answer": "When editing one question and clicking 'Answer' on another: prompt to save or discard first"},
  {"question_id": "q15", "component": "GapQuestionCard", "topic": "edge_case", "answer": "If user saves without opening advanced section: send hardcoded CV_IMPACT as default destination"},
  {"question_id": "q16", "component": "GapQuestionCard", "topic": "edge_case", "answer": "Impact and probability badges are read-only. Visible in collapsed header row even before advanced section opened."}
]
```

---

### Component 3: RichTextEditor (new)
File: components/RichTextEditor/RichTextEditor.tsx (new)
Tier: feature
Change type: new (TipTap-based, used inside GapQuestionCard)
Today's date: 2026-05-23

**Diff analysis layout change:**
```json
{
  "description": "Edit mode now shows a rich text editor (toolbar with B, I, U, bullet list, numbered list) instead of a plain textarea",
  "affects_component": "GapQuestionCard",
  "change_type": "structure"
}
```

**Diff analysis new_components_needed:**
```
"RichTextEditor — toolbar-based rich text input (Bold, Italic, Underline, Bullet List, Numbered List)
replacing plain textarea; may use TipTap or similar"
```

**Gap answers — gap-analysis:**
```json
[
  {"question_id": "q4", "component": "RichTextEditor", "topic": "edge_case", "answer": "TipTap (headless, extensible, React-native)"},
  {"question_id": "q5", "component": "RichTextEditor", "topic": "edge_case", "answer": "Markdown — convert to/from HTML in editor. Storage format: Markdown. Display format: HTML via TipTap."},
  {"question_id": "q9", "component": "RichTextEditor", "topic": "edge_case", "answer": "Strip formatting on paste but keep bold, italic, lists only"},
  {"question_id": "q10", "component": "GapQuestionCard", "topic": "accessibility", "answer": "Toolbar buttons get aria-labels; editor gets aria-labelledby pointing to question text"}
]
```

**Markdown/HTML contract note:**
- Existing responses stored as plain text must render correctly when loaded into TipTap (plain text is valid Markdown)
- New responses saved as Markdown are sent to POST /jobs/{jobId}/gap-responses in the `response` field
- API change risk: if API validates response as plain text, Markdown may fail. Flag in Design Notes: developer must confirm API accepts Markdown in the response field before implementation.

## PROHIBITED
- Do not write ACs that cannot be expressed as a test assertion
- Do not include BLOCKED items from contract verification anywhere in the spec
- Do not omit the Verification Contract table
- Do not omit the Traceability Matrix (results may all be "pending")
- Do not write vague ACs ("should look correct", "should be responsive")
- Do not set status to anything other than "draft"

STOP: Output only the three spec markdowns, back-to-back.
