# Multi-CV Management — Backend Changes

**Status:** Implemented  
**Branch:** `front/vpr-ttl-s3`  
**Date:** 2026-04-12

---

## Summary

Users can now upload, store, retrieve, and delete multiple CVs. Each CV carries a
human-readable `label` derived from the uploaded filename. All existing artifact
generation APIs (VPR, Cover Letter, CV Tailoring, Gap Analysis) already accept a
`cv_id` parameter, so no changes were needed on the generation side.

---

## What Changed

### 1. `UserCV` Model — new `label` field

**File:** `src/backend/careervp/models/cv.py`

Added an optional `label: str | None` field to the `UserCV` Pydantic model. The label
is set automatically during upload from the source filename (minus extension). For
example, uploading `Senior_Dev_Resume.pdf` produces `label = "Senior_Dev_Resume"`.

Existing CVs without a label will have `label = None` — no migration needed since
the field is optional.

### 2. Upload Handler — label derivation

**File:** `src/backend/careervp/handlers/cv_upload_handler.py`

The OpenAPI upload path (`{cv_content, file_name}`) now passes `file_name` through
the normalization step. After parsing, the handler sets:

```python
user_cv.label = os.path.splitext(os.path.basename(file_name))[0]
```

The legacy upload path (`{file_content, file_type}`) also checks for a `file_name`
key in the request body as a fallback.

### 3. DAL — three new methods

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_all_cvs` | `(user_id) -> list[UserCV]` | Returns all CVs for a user, sorted by `updated_at` desc. Skips malformed items. |
| `get_cv_by_id` | `(user_id, cv_id) -> UserCV \| None` | Direct key lookup. Tries `userId/cvId` schema, falls back to `pk/sk`. |
| `delete_cv` | `(user_id, cv_id) -> tuple[bool, str \| None]` | Deletes the DynamoDB record. Returns `(deleted, source_file_key)`. |

A shared `_normalize_cv_item` static method was extracted to deduplicate key
normalization (`userId` -> `user_id`, `cvId` -> `cv_id`) across all CV read paths.

### 4. New API Endpoints

**File:** `src/backend/careervp/handlers/user_handler.py`

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/users/me/cv/<cv_id>` | GET | 200 + CV JSON, 404 | Fetch a single CV by its ID. |
| `/users/me/cv/<cv_id>` | DELETE | 204, 404 | Delete a CV. Also removes the S3 source file if present. |

Both endpoints require authentication (401 if missing) and read `TABLE_NAME` and
`CV_BUCKET_NAME` from environment variables.

### 5. Tests

**File:** `src/backend/tests/unit/test_cv_management.py`

15 unit tests covering:

- DAL: `get_all_cvs` (multiple, empty), `get_cv_by_id` (found, not found),
  `delete_cv` (success, not found)
- Handler: GET single CV (success, 404, 401), DELETE CV (success with S3 cleanup,
  404, 401)
- Model: `label` field acceptance, default, filename derivation

---

## Existing Endpoints (unchanged)

| Endpoint | Notes |
|----------|-------|
| `GET /users/me/cv` | Already returns `{cvs: [...]}` array. No changes needed. |
| `POST /users/me/cv` | Upload endpoint. Now sets `label` on the parsed CV. |
| `POST /vpr/generate` | Already accepts `cv_id` in request body. |
| `POST /cover-letter/generate` | Already accepts `cv_id`. |
| `POST /cv-tailoring/generate` | Already accepts `cv_id`. |
| `POST /gap-analysis/questions` | Already accepts `cv_id`. |

---

## DynamoDB Schema

No table schema changes. The CVs table uses `userId` (partition) / `cvId` (sort) as
primary key. The `label` field is stored as a regular attribute — no GSI needed since
CVs are always queried by user.

Items written by `save_cv` include both `userId`/`cvId` and legacy `pk`/`sk` keys for
backward compatibility.

---

## Frontend Integration Notes (for future UI overhaul)

When the frontend is updated to support multi-CV:

1. **List all CVs:** Call `GET /users/me/cv` — returns `{cvs: [...], cursor: ""}`.
   Each CV now includes a `label` field for display.
2. **Fetch single CV:** Call `GET /users/me/cv/{cvId}` for detail view.
3. **Delete CV:** Call `DELETE /users/me/cv/{cvId}` — returns 204 on success.
4. **CV selector:** When generating artifacts, pass the selected `cv_id` to the
   generation APIs. The frontend currently hardcodes `cv.cv_id` from `getCV()`
   (which returns only `cvs[0]`). Update `api.ts` to expose the full array.
5. **Artifact provenance:** Each artifact's `input_data` already records which
   `cv_id` was used. Display this to warn users when viewing artifacts generated
   with a different CV than the currently selected one.
