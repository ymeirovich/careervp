# Investigate and Fix Live Test Issues

## Context

You are investigating live test failures from `live-test-results14.log`. The API is deployed at `https://dev-api.careervp.com`.

**READ FIRST**
1. /Users/yitzchak/Documents/dev/careervp/live-test-results14.log
2. /Users/yitzchak/Documents/dev/careervp/docs/beta/api-failing-analysis/PLAN.md

## VALIDATE
Analyze live-test-results14.log and validate these assumptions are correct. Check if the issues include problems with:
- the test (/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/run_all_tests.py)
- API Gateway
- Lambda
- DynamoDb
- DAL

## Issues to Investigate

### Issue 1: 500 Errors - LLM Response Parsing Failures

**Locations:**
- `POST /jobs/{job_id}/gap-questions` returns 500: "Failed to parse LLM response: Expecting value: line 1 column 1 (char 0)"
- `POST /jobs/{job_id}/gap-responses` returns 500: "Failed to save gap responses. Please try again."

**What to check:**
1. Check if Anthropic API key is valid in the Lambda environment
2. Look at the gap handler code to see where JSON parsing fails
3. Add better error handling to catch and log the actual LLM response

**Files to investigate:**
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/logic/gap_service.py` (if exists)

### Issue 2: 400 Errors on VPR Generation

**Location:**
- `POST /vpr/generate` returns 400: "Invalid request body"

**What to check:**
1. Check what fields are required for VPR generation
2. Compare with test payload in `test_04_vpr.py`
3. Add better validation error messages to show what's missing

**Files to investigate:**
- `src/backend/careervp/handlers/vpr_submit_handler.py`
- `src/backend/careervp/handlers/vpr_status_handler.py`

### Issue 3: 400 Errors on Cover Letter Generation

**Location:**
- `POST /cover-letter/generate` returns 400: "Request validation failed"

**What to check:**
1. Check what prerequisites are required (gap_response_ids, company_research_id)
2. Verify the test is providing all required fields
3. Add better error messages showing what's missing

**Files to investigate:**
- `src/backend/careervp/handlers/cover_letter_handler.py`

### Issue 4: 400 Errors on Interview Prep Generation

**Location:**
- `POST /interview-prep/generate` returns 400: "Request validation failed"

**What to check:**
1. Check what prerequisites are required (gap_response_ids)
2. Verify the test is providing all required fields
3. Add better error messages showing what's missing

**Files to investigate:**
- `src/backend/careervp/handlers/interview_prep_handler.py`

## Your Task

1. **Investigate** each issue by reading the relevant handler code
2. **Validate** the root cause by checking what's actually failing
3. **Fix** the issues with code changes
4. **Add validations** - Add proper input validation with clear error messages showing what's missing
5. **Add tests** - Add unit tests to verify the validation logic works correctly

## Important Notes

- The API is already deployed to dev - any fixes will need deployment
- After making fixes, run the live tests again to verify: `python -m pytest docs/refactor/live_tests/ -v`
- All code must comply with careervp/docs/best_practices/yaml/*
- All code must be validated using ruff, mypy, pytest
- Focus on the 500 errors first as they indicate broken functionality
- The 400 errors may be expected if prerequisites aren't met - document this
- The docs/refactor/live_tests/run_all_tests.py **may** be written out of order to account for async operations
- PLAN.md **may** have some issues already solved as work has progressed since then.

## Test Commands

Run specific tests:
```bash
# Test gap analysis
python -m pytest docs/refactor/live_tests/test_05_gap_analysis.py -v

# Test VPR
python -m pytest docs/refactor/live_tests/test_04_vpr.py -v

# Test cover letter
python -m pytest docs/refactor/live_tests/test_07_cover_letter.py -v

# Test interview prep
python -m pytest docs/refactor/live_tests/test_08_interview_prep.py -v
```
