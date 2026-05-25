---
spec_id: FE-UI-019
title: "new GapQuestionCard — per-question card with edit lifecycle and collapsed advanced section"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]/gap-analysis
component_file: src/frontend/components/GapQuestionCard/GapQuestionCard.tsx
tier: feature
---

## Problem Statement
**Current behavior:** Question rendering is an inline `questions.map` block inside GapAnalysisContent (page.tsx lines 212-269). All questions share a single global edit/view mode. Each question row shows impact/probability badges inline and destination radios (CV_IMPACT/INTERVIEW_MVP_ONLY) directly in edit mode. The answer input is a plain `<textarea>`.

**Required behavior:** Each question is rendered by a dedicated GapQuestionCard component with its own state machine (unanswered → editing → saving → saved). Unanswered cards show an orange "Answer" button; answered cards show the saved response text and an outlined "Edit" button. Edit mode replaces the read view with a RichTextEditor (spec FE-UI-020) and an inline orange "Save" button with floppy-disk icon. Impact/probability badges are read-only and visible in a collapsed header row. Destination radios (CV_IMPACT/INTERVIEW_MVP_ONLY) are in a collapsed "Advanced" section that defaults to CV_IMPACT if never opened. The multi-editor guard is coordinated by the parent GapAnalysisContent via `isEditing`/`onRequestEdit` props.

**User impact:** Per-question editing prevents accidental changes to other answers. The collapsed advanced section reduces visual noise for the common case while preserving power-user access to destination choice.

