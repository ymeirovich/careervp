---
spec_id: FE-UI-018
title: "modify GapAnalysisContent — restructure to per-question editing with progress bar"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]/gap-analysis
component_file: src/frontend/app/applications/[id]/gap-analysis/page.tsx
tier: feature
---

## Problem Statement
**Current behavior:** GapAnalysisContent uses a global edit/view mode toggle via a sticky header bar with Edit/Save/Cancel buttons. All questions enter edit mode simultaneously. A "Generate Questions" button appears when no questions exist. Impact badges and destination radios are shown inline in each question row. The page title is small and uses a back button labeled "← Back to Hub" in the top-right action bar.

**Required behavior:** Per-question editing replaces the global edit mode — each question card has its own Answer/Edit/Save lifecycle managed by the new GapQuestionCard child component. The sticky header bar with global Edit/Save/Cancel buttons is removed. A progress bar ("X out of Y answered") replaces the inline text counter. The page title is larger/bold, the subtitle changes to "Answer some questions to fill in gaps between your CV and this role", and a "← Back" link replaces the back button (top-left, above subtitle). The "Generate Questions" button is removed entirely — questions are pre-generated on application submit. Impact badges move to a collapsed section inside GapQuestionCard. An empty state directs the user back to the hub instead of prompting question generation.

**User impact:** Users gain focused per-question editing flow, eliminating accidental edits to other questions. Progress tracking is visually prominent. Removing the generate button simplifies the UI for the common case where questions already exist.

## Evidence
**Mockup files:** gap analysis questionnaire form.png, gap analysis questionnaire form continued.png, gap analysis questionnaire form question counter read state.png, gap analysis questionnaire form-rich textbox edit.png, gap analysis questionnaire form-rich textbox edit 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/gap-analysis.json
**Gap answers source:** docs/upgrade/gap-answers/gap-analysis.json

