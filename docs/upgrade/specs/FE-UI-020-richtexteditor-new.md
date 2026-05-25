---
spec_id: FE-UI-020
title: "new RichTextEditor — TipTap rich text input with toolbar and Markdown storage"
priority: high
status: draft
owner: frontend
created_at: 2026-05-23
updated_at: 2026-05-23
route: /applications/[id]/gap-analysis
component_file: src/frontend/components/RichTextEditor/RichTextEditor.tsx
tier: feature
---

## Problem Statement
**Current behavior:** Gap analysis answers are entered via a plain `<textarea>` element (page.tsx lines 255-261). No formatting is supported. Responses are stored and transmitted as plain text strings.

**Required behavior:** A TipTap-based rich text editor replaces the textarea. The editor provides a toolbar with Bold, Italic, Underline, Bullet List, and Numbered List buttons. Content is authored as rich text (HTML internally in TipTap) but stored and transmitted as Markdown. On mount, existing Markdown (or plain text) content is converted to TipTap's internal format. On change/save, TipTap content is serialized back to Markdown. Paste events strip all formatting except bold, italic, and lists. The editor supports ARIA attributes for accessibility.

**User impact:** Users can format their gap analysis answers with basic rich text, improving readability of responses used downstream by AI models for CV tailoring and interview prep.

## Evidence
**Mockup files:** gap analysis questionnaire form-rich textbox edit.png, gap analysis questionnaire form-rich textbox edit 2.png
**Diff analysis source:** docs/upgrade/diff-analysis/gap-analysis.json
**Gap answers source:** docs/upgrade/gap-answers/gap-analysis.json

## Architecture & Ownership Map
**Component file:** src/frontend/components/RichTextEditor/RichTextEditor.tsx (new)
**Page file(s):** app/applications/[id]/gap-analysis/page.tsx (indirectly, via GapQuestionCard)
**Tier:** feature — cascade risk: low (used only by GapQuestionCard initially; reusable for future routes)
**API dependencies:** None directly — content is passed to parent via onChange callback
**Imports this component:** GapQuestionCard (components/GapQuestionCard/GapQuestionCard.tsx)

## Fix Plan
**Files to modify:**
- `src/frontend/components/RichTextEditor/RichTextEditor.tsx` — new file
- `src/frontend/components/RichTextEditor/index.ts` — barrel export (new)
- `src/frontend/components/RichTextEditor/markdownSerializer.ts` — Markdown ↔ HTML conversion utilities (new)
- `src/frontend/tests/ui/unit/RichTextEditor.test.tsx` — new test file
- `package.json` — add TipTap dependencies

**Dependencies to install:**
- `@tiptap/react` — React bindings for TipTap
- `@tiptap/starter-kit` — base extensions (bold, italic, lists, paragraph, etc.)
- `@tiptap/extension-underline` — underline support (not in starter-kit)
- `turndown` — HTML-to-Markdown conversion
- `marked` or `markdown-it` — Markdown-to-HTML conversion (for loading existing content)
- `@types/turndown` — TypeScript types

**Props contract:**
```typescript
interface RichTextEditorProps {
  content: string;                    // Markdown string (initial content)
  onChange: (markdown: string) => void; // emits Markdown on every content change
  readOnly?: boolean;                 // disable editing (used during save)
  ariaLabelledBy?: string;            // ID of the element labeling this editor
  placeholder?: string;              // placeholder text when empty
}
```

