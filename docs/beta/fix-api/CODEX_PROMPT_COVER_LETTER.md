# Codex Prompt: Cover Letter List Returns Empty After Successful Generation

## Context

This document contains analysis and a task for Codex to validate, investigate, and fix a bug where:
- POST `/cover-letter/generate` successfully generates a cover letter
- GET `/cover-letter/{id}/status` successfully returns the cover letter
- GET `/cover-letters` returns empty array `[]`

## Test Evidence

```
=== RESPONSE test_cover_letter_async_polling ===
{
  "test_name": "test_cover_letter_async_polling",
  "endpoint": "GET /cover-letter/343e7d04-4885-4f20-a1ee-7fd88a48fa77/status",
  "status_code": 200,
  "response": {
    "id": "343e7d04-4885-4f20-a1ee-7fd88a48fa77",
    "status": "completed",
    "result": {
      "cover_letter": "Dear Hiring Team,\n\nI am excited to apply for this role..."
    }
  }
}
✓ Cover letter polling - Completed after 0s
PASSED

=== RESPONSE test_list_cover_letters ===
{
  "test_name": "test_list_cover_letters",
  "endpoint": "GET /cover-letters",
  "status_code": 200,
  "response": {
    "cover_letters": []
  }
}
✓ GET /cover-letters - Found 0 cover letter(s)
PASSED
```

## My Hypothesis

### The Bug is in the DAL's list_cover_letters() method

In `dynamo_dal_handler.py` line 452:
```python
results = [item.get('cover_letter') or item for item in items]
```

This returns only the **nested `cover_letter` field** from each DynamoDB item, discarding the top-level fields like `cv_id`, `job_id`, `created_at`, `pk`, `sk`.

### Why Status Works But List Doesn't

The status endpoint (`get_cover_letter_status`) uses `_find_cover_letter_item()` which:
1. Calls `_list_cover_letter_items()` to get items
2. Uses `_matches_cover_letter_id()` to find the matching item
3. `_matches_cover_letter_id()` has fallback logic to extract ID from nested payloads (lines 475-481)

The list endpoint (`list_cover_letters`) directly passes items to `_build_cover_letter_list_item()` which expects top-level fields (`cv_id`, `job_id`, `created_at`, `sk`) that no longer exist because the DAL stripped them.

## Key Files to Examine

1. `src/backend/careervp/dal/dynamo_dal_handler.py`
   - `list_cover_letters()` method (~line 437-457)
   - Line 452: `results = [item.get('cover_letter') or item for item in items]`

2. `src/backend/careervp/handlers/cover_letter_handler.py`
   - `list_cover_letters()` (~line 323-337)
   - `_list_cover_letter_items()` (~line 463-468)
   - `_build_cover_letter_list_item()` (~line 553-578)

## Your Task

### 1. Validate My Analysis
- Read the relevant code sections
- Confirm or refute my hypothesis about line 452 in dynamo_dal_handler.py

### 2. If You Agree With My Analysis
Implement ONE of these fixes:

**Option A (Preferred):** Fix the DAL to return full items
```python
# In dynamo_dal_handler.py list_cover_letters(), line 452
# Change from:
results = [item.get('cover_letter') or item for item in items]
# To:
results = items  # Return full DynamoDB items
```

**Option B:** Fix the handler to handle both cases
- Modify `_build_cover_letter_list_item()` to extract fields from nested payload when top-level fields are missing

### 3. If You Disagree
- Propose an alternative root cause
- Explain why the list returns empty
- Implement your proposed fix

### 4. Add Tests
Create or update tests to prevent regression:

**Unit Test (recommended):**
- Add test in `tests/cover-letter/unit/` that verifies `list_cover_letters` returns items with all required fields

**Integration Test:**
- Add test in `docs/refactor/live_tests/test_07_cover_letter.py` that:
  1. Generates a cover letter
  2. Lists all cover letters
  3. Asserts the generated cover letter appears in the list

### 5. Verify the Fix
Run the relevant tests to confirm the fix works.

## Hints
- The same pattern exists in gap_questions - write works, read returns empty
- The root cause may be similar: DAL stripping fields that handler needs
- Check if other list endpoints have the same issue (e.g., gap questions list)

## Test File Reference
- careervp/live-test-results25.log
