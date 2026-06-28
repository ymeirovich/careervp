# FE-EDIT-MODE-001 — Edit Mode for Tailored CV and Cover Letter

**Status:** Draft  
**Date:** 2026-06-05  
**Scope:** Inline edit mode for two read-only artifact pages.

---

## 1. URL Contract

Edit mode is communicated via a `mode=edit` query parameter appended to the existing artifact URL.

| Page | View URL | Edit URL |
|---|---|---|
| Tailored CV | `/applications/{jobId}/cv-tailored?id={artifactId}` | `/applications/{jobId}/cv-tailored?id={artifactId}&mode=edit` |
| Cover Letter | `/applications/{jobId}/cover-letter?id={artifactId}` | `/applications/{jobId}/cover-letter?id={artifactId}&mode=edit` |

Rules:
- Absence of `mode` param (or any value other than `edit`) renders the page in read-only mode.
- Pages detect mode via `useSearchParams().get('mode') === 'edit'`.
- Navigating directly to the edit URL must render the page in edit mode without requiring a prior view-mode visit.

---

## 2. Hub Wiring

**File:** `src/frontend/app/applications/[id]/page.tsx`

**Current behaviour (lines 165–174):**  
Both `'View'` and `'Edit'` secondary action labels push the same route via `routeFn(moduleState.resultUrl)`. No mode parameter is appended.

**Required change:**  
In `buildSecondaryActions`, when `action.label === 'Edit'`, append `&mode=edit` to the destination URL:

```ts
if ((action.label === 'View' || action.label === 'Edit') && routeFn) {
  const base = routeFn(moduleState.resultUrl);
  const dest = action.label === 'Edit' ? `${base}&mode=edit` : base;
  return { ...action, onClick: () => router.push(dest) };
}
```

**Secondary action labels by module status** (from `adapters/mapApplicationDataToHubState.ts`):
- `ready` → `['Edit', 'Regenerate']`
- `complete` → `['Edit', 'History']`
- `stale` → `['View']`
- `edited` → `['Regenerate', 'History']`
- `final` → `['History']`

This means the `'Edit'` button appears on `ready` and `complete` statuses. The `'View'` button on `stale` always routes without `mode=edit`.

---

## 3. Tailored CV Edit Behaviour

### 3.1 Data Shape

Source type: `CVSections` (from `src/frontend/lib/types.ts`):

```ts
interface CVSections {
  contact: CVContact;       // { name, email, phone, linkedin, location }
  summary: string;
  skills: CVSkills;         // { technical: string[], soft: string[] }
  experience: CVExperience[]; // each has bullets: CVBullet[]
  education: CVEducation[];
  certifications: CVCertification[];
  languages?: string[] | null;
}
```

### 3.2 Editable Fields

| Field | Input type | Notes |
|---|---|---|
| `summary` | `<textarea>` | Auto-resize to content; replaces the `<p>` in `CVDocument` |
| `skills.technical` | `<textarea>` (comma-separated) | Render as comma-separated string; parse back on save |
| `experience[i].bullets[j].text` | `<textarea>` per bullet | One textarea per bullet inline; `source` and `user_edited` preserved |
| `contact.name` | `<input type="text">` | Optional; replaces the `<h1>` in the header |
| `contact.email` | `<input type="text">` | Optional |
| `contact.phone` | `<input type="text">` | Optional |
| `contact.linkedin` | `<input type="text">` | Optional |
| `contact.location` | `<input type="text">` | Optional |

### 3.3 Non-Editable Fields in Edit Mode

The following are displayed read-only even when `mode=edit`:
- ATS score, ATS grade, ATS colour badge
- `keywords_matched` and `keywords_missing` lists

They provide context to guide edits but must not be interactive.

### 3.4 Fallback: Raw `tailored_cv` String

When `cv_sections` is absent but `result.tailored_cv` is present, the page currently renders the raw string in a `<pre>`. In edit mode, replace the `<pre>` with a single full-page `<textarea>` containing the raw string. Save sends the full updated string as `tailored_cv` (see §3.6).

### 3.5 Dirty State

- On entering edit mode, snapshot the loaded data as `originalData`.
- A boolean `isDirty` flag is `true` when any field value differs from `originalData`.
- Display a visible dirty indicator (e.g., badge "Unsaved changes") in the page header while `isDirty` is true.
- `isDirty` resets to `false` after a successful save or after cancel.

### 3.6 Save Action

**Backend dependency — endpoint does not exist yet.**

```
PATCH /users/me/cv-tailored/{artifactId}
```

Request body (full `CVSections` — not delta; simpler to implement and validate):

```json
{
  "cv_sections": { /* full CVSections object */ }
}
```

For the raw-string fallback:
```json
{
  "tailored_cv": "<edited full text>"
}
```

Expected response: `200 OK` with updated `CVTailoredStatusResponse` (same shape as `GET`).

Frontend behaviour on save:
1. Disable save/cancel buttons and show inline spinner.
2. `PATCH` the artifact.
3. On success: update local state with response data, set `isDirty = false`, remove `mode=edit` from the URL (via `router.replace`) so the page transitions to read mode.
4. On error: show an inline error message; remain in edit mode with current field values.

### 3.7 Cancel Action

