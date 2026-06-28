# Handoff Prompt — Tests: Bug Fixes + Edit Mode

## Session context

You are writing **unit and integration tests** for a Claude Code session. The project is a Next.js 14 frontend at `src/frontend/` with Vitest + React Testing Library. Backend is Python/Pydantic at `src/backend/`.

Run existing tests first to confirm baseline: `cd src/frontend && npm run test:unit`

---

## Part A — Tests for already-fixed bugs

### Bug 1: Cover Letter `company_research_id` empty string

**What was fixed:**
- `src/frontend/hooks/useGenerateModule.ts`: `company_research_id` no longer defaults to `''` when `companyResearchId` is undefined — it passes `undefined`, which omits the field from the JSON body.
- `src/frontend/lib/types.ts`: `CoverLetterRequest.company_research_id` is now `company_research_id?: string` (optional).
- `src/backend/careervp/models/api_models.py`: `company_research_id` changed from `str = Field(min_length=1)` to `str | None = None`.

**Tests to write:**

1. **Frontend unit test** — `src/frontend/hooks/useGenerateModule.test.ts`:
   - Mock `api.generateCoverLetter` and capture what it was called with.
   - When `generate({ cvId, vprId, gapResponseIds })` is called WITHOUT `companyResearchId`, assert `company_research_id` is `undefined` (not `''`) in the captured call.
   - When `generate({ ..., companyResearchId: 'some-id' })` is called, assert `company_research_id === 'some-id'`.

2. **Backend unit test** — `src/backend/tests/unit/models/test_api_models.py` (create if missing):
   - `CoverLetterRequest` parses successfully when `company_research_id` is omitted.
   - `CoverLetterRequest` parses successfully when `company_research_id` is a non-empty string.
   - `CoverLetterRequest` parses successfully when `company_research_id` is `null` / `None`.
   - `CoverLetterRequest` used to reject `""` — confirm that `""` now either passes (as None normalisation) or fails gracefully; document the chosen behaviour.

---

### Bug 2: Gap analysis `PROCESSING_BLOCKED` shown when complete

**What was fixed:**
- `src/frontend/hooks/useApplicationHub.ts`: after building `moduleData` for other modules, the hook now sets `moduleData.gapAnalysis` based on `appData.gap_analysis.responses.length`:
  - `responses.length > 0` → `status: 'completed'` → module derives to `'ready'`
  - `questions.length > 0` (but no responses) → `status: 'processing'`
  - Neither → not set → derives to `'notStarted'` (unchanged)

**Tests to write:**

1. **Unit test for `mapApplicationDataToHubState`** — `src/frontend/adapters/mapApplicationDataToHubState.test.ts` (add cases):
   - When `moduleData.gapAnalysis` has `status: 'completed'`, `hubStatus` must NOT be `'PROCESSING_BLOCKED'`.
   - When `moduleData.gapAnalysis` is absent AND `baseCV` is `'ready'`, `hubStatus` must be `'PROCESSING_BLOCKED'`.
   - When `moduleData.gapAnalysis` has `status: 'processing'`, `moduleStatuses.gapAnalysis` must be `'processing'` and `hubStatus` must be `'LOADING'`.

2. **Integration test for `useApplicationHub`** — `src/frontend/hooks/useApplicationHub.test.ts` (add cases):
   - Mock GET `/applications/{jobId}` to return a payload where `gap_analysis.responses` has 10 items. Assert that the returned `hubState.modules.gapAnalysis.status` is `'ready'` (not `'notStarted'`).
   - Mock GET `/applications/{jobId}` to return a payload where `gap_analysis.questions` has items but `responses` is empty. Assert `hubState.modules.gapAnalysis.status` is `'processing'`.
   - Mock GET `/applications/{jobId}` to return a payload where both are empty. Assert `hubState.modules.gapAnalysis.status` is `'notStarted'`.
   - In the first case, assert `hubState.hubStatus` is NOT `'PROCESSING_BLOCKED'`.

---

## Part B — Tests for Edit Mode (spec-driven, write after spec FE-EDIT-MODE-001 is approved)

These tests depend on the spec at `docs/tasks/FE-EDIT-MODE-001-edit-mode-spec.md`. Write them AFTER that spec is merged.

### Unit tests

1. **`ARTIFACT_ROUTES` mode wiring** (in `app/applications/[id]/page.tsx` or extracted util):
   - `'View'` action → route does NOT contain `mode=edit`.
   - `'Edit'` action → route DOES contain `mode=edit`.

2. **CV Tailored page mode detection**:
   - When `searchParams.get('mode') === 'edit'`, the page renders `<textarea>` elements (not just `<p>` / `<span>`).
   - When `searchParams.get('mode')` is absent, the page renders read-only elements.

3. **Dirty state**:
   - Initially no dirty indicator.
   - After changing a field value, dirty indicator appears.
   - After clicking Cancel, dirty indicator disappears and field reverts.

4. **Save**:
   - Clicking Save calls `PATCH /cv-tailored/{artifactId}` with the changed fields.
   - After successful save, page transitions to read mode.
   - On API error, error message is displayed and mode stays edit.

### Playwright / e2e tests (add to `test:e2e` suite)

1. Navigate to hub for an application with a completed Tailored CV.
2. Click "View" → assert URL does not include `mode=edit` → assert no `<textarea>` visible.
3. Go back. Click "Edit" → assert URL includes `mode=edit` → assert `<textarea>` elements are visible.
4. Edit a field, click Cancel → assert field reverts.
5. Edit a field, click Save → assert network request fired → assert read mode shown.

---

## Key files to read

- `src/frontend/hooks/useGenerateModule.ts`
- `src/frontend/hooks/useApplicationHub.ts`
- `src/frontend/adapters/mapApplicationDataToHubState.ts`
- `src/frontend/app/applications/[id]/cv-tailored/page.tsx`
- `src/backend/careervp/models/api_models.py` (lines 328–343)
- Existing test files for patterns: `src/frontend/**/*.test.ts`

## Commands

```bash
# Frontend tests
cd src/frontend && npm run test:unit

# Backend tests
cd src/backend && uv run pytest tests/unit/ -v --tb=short
```