**Behavior changes:**
1. **Initialization:** On mount, convert `content` prop (Markdown string) to HTML via `marked`/`markdown-it`, then set as TipTap editor content. Plain text (no Markdown syntax) passes through as-is — plain text is valid Markdown.
2. **Toolbar:** Render a horizontal toolbar above the editor with 5 buttons in order: Bold (B), Italic (I), Underline (U), Bullet List (unordered list icon), Numbered List (ordered list icon). Each button toggles its respective TipTap mark/node. Active marks show a visually distinct pressed/active state (e.g., `bg-surface-subtle` background).
3. **Content editing:** Standard TipTap contenteditable behavior. On every content change (via TipTap `onUpdate`), serialize the editor HTML to Markdown via `turndown` and call `onChange(markdown)`.
4. **Paste handling:** Register a TipTap paste-rules plugin or `handlePaste` extension that strips all formatting from pasted content except: bold (`<strong>`, `<b>`), italic (`<em>`, `<i>`), underline (`<u>`), bullet lists (`<ul>`, `<li>`), and numbered lists (`<ol>`, `<li>`). All other HTML tags (headings, images, tables, links, etc.) are stripped, preserving only text content.
5. **Read-only mode:** When `readOnly` is true, the editor is non-editable and the toolbar is hidden. Used by GapQuestionCard to display saved responses in read state and during the saving state.
6. **Empty state:** When the editor has no content, display placeholder text via TipTap's placeholder extension or CSS pseudo-element.
7. **Focus behavior:** Clicking inside the editor area focuses the TipTap editor. The editor container shows a focus ring (`ring-1 ring-primary-action border-primary-action`) matching the existing textarea focus style.
8. **Styling:** Editor area has `min-h-[120px]` to match the previous 4-row textarea. Toolbar has `border-b border-border-default` separator. Overall container has `border border-border-default rounded-lg overflow-hidden bg-card`.

**Non-goals (explicitly out of scope):**
- Image upload or embedding
- Link insertion UI
- Heading levels (only paragraph-level formatting)
- Code blocks or syntax highlighting
- Undo/redo buttons in toolbar (TipTap provides keyboard shortcuts by default)
- Collaborative editing

**Rollback plan:** Revert page/component file to prior version — no database or API changes

## Acceptance Criteria
- [ ] AC-001: Given the editor mounts with content="" (empty string), when it renders, then an empty editable area is shown with placeholder text and an empty toolbar above it
- [ ] AC-002: Given the editor mounts with content="Hello **world**" (Markdown), when it renders, then the editor displays "Hello " followed by bold "world"
- [ ] AC-003: Given the editor mounts with content="Plain text answer" (no Markdown), when it renders, then the editor displays "Plain text answer" without any formatting artifacts
- [ ] AC-004: Given the user selects text and clicks the Bold toolbar button, when the action completes, then the selected text is wrapped in bold formatting and the Bold button shows an active/pressed state
- [ ] AC-005: Given the user selects text and clicks the Italic toolbar button, when the action completes, then the selected text is italicized and the Italic button shows an active/pressed state
- [ ] AC-006: Given the user selects text and clicks the Underline toolbar button, when the action completes, then the selected text is underlined and the Underline button shows an active/pressed state
- [ ] AC-007: Given the user clicks the Bullet List toolbar button, when the action completes, then a bulleted list is started at the cursor position
- [ ] AC-008: Given the user clicks the Numbered List toolbar button, when the action completes, then a numbered list is started at the cursor position
- [ ] AC-009: Given the user types formatted content, when onChange fires, then the callback receives a valid Markdown string representing the current content (e.g., bold text as `**text**`, bullet items as `- item`)
- [ ] AC-010: Given the user pastes HTML content containing bold, italic, a heading, an image, and a table, when paste completes, then only bold and italic formatting are preserved; the heading renders as plain paragraph text; and the image and table are stripped (only text content retained)
- [ ] AC-011: Given the user pastes HTML with a `<ul>` containing `<li>` items, when paste completes, then the bullet list structure is preserved in the editor
- [ ] AC-012: Given readOnly is true, when the editor renders, then the content is displayed but not editable, and the toolbar is hidden
- [ ] AC-013: Given readOnly transitions from false to true (saving state), when the prop changes, then the editor becomes non-editable and the toolbar hides without losing content
- [ ] AC-014: Given the editor is focused, when a screen reader inspects the editor element, then it has role="textbox" (TipTap default), aria-multiline="true", and aria-labelledby set to the value of the ariaLabelledBy prop
- [ ] AC-015: Given the toolbar renders, when a screen reader reads each button, then Bold has aria-label="Bold", Italic has aria-label="Italic", Underline has aria-label="Underline", Bullet List has aria-label="Bullet list", Numbered List has aria-label="Numbered list"
- [ ] AC-016: Given the editor has content, when the user presses Ctrl+B / Cmd+B, then the selected text toggles bold (keyboard shortcut works alongside toolbar)
- [ ] AC-017: Given the editor area is empty and not focused, when the user views it, then placeholder text is visible (e.g., "Your answer..." in a muted color)
- [ ] AC-018: Given the user clicks inside the editor area, when focus is received, then a focus ring (ring-1 ring-primary-action) is displayed around the editor container