## Architecture & Ownership Map
**Component file:** src/frontend/app/applications/[id]/gap-analysis/page.tsx
**Page file(s):** app/applications/[id]/gap-analysis/page.tsx
**Tier:** feature — cascade risk: low (route-scoped)
**API dependencies:** GET /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses, GET /applications/{id}
**Imports this component:** ErrorBoundary (components/ErrorBoundary/ErrorBoundary.tsx), Spinner (components/ui/Spinner.tsx). After upgrade also imports: GapQuestionCard (components/GapQuestionCard/GapQuestionCard.tsx), ProgressBar (components/ui/ProgressBar.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/app/applications/[id]/gap-analysis/page.tsx` — major restructure of GapAnalysisContent
- `src/frontend/tests/unit/gap-analysis-page.test.tsx` — update tests for new structure

**Behavior changes:**
1. Remove `FormMode` type and global `mode` state. Replace with `editingQuestionId: string | null` state to track which single question is being edited.
2. Remove `handleGenerate` function, `generating` state, and "Generate Questions" button entirely.
3. Remove sticky header bar (lines 178-209) with global Edit/Save/Cancel.
4. Replace inline answered-count text with `<ProgressBar>` component using `value={(answeredCount / questions.length) * 100}` and label "X out of Y answered".
5. Replace "← Back to Hub" button with a "← Back" link (`<a>` or Next.js `<Link>`) positioned top-left above the subtitle.
6. Update page title to use larger/bolder styling (`text-2xl font-bold`).
7. Update subtitle text to "Answer some questions to fill in gaps between your CV and this role".
8. Replace the inline `questions.map` rendering with `<GapQuestionCard>` component delegation.
9. Implement multi-editor guard: track `editingQuestionId` at this level, pass to each GapQuestionCard; when a card requests edit while another is editing, show a confirmation dialog ("Save or discard changes to question N?").
10. Update empty state: remove generate-button reference, show message "There was an error, contact site administrator." with a link back to hub.
11. Update loading state to skeleton cards (3-4 placeholder cards with shimmer animation) instead of a centered Spinner.
12. Add error state as inline error banner above question list with a Retry button that re-fetches questions.
13. Update question card container to use `rounded-xl` borders with subtle shadow (`shadow-sm`).

**Non-goals (explicitly out of scope):**
- AppHeader credits display (owned by FE-UI-004)
- Changes to the POST /jobs/{jobId}/gap-responses API contract
- Export functionality (gap analysis has no export)
- Generating questions on-demand (removed from UI)

**Rollback plan:** Revert page/component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given the page is loading, when the user navigates to /applications/[id]/gap-analysis, then 3-4 skeleton placeholder cards with shimmer animation are displayed (no centered spinner)
- [ ] AC-002: Given questions have loaded, when the page renders, then the page title "Gap Analysis Questions" is displayed with text-2xl font-bold styling
- [ ] AC-003: Given questions have loaded, when the page renders, then the subtitle reads "Answer some questions to fill in gaps between your CV and this role"
- [ ] AC-004: Given questions have loaded, when the page renders, then a "← Back" link is displayed top-left above the subtitle, and clicking it navigates to /applications/{jobId}
- [ ] AC-005: Given 2 of 5 questions are answered, when the page renders, then a ProgressBar displays with value 40 and label text "2 out of 5 answered"
- [ ] AC-006: Given the page has rendered, when the user looks for a global Edit/Save/Cancel bar, then no sticky header bar with those buttons exists
- [ ] AC-007: Given the page has rendered, when the user looks for a "Generate Questions" button, then no such button exists anywhere on the page
- [ ] AC-008: Given no questions exist (empty array from API), when the page renders, then an empty-state message "There was an error, contact site administrator." is shown with a link back to /applications/{jobId}
- [ ] AC-009: Given the API call to GET /jobs/{jobId}/gap-questions fails, when the page renders, then an inline error banner is displayed above the question list area with a "Retry" button
- [ ] AC-010: Given the user clicks "Retry" on the error banner, when the retry executes, then GET /jobs/{jobId}/gap-questions is called again and the error banner is replaced with the result (questions or error)
- [ ] AC-011: Given question 3 is in editing mode, when the user clicks "Answer" on question 5, then a confirmation dialog prompts the user to save or discard changes on question 3 before opening question 5 for editing
- [ ] AC-012: Given questions have loaded, when the page renders, then each question is rendered by a GapQuestionCard component with props: question, questionIndex, response, isEditing, onRequestEdit, onSave, onCancel
- [ ] AC-013: Given the page renders in Hebrew locale, when the user views the page, then all static strings (title, subtitle, progress label, back link, empty-state message, error banner, retry button) are displayed in Hebrew
- [ ] AC-014: Given a mobile viewport (< 768px), when the page renders, then question cards stack vertically at full width with no horizontal overflow
- [ ] AC-015: Given a GapQuestionCard calls onSave with a question_id and response text, when the save executes, then POST /jobs/{jobId}/gap-responses is called with the single question's response, and on success the local state updates and editingQuestionId resets to null
- [ ] AC-016: Given the page renders, when a screen reader reads the progress bar, then role="progressbar" with aria-valuenow, aria-valuemin=0, aria-valuemax=100, and an aria-label of "X out of Y answered" are present

## States to Handle
| State | Trigger | Visual |
|-------|---------|--------|
| loading | Initial page load | 3-4 skeleton cards with shimmer |
| error | API fetch failure | Inline error banner + Retry button |
| empty | API returns 0 questions | Error message + link to hub |
| read | Questions loaded, none editing | Question cards in read mode |
| saving | GapQuestionCard triggers save | Delegated to GapQuestionCard saving state |

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
| AC-013 | unit | pre_merge | false |
| AC-014 | unit | pre_merge | false |
| AC-015 | integration | pre_merge | false |
| AC-016 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /jobs/{jobId}/gap-responses accepts both plain text (legacy) and Markdown (new) — flag if API change needed
- Existing responses display correctly after upgrade (existing plain text renders cleanly in TipTap)
- No regression on hub page (/applications/[id]) that links to this route
- Navigation from hub to gap-analysis and back must continue to work
- Previously saved gap responses must load and display without data loss

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-002 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-003 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-004 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-005 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-006 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-007 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-008 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-009 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-010 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-011 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-012 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-013 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-014 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |
| AC-015 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | integration | pre_merge | pending |
| AC-016 | src/frontend/app/applications/[id]/gap-analysis/page.tsx:TBD | tests/unit/gap-analysis-page.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx response on POST /jobs/{jobId}/gap-responses | Block deploy, investigate |
| RT-003 | Previously saved gap responses fail to display after upgrade | Revert component file, investigate data rendering path |

## Design Notes
- The multi-editor guard confirmation dialog design is not shown in mockups. Implementation should use a simple browser `confirm()` dialog or a lightweight modal. Clarify with design if a custom modal is preferred.
- The existing `savedToast` success notification pattern is removed from global save. Per-question save feedback should be handled within GapQuestionCard (inline success indicator or brief highlight).
- The `cv` state and `getCV()` call can be removed since "Generate Questions" is gone — unless other functionality still needs it. Verify during implementation.
- The existing `GapResponse` type uses `response` field (not `answer`). The API call `saveGapResponses` sends `{ responses: [{question_id, response}] }`. Per-question save should call the same endpoint with a single-item array, or a dedicated single-response endpoint if available.
- Progress bar uses the existing `ProgressBar` component (`components/ui/ProgressBar.tsx`) with `color="primary"` (orange). The label "X out of Y answered" should be rendered as visible text alongside the bar, not only as sr-only.