- Discard all unsaved changes by resetting field values to `originalData`.
- Set `isDirty = false`.
- Remove `mode=edit` from the URL via `router.replace` (same as after save, but without a network call).
- No navigation away from the page.

### 3.8 UX: Inline Editing

Editable fields replace their read-only counterparts in place within the same `CVDocument` layout. No separate edit page or modal. The structural document layout (section headings, order of sections) stays intact and is not editable in V1.

---

## 4. Cover Letter Edit Behaviour

**Cover letter page exists** at `src/frontend/app/applications/[id]/cover-letter/page.tsx`.

### 4.1 Current State

Renders `fullText` (a plain string) as a `<p>` with `whitespace-pre-wrap`. Data is fetched via `api.getCoverLetter(artifactId)`, returning `CoverLetterStatusResponse` with `result?.cover_letter`.

### 4.2 Edit Mode

In edit mode, replace the `<p data-testid="cover-letter-text">` with a single `<textarea>` containing `fullText`. The textarea should be full-width and tall enough to show the entire letter without an internal scrollbar (e.g., `rows` set dynamically or `min-h` via Tailwind).

### 4.3 Dirty State

Same contract as §3.5.

### 4.4 Save Action

**Backend dependency — endpoint does not exist yet.**

```
PATCH /users/me/cover-letter/{artifactId}
```

Request body:
```json
{
  "cover_letter": "<edited full text>"
}
```

Expected response: `200 OK` with updated `CoverLetterStatusResponse`.

Frontend behaviour on save: identical to §3.6 (spinner, success → read mode, error → stay in edit).

### 4.5 Cancel Action

Identical to §3.7: revert textarea to `originalData`, remove `mode=edit` from URL.

---

## 5. Acceptance Criteria

1. **View route has no mode param.** Clicking the "View" button on the hub navigates to `/applications/{jobId}/cover-letter?id={artifactId}` with no `mode=edit`. The page renders in read-only mode.
2. **Edit route has mode param.** Clicking the "Edit" button on the hub navigates to the same URL with `&mode=edit` appended. The page renders in edit mode immediately.
3. **Direct URL loads edit mode.** Navigating directly to a URL containing `mode=edit` (e.g., via browser address bar or deep link) renders the page in edit mode without requiring interaction.
4. **Editable fields are rendered as inputs.** In edit mode, `summary`, `skills.technical`, and each `experience[i].bullets[j].text` are rendered as `<textarea>` elements; `contact.*` fields are rendered as `<input>` elements. In read mode, all of these are rendered as text.
5. **Non-editable context is read-only in edit mode.** ATS score, ATS grade, and keyword lists are not interactive in edit mode.
6. **Dirty indicator appears after a change.** After modifying any field, a dirty indicator (e.g., "Unsaved changes" badge) becomes visible in the page header.
7. **Save sends correct PATCH and transitions to read mode.** Clicking Save issues `PATCH /users/me/cv-tailored/{artifactId}` (or `cover-letter`) with the updated payload. On `200`, the URL loses `mode=edit`, the page renders in read-only mode with updated content, and the dirty indicator disappears.
8. **Cancel reverts changes and transitions to read mode without navigation.** Clicking Cancel resets all fields to their original loaded values, removes `mode=edit` from the URL, and hides the dirty indicator. The user remains on the same page. No network request is made.
9. **Save failure stays in edit mode.** If the PATCH returns an error, the page stays in edit mode, the user's edits are preserved, and an error message is shown.
10. **View URL shows read-only mode.** Navigating from edit mode to the view URL (e.g., after cancel) renders only non-interactive text elements. No `<textarea>` or `<input>` elements are present.

---

## 6. Out of Scope for V1 Edit Mode

- Collaborative or multi-user editing
- Version history or undo history beyond single-session revert (cancel resets to loaded state only)
- Rich-text formatting (bold, italic, lists as HTML)
- Editing structural fields: section order, adding/removing experience entries or education entries
- Editing `skills.soft`, `education.*`, `certifications.*`, or `languages` (can be added in V2)
- Autosave / draft persistence across page refreshes

---

## 7. Backend Dependency Table

| # | Method | Path | Request body | Response body | Owner | Notes |
|---|---|---|---|---|---|---|
| 1 | `PATCH` | `/users/me/cv-tailored/{artifactId}` | `{ cv_sections?: CVSections, tailored_cv?: string }` | `CVTailoredStatusResponse` | Backend | One of `cv_sections` or `tailored_cv` must be present. Backend should recalculate ATS score on save and return updated result. If recalculation is too expensive, return the stored `ats_score` unchanged. |
| 2 | `PATCH` | `/users/me/cover-letter/{artifactId}` | `{ cover_letter: string }` | `CoverLetterStatusResponse` | Backend | Overwrites `result.cover_letter`. Should update `updated_at` and, if the module status model includes it, set status to `edited`. |

**Auth:** Both endpoints must be authenticated and scoped to the requesting user (same as all existing artifact endpoints).

**Status model note:** If the hub module status model supports an `edited` state (the `TailoredCvListItem.status` type already includes `'edited'`), the backend should transition the artifact to `edited` on save. The hub adapter (`getSecondaryLabels`) maps `edited` → `['Regenerate', 'History']`, which removes the `'Edit'` button. This is intentional: once edited, regeneration is the next action.
