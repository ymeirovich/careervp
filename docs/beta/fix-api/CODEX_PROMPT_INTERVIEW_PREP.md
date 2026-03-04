# Codex Prompt: Interview Prep Status Returns CV_NOT_FOUND

## Context

This document contains analysis and a task for Codex to validate, investigate, and fix a bug where:
- POST `/interview-prep/generate` returns 202 with a job ID
- GET `/interview-prep/{id}/status` returns 404 with error "Interview prep not found" and code "CV_NOT_FOUND"

## Test Evidence

```
=== RESPONSE test_generate_interview_prep ===
{
  "test_name": "test_generate_interview_prep",
  "endpoint": "POST /interview-prep/generate",
  "status_code": 202,
  "response": {
    "request_id": "c00798a5-f827-40a4-80b1-41fafac16c2f",
    "artifact_id": "c00798a5-f827-40a4-80b1-41fafac16c2f",
    "status": "processing",
    "estimated_time_seconds": 60
  }
}
✓ POST /interview-prep/generate - Interview prep submitted, ID: c00798a5-f827-40a4-80b1-41fafac16c2f
PASSED

=== RESPONSE test_get_interview_prep_status ===
{
  "test_name": "test_get_interview_prep_status",
  "endpoint": "GET /interview-prep/c00798a5-f827-40a4-80b1-41fafac16c2f/status",
  "status_code": 404,
  "response": {
    "error": "Interview prep not found",
    "code": "CV_NOT_FOUND"
  }
}
FAILED
```

## Architecture

Three separate Lambda functions handle interview prep:

| Endpoint | Lambda Function | Handler File |
|----------|---------------|--------------|
| POST /interview-prep/generate | `interview-prep-api` | `interview_prep_submit_handler.py` |
| GET /interview-prep/{id}/status | `interview-prep-status` | `interview_prep_handler.py` |
| SQS Worker | `interview-prep-worker` | `interview_prep_handler.py` |

## My Hypothesis

### Possible Root Causes

**Option A: DynamoDB save silently failed**
- In `interview_prep_submit_handler.py`, the `table.put_item()` might fail without raising a `BotoClientError`
- Other exceptions would be caught by the outer `except Exception` at line ~151 but not properly handled
- The handler returns 202 even though the item wasn't saved to DynamoDB

**Option B: Key mismatch between save and query**
- Save: `sk = f'ARTIFACT#INTERVIEW_PREP#{job_id}'` (job_id = UUID)
- Query tries:
  - `sk = {interview_prep_id}` (raw UUID)
  - `sk = ARTIFACT#INTERVIEW_PREP#{interview_prep_id}` (with prefix)
- If job_id differs from interview_prep_id, the query won't find the item

**Option C: User ID mismatch**
- Submit extracts user ID from auth
- Status extracts user ID from auth (but might be different due to token caching)
- DynamoDB query uses pk=user_id, which won't match if user IDs differ

## Key Files to Examine

1. `src/backend/careervp/handlers/interview_prep_submit_handler.py`
   - `lambda_handler()` - the submit endpoint
   - `table.put_item()` around line 134-150
   - How job_id is generated and used

2. `src/backend/careervp/handlers/interview_prep_handler.py`
   - `_get_interview_prep_item()` around line 439-465
   - How interview_prep_id is extracted and used in queries

3. `src/backend/careervp/dal/dynamo_dal_handler.py`
   - `save_interview_prep()` if exists
   - How items are saved and keyed

## Your Task

### 1. Validate My Hypothesis
- Read the relevant code sections
- Check if DynamoDB put_item is wrapped properly
- Verify key construction matches between save and query

### 2. Identify the Exact Root Cause
- If Option A: Find where exceptions are being swallowed
- If Option B: Check how job_id vs interview_prep_id are used
- If Option C: Compare auth extraction between submit and status

### 3. Implement the Fix
- Make minimal changes to fix the issue
- Ensure the status endpoint can find items created by the submit endpoint

### 4. Add Tests
**Unit Test:**
- Add test to verify that items saved with sk=ARTIFACT#INTERVIEW_PREP#{job_id} can be found using the interview_prep_id

**Integration Test:**
- In `docs/refactor/live_tests/test_08_interview_prep.py`, verify that:
  1. POST /interview-prep/generate returns 202
  2. GET /interview-prep/{id}/status returns 200 (not 404)

### 5. Verify the Fix
- Run the live tests to confirm the fix works
- Ensure no regression in other interview prep functionality

## Hints

- This is the SAME pattern as gap questions and cover letter bugs
- All three have "write works, read fails" pattern
- Look for systematic issues in how DynamoDB items are saved vs queried
- Check if there's a mismatch between the job_id returned vs what's stored in DynamoDB

## Test File Reference
- `careervp/live-test-results25.log` - contains test evidence
- `docs/refactor/live_tests/test_08_interview_prep.py` - test file
