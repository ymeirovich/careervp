# Live Test Results Analysis Plan

## Non-2xx Status Codes Analysis

### Status 403 - Multiple Endpoints
**Root Cause:** Tests use wrong endpoint paths (route mismatch), NOT authentication issues

| Test Path | Expected Path | Issue |
|-----------|---------------|-------|
| `/users/me/cvs` | `/users/me/cv` | Wrong plural form |
| `/users/me/cvs/{cv_id}` | `/users/me/cv/{cv_id}` | Wrong plural form |
| `/gap-analysis/questions` | `/jobs/{jobId}/gap-questions` | Completely wrong route |
| `/gap-analysis/responses` | `/jobs/{jobId}/gap-responses` | Completely wrong route |
| `/gap-analysis/{job_id}/questions` | `/jobs/{jobId}/gap-questions` | Wrong route structure |

### Status 404 - /users/me
**Root Cause:** No user profile exists in DynamoDB after Cognito registration

The auth works (Cognito token valid), but the user profile record doesn't exist in DynamoDB, causing GET /users/me to return 404.

### Status 502 - Multiple Endpoints
**Root Cause:** Lambda exceptions due to missing prerequisites

- `/cover-letter/generate` - Requires CV to exist in DynamoDB
- Other endpoints may have similar missing data requirements

---

## Gap Analysis Investigation (CORRECTED)

### Finding: Gap Analysis IS IMPLEMENTED

**Handler:** `src/backend/careervp/handlers/gap_handler.py`
- Exists and handles GET/POST for gap questions and responses

**Logic:** `src/backend/careervp/logic/gap_analysis.py`
- Exists with gap analysis business logic

**Models:** `src/backend/careervp/models/gap_analysis.py`
- Exists with data models

**DAL:** Uses DynamoDB via existing DAL (not a separate gap_dal)

### API Routes (from api_construct.py)
```python
("/jobs/{jobId}/gap-questions", "POST", self.gap_api_func),
("/jobs/{jobId}/gap-questions", "GET", self.gap_api_func),
("/jobs/{jobId}/gap-responses", "POST", self.gap_api_func),
```

### Test Error (test_05_gap_analysis.py)
The test uses WRONG paths:
```python
url = f"{self.base_url}/gap-analysis/questions"      # WRONG
url = f"{self.base_url}/gap-analysis/responses"       # WRONG
url = f"{self.base_url}/gap-analysis/{job_id}/questions"  # WRONG
```

**Should be:**
```python
url = f"{self.base_url}/jobs/{job_id}/gap-questions"
url = f"{self.base_url}/jobs/{job_id}/gap-responses"
```

---

## Fix Plan

### 1. Fix Gap Analysis Test Paths (HIGH PRIORITY)
- Update test_05_gap_analysis.py to use correct endpoint paths
- Path format: `/jobs/{job_id}/gap-questions` and `/jobs/{job_id}/gap-responses`

### 2. Create User Profile on Signup (MEDIUM PRIORITY)
- Add user profile creation in Cognito post-confirmation or first API call
- Or create test setup that creates user profile in DynamoDB

### 3. Add Lambda Health Check (MEDIUM PRIORITY)
- Update health_handler.py to check Lambda invocation health
- Currently only checks Anthropic and DynamoDB

### 4. Fix 502 Errors (LOW PRIORITY - requires data setup)
- Ensure CV exists before testing cover letter generation
- Add proper test data setup

---

## Summary

| Issue | Status | Root Cause |
|-------|--------|------------|
| 403 on Gap Analysis | TEST BUG | Test uses `/gap-analysis/*` instead of `/jobs/{jobId}/gap-*` |
| 403 on /users/me/cvs | TEST BUG | Wrong plural form (`cvs` vs `cv`) |
| 404 on /users/me | MISSING DATA | No user profile in DynamoDB |
| 502 on /cover-letter | MISSING DATA | No CV in DynamoDB |
| Health missing Lambda | BUG | health_handler.py missing Lambda check |