## Evidence
**Mockup files:** gap analysis questionnaire form.png, gap analysis questionnaire form continued.png, gap analysis questionnaire form question counter read state.png, gap analysis questionnaire form-rich textbox edit.png, gap analysis questionnaire form-rich textbox edit 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/gap-analysis.json
**Gap answers source:** docs/upgrade/gap-answers/gap-analysis.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/GapQuestionCard/GapQuestionCard.tsx (new)
**Page file(s):** app/applications/[id]/gap-analysis/page.tsx
**Tier:** feature — cascade risk: low (used only by GapAnalysisContent on this route)
**API dependencies:** POST /jobs/{jobId}/gap-responses (save is triggered by parent, but the card emits the data)
**Imports this component:** GapAnalysisContent (app/applications/[id]/gap-analysis/page.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/components/GapQuestionCard/GapQuestionCard.tsx` — new file
- `src/frontend/components/GapQuestionCard/index.ts` — barrel export (new)
- `src/frontend/tests/ui/unit/GapQuestionCard.test.tsx` — new test file

**Props contract:**
```typescript
interface GapQuestionCardProps {
  question: GapQuestion;            // from lib/types.ts
  questionIndex: number;            // 0-based, displayed as questionIndex+1
  response: string | null;          // existing saved response text (plain text or Markdown)
  destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '';  // existing saved destination
  isEditing: boolean;               // controlled by parent (single-editor guard)
  onRequestEdit: () => void;        // ask parent for edit permission
  onSave: (data: { questionId: string; response: string; destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' }) => Promise<void>;
  onCancel: () => void;             // cancel editing, revert to read state
}
```

**Behavior changes:**
1. **Read state (unanswered):** Show question number + text on left. Orange solid "Answer" button on right. No response block below.
2. **Read state (answered/saved):** Show question number + text on left. Outlined "Edit" button on right. Below the question text, display the saved response in a light-background block (`bg-surface-subtle rounded-lg p-3`). Response text rendered via TipTap read-only mode (handles both plain text and Markdown).
3. **Editing state:** Replace the read view content area with RichTextEditor (FE-UI-020). Pre-populate with existing response if editing an answered question. Show orange "Save" button with floppy-disk icon inline to the right of the editor. Show "Cancel" text button to the left of Save.
4. **Saving state:** Save button shows spinner and is disabled. Editor is read-only during save.
5. **Error state:** If onSave rejects, show inline error text below editor ("Failed to save. Please try again.") and re-enable the Save button.
6. **Impact/probability badges:** Read-only display in the card header row, always visible (even in collapsed state). Use existing `impactBadgeClass` logic. Format: "Impact: HIGH", "Prob: MEDIUM".
7. **Advanced collapsed section:** A disclosure widget (`<details>`/`<summary>` or custom collapsible) labeled "Advanced options" below the editor in edit mode. Contains CV_IMPACT and INTERVIEW_MVP_ONLY radio buttons. Default selection: CV_IMPACT if destination is empty or unset.
8. **Card styling:** `rounded-xl border border-border-default shadow-sm p-4` with `bg-card`.
9. **Multi-editor guard interaction:** When `isEditing` is false and user clicks Answer/Edit, call `onRequestEdit()`. Parent decides whether to grant (flipping `isEditing` to true) or prompt to save/discard the other editing card first.

**Non-goals (explicitly out of scope):**
- API call execution (parent GapAnalysisContent owns the POST call)
- Progress bar (owned by GapAnalysisContent)
- RichTextEditor internals (owned by FE-UI-020)
- Reordering or drag-and-drop of question cards

**Rollback plan:** Revert page/component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given a question with no saved response, when the card renders in read state, then the question number and text are shown with an orange solid "Answer" button on the right
- [ ] AC-002: Given a question with a saved response "I have 5 years of Python experience", when the card renders in read state, then the response text is displayed in a light-background block below the question, and an outlined "Edit" button is shown on the right
- [ ] AC-003: Given isEditing is true, when the card renders, then a RichTextEditor replaces the read-state content, pre-populated with the existing response (if any), and "Save" (orange, with icon) and "Cancel" buttons are visible
- [ ] AC-004: Given the user is editing and clicks "Save", when the save is in progress, then the Save button shows a spinner and is disabled, and the editor becomes read-only
- [ ] AC-005: Given the onSave promise rejects, when the save fails, then an inline error message "Failed to save. Please try again." appears below the editor, and the Save button is re-enabled
- [ ] AC-006: Given the user is editing and clicks "Cancel", when cancel executes, then the editor content reverts to the last saved response (or empty if unanswered) and the card returns to read state via onCancel
- [ ] AC-007: Given a question has impact="HIGH" and probability="MEDIUM", when the card renders (any state), then badges "Impact: HIGH" (green-tinted) and "Prob: MEDIUM" (yellow-tinted) are visible in the card header row
- [ ] AC-008: Given the user is editing, when they expand the "Advanced options" section, then CV_IMPACT and INTERVIEW_MVP_ONLY radio buttons are shown, with CV_IMPACT selected by default if no prior destination was set
- [ ] AC-009: Given the user saves without ever opening the Advanced section, when onSave is called, then the destination value sent is "CV_IMPACT"
- [ ] AC-010: Given isEditing is false, when the user clicks the "Answer" or "Edit" button, then onRequestEdit is called (the card does not self-transition to editing)
- [ ] AC-011: Given a saved response contains plain text (legacy format), when rendered in read state, then the text displays correctly without formatting artifacts
- [ ] AC-012: Given a saved response contains Markdown (bold, italic, lists), when rendered in read state via TipTap, then formatting is preserved visually
- [ ] AC-013: Given the card renders, when a screen reader reads the editor area, then the editor has aria-labelledby pointing to the question text element
- [ ] AC-014: Given the card renders, when a screen reader reads the toolbar buttons in edit mode, then each button (Bold, Italic, Underline, Bullet list, Numbered list) has an aria-label
- [ ] AC-015: Given the page renders in Hebrew locale, when the card is displayed, then "Answer", "Edit", "Save", "Cancel", "Advanced options", "Include in CV", "Interview Only", and "Failed to save. Please try again." are in Hebrew
- [ ] AC-016: Given a mobile viewport (< 768px), when the card renders, then the Answer/Edit button wraps below the question text if needed, and the card uses full width

## States to Handle
| State | Trigger | Visual | Transitions to |
|-------|---------|--------|----------------|
| unanswered | No saved response | Question + "Answer" button | editing (via onRequestEdit) |
| saved | Has saved response | Question + response block + "Edit" button | editing (via onRequestEdit) |
| editing | Parent sets isEditing=true | RichTextEditor + Save/Cancel | saving (on save click), unanswered/saved (on cancel) |
| saving | User clicks Save | Editor read-only, Save spinner | saved (on success), error (on failure) |
| error | onSave rejects | Inline error below editor, Save re-enabled | saving (on retry), unanswered/saved (on cancel) |

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
| AC-015 | unit | pre_merge | false |
| AC-016 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /jobs/{jobId}/gap-responses accepts both plain text (legacy) and Markdown (new) — flag if API change needed
- Existing responses display correctly after upgrade (existing plain text renders cleanly in TipTap)
- No regression on hub page (/applications/[id]) that links to this route

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-002 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-003 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-004 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-005 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-006 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-007 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-008 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-009 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-010 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-011 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-012 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-013 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-014 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-015 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |
| AC-016 | components/GapQuestionCard/GapQuestionCard.tsx:TBD | tests/ui/unit/GapQuestionCard.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx response on POST /jobs/{jobId}/gap-responses | Block deploy, investigate |
| RT-003 | Saved responses display garbled or missing text after upgrade | Revert component file, investigate TipTap rendering of legacy plain text |

## Design Notes
- The floppy-disk icon on the Save button is referenced in mockups but the icon library is not specified. Use `lucide-react` Save icon if available in the project, otherwise a simple SVG.
- Read-state response rendering uses TipTap in read-only/non-editable mode to handle both plain text and Markdown. This creates a dependency on TipTap being loaded even in read state. If bundle-size is a concern, consider a lightweight Markdown-to-HTML renderer for read-only display and only load TipTap when entering edit mode.
- The `onSave` callback is async and returns a Promise. The card must await it to know success/failure. The parent GapAnalysisContent is responsible for calling the API and resolving/rejecting the promise.
- The `destination` default of "CV_IMPACT" when the Advanced section is never opened means the card must track whether the user explicitly chose a destination. If `destination` prop is empty and the user never opens Advanced, the emitted save data should include `destination: "CV_IMPACT"`.
