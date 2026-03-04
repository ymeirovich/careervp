# Codex Prompt: Gap Questions GET Returns Empty (Write Works, Read Fails)

## Context

This is a comprehensive fix for the "write works, read fails" bug in Gap Questions.

**This prompt merges:**
- CODEX_PROMPT.md (original gap questions bug)
- CODEX_PROMPT_GAP_GET_EMPTY.md (duplicate analysis)
- CODEX_PROMPT_WRITE_READ_BUGS (comprehensive analysis)

## Bug Summary

- POST `/jobs/{job_id}/gap-questions` successfully generates and saves questions
- GET `/jobs/{job_id}/gap-questions` returns empty `{cv_id: null, questions: []}`
- This is the SAME pattern as Cover Letter List and Interview Prep Status bugs

## Test Evidence

```
=== RESPONSE test_generate_gap_questions ===
POST /jobs/18ff3113-8a85-4090-92a3-34bb052fe7b8/gap-questions
Status: 200
Generated 10 questions

=== RESPONSE test_get_gap_questions ===
GET /jobs/18ff3113-8a85-4090-92a3-34bb052fe7b8/gap-questions
Status: 200
Response: {
  "job_id": "18ff3113-8a85-4090-92a3-34bb052fe7b8",
  "cv_id": null,
  "questions": []
}
FAILED
```

## Root Cause

The bug is in `src/backend/careervp/dal/dynamo_dal_handler.py` at **line 480**:

```python
# In list_gap_questions_by_prefix() method (line 460-485)
if job_id:
    items = [item for item in items if item.get('job_id') == job_id]
```

This strict filter compares job_id exactly. If there's any mismatch (whitespace, case, format), the filter returns empty.

### How It Should Work

1. **POST (Generate)** saves with:
   - `pk`: user_id
   - `sk`: `ARTIFACT#GAP_ANALYSIS#{cv_id}#{job_id}`
   - `job_id`: from request

2. **GET (Retrieve)** queries:
   - pk = user_id
   - sk begins with `ARTIFACT#GAP_ANALYSIS#`
   - Then filters by job_id

## Your Task

### 1. Verify the Root Cause

Read these files:
- `src/backend/careervp/handlers/gap_handler.py` - `get_questions()` function (lines 238-282)
- `src/backend/careervp/dal/dynamo_dal_handler.py` - `list_gap_questions_by_prefix()` (lines 460-485)

Confirm that line 480 is causing the issue:
```python
if job_id:
    items = [item for item in items if item.get('job_id') == job_id]
```

### 2. Implement the Fix

**Option A: Remove the strict filter**
The prefix query is sufficient - remove the job_id filter entirely:
```python
# In list_gap_questions_by_prefix(), remove lines 479-480:
# OLD:
if job_id:
    items = [item for item in items if item.get('job_id') == job_id]

# NEW: (remove the filter, or make it optional/less strict)
# The prefix query already narrows results sufficiently
```

**Option B: Fix the filter to be less strict**
If filter is needed, make it more lenient:
```python
# Instead of exact match, use contains
if job_id:
    items = [item for item in items if job_id in str(item.get('job_id', ''))]
```

### 3. Verify No Regression

After the fix:
- POST still generates and saves questions
- GET retrieves the same questions that were saved

### 4. Add Tests

**Unit Test:**
- Test that `list_gap_questions_by_prefix` returns items when job_id matches

**Integration Test:**
- In `docs/refactor/live_tests/test_05_gap_analysis.py`:
  1. POST to generate gap questions
  2. GET to retrieve the questions
  3. Verify questions array is NOT empty

## Files to Modify

| File | Line | Change |
|------|------|--------|
| dynamo_dal_handler.py | ~480 | Remove or fix strict job_id filter |

## Test File Reference

- `careervp/live-test-results25.log` - contains test evidence
- `docs/refactor/live_tests/test_05_gap_analysis.py` - gap analysis tests
- `src/backend/careervp/handlers/gap_handler.py` - handler
- `src/backend/careervp/dal/dynamo_dal_handler.py` - DAL

## Hints

- The filter at line 480 is too strict
- The prefix query already filters by sort key - additional filter is redundant
- This is the SAME pattern as cover letter list bug (DAL stripping fields)
- Check if job_id format differs between POST and GET (case, whitespace)