## States to Handle
| State | Trigger | Visual |
|-------|---------|--------|
| empty | No content, not focused | Placeholder text, toolbar enabled |
| has-content | User has typed/loaded content | Formatted content visible, toolbar enabled |
| focused | User clicks into editor | Focus ring visible, cursor in editor |
| read-only | readOnly prop is true | Content displayed, toolbar hidden, not editable |
| paste | User pastes content | Content sanitized per paste rules |

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
| AC-016 | integration | pre_merge | false |
| AC-017 | unit | pre_merge | false |
| AC-018 | unit | pre_merge | false |

## Baseline & Regression Budget
**blocked_regressions:**
- POST /jobs/{jobId}/gap-responses accepts both plain text (legacy) and Markdown (new) — flag if API change needed
- Existing responses display correctly after upgrade (existing plain text renders cleanly in TipTap)
- No regression on hub page (/applications/[id]) that links to this route

**allowed_deltas:** {}

## Traceability Matrix
| requirement_id | code_reference | test_reference | verification_type | blocking_gate | result |
|---|---|---|---|---|---|
| AC-001 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-002 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-003 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-004 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-005 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-006 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-007 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-008 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-009 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-010 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-011 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-012 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-013 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-014 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-015 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-016 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | integration | pre_merge | pending |
| AC-017 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |
| AC-018 | components/RichTextEditor/RichTextEditor.tsx:TBD | tests/ui/unit/RichTextEditor.test.tsx | unit | pre_merge | pending |

## Rollback Trigger Matrix
| trigger_id | condition | action |
|---|---|---|
| RT-001 | Any blocking AC flips pass→fail post-deploy | Revert component file, re-open spec |
| RT-002 | New non-2xx response on POST /jobs/{jobId}/gap-responses | Block deploy, investigate |
| RT-003 | Markdown content sent via POST /jobs/{jobId}/gap-responses causes API validation failure | Block deploy; if API rejects Markdown in the `response` field, this spec is blocked until backend accepts Markdown |

## Design Notes
- **API Markdown acceptance (CRITICAL):** The POST /jobs/{jobId}/gap-responses endpoint currently receives `{ responses: [{question_id, response}] }` where `response` is a plain text string. Markdown will now be sent in this field (e.g., `**bold** text\n- list item`). Developer must confirm the API accepts Markdown without validation errors before merging this spec. If the API strips or rejects Markdown, a backend change is required first.
- **Markdown serialization library choice:** `turndown` is the most popular HTML-to-Markdown library. For Markdown-to-HTML on load, `marked` is lightweight and fast. Both are well-maintained. Consider `markdown-it` if more control over parsing rules is needed.
- **TipTap bundle size:** `@tiptap/react` + `@tiptap/starter-kit` + `@tiptap/extension-underline` adds ~40-60KB gzipped. Since this is used on a single route behind dynamic import in GapQuestionCard's edit mode, the impact is acceptable. Consider lazy-loading the editor component (`React.lazy`) if initial page load metrics are a concern.
- **Underline in Markdown:** Standard Markdown has no underline syntax. `turndown` will need a custom rule to serialize `<u>` tags. Options: (a) use HTML `<u>` inline in Markdown output, (b) use a custom syntax like `++underline++`, (c) drop underline from Markdown serialization and only preserve it in the editor session. Recommend option (a) — HTML inline in Markdown is valid and will render correctly when loaded back into TipTap.
- **Paste rule testing:** AC-010 and AC-011 are difficult to test in jsdom/vitest because clipboard events require manual construction. Consider marking these as integration tests if unit-level mocking proves unreliable.
