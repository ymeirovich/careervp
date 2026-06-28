# Handoff Prompt — Spec: Edit Mode for Tailored CV and Cover Letter

## Session context

You are writing a **functional specification** for a new Claude Code session. The codebase is a Next.js 14 (App Router) frontend at `src/frontend/`. The user wants inline edit mode for two artifact pages that currently display in read-only mode. No edit implementation exists yet.

## Background

Two artifact detail pages exist:

| Page | Route | Current state |
|---|---|---|
| Tailored CV | `app/applications/[id]/cv-tailored/page.tsx` | Read-only. Renders structured `CVSections` or raw `tailored_cv` string. |
| Cover Letter | `app/applications/[id]/cover-letter/page.tsx` | Unknown — check if it exists; if not, note it as out-of-scope for this spec but flag it. |

Both pages are navigated to from the hub (`app/applications/[id]/page.tsx`) via secondary actions. The hub adapter (`adapters/mapApplicationDataToHubState.ts`) already emits `'Edit'` and `'View'` as secondary action labels for `ready` and `complete` statuses. Currently both actions push the same route with no mode parameter.

## What to produce

Write a Markdown spec document at `docs/upgrade/specs/FE-EDIT-MODE-029-edit-mode-spec.md` covering:

### 1. URL contract
Define how the mode is communicated (e.g. `?mode=edit` query param). The spec must state:
- View route: `/applications/{jobId}/cv-tailored?id={artifactId}`
- Edit route: `/applications/{jobId}/cv-tailored?id={artifactId}&mode=edit`
- Same pattern for cover-letter page (if it exists).

### 2. Hub wiring
How the hub page (`app/applications/[id]/page.tsx`) should distinguish between `'View'` and `'Edit'` button clicks when building the route via `ARTIFACT_ROUTES`. The spec should say: append `&mode=edit` when `action.label === 'Edit'`.

### 3. Tailored CV edit behaviour
The data shape is `CVSections` (see `lib/types.ts`). The spec must cover:

- **Editable fields**: `summary` (textarea), `skills.technical` (tag list / comma-separated textarea), each `experience[i].bullets[j].text` (textarea per bullet), and optionally `contact.*` fields.
- **Non-editable fields** in edit mode: ATS score, keyword lists (read-only context).
- **Dirty state**: track whether any field has been changed since load.
- **Save action**: `PATCH /cv-tailored/{artifactId}` (define the request body schema — delta of changed fields only, or full `CVSections`). If the endpoint does not exist yet, mark it as a backend dependency and describe the expected contract.
- **Cancel action**: discard changes, revert to loaded data (no navigation).
- **UX**: edit fields should be inline (replace rendered text with `<textarea>` or `<input>` in place). No separate edit page.

### 4. Cover Letter edit behaviour
Check whether `app/applications/[id]/cover-letter/page.tsx` exists. If it does:
- The cover letter result is a plain text string. Edit mode = a single `<textarea>` replacing the `<pre>` block.
- Same save/cancel/dirty-state contract as above, with `PATCH /cover-letter/{artifactId}`.

If the page does not yet exist, note it as a dependency (cover letter view page must be built first) and write the spec for it too (view + edit combined).

### 5. Acceptance criteria (testable)
Write ≥ 8 numbered ACs that a QA agent or Playwright test can verify:
- Clicking "View" → URL has no `mode=edit`
- Clicking "Edit" → URL has `mode=edit`
- Page loads in edit mode when `mode=edit` is in URL
- Editable fields are rendered as inputs/textareas
- Dirty indicator appears after a change
- Save sends correct PATCH request and transitions to read mode
- Cancel reverts changes without navigating away
- Navigating to view URL shows read-only mode

### 6. Out of scope for V1 edit mode
- Collaborative editing
- Version history / undo history beyond single-session revert
- Rich-text formatting

### 7. Backend dependency table
List every new or changed API endpoint the spec requires, with method, path, request body, response body, and owner (backend).

## Files to read before writing the spec

- `src/frontend/app/applications/[id]/cv-tailored/page.tsx` — current read-only implementation
- `src/frontend/app/applications/[id]/page.tsx` lines 148–180 — ARTIFACT_ROUTES and action wiring
- `src/frontend/adapters/mapApplicationDataToHubState.ts` lines 123–131 — secondary action labels
- `src/frontend/lib/types.ts` — `CVSections`, `CoverLetterStatusResponse`

## Output

A single file: `docs/tasks/FE-EDIT-MODE-001-edit-mode-spec.md`
