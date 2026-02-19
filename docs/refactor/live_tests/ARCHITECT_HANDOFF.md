# Architect Handoff: CareerVP API Validation

## Mission
Validate and remediate ALL 27 CareerVP API endpoints to return successful (200/201) responses with complete JSON payloads. The Architect must ensure the full API → Application → DAL workflow executes correctly.

---

## Current State

### Test Results (Live Run)
- **Total Tests:** 32
- **Passed:** 26
- **Skipped:** 6
- **Duration:** ~77 seconds

### Endpoints with Issues (MUST FIX)

| Endpoint | Status | Error | Root Cause |
|----------|--------|-------|------------|
| GET /health | 404 | Not deployed | Infrastructure |
| GET /users/me | 404 | Not found | API Gateway route |
| PUT /users/me | 404 | Not found | API Gateway route |
| GET /users/me/cvs | 404 | Not found | API Gateway route |
| GET /jobs | 404 | Endpoint not found | API Gateway route |
| POST /gap-analysis/questions | 500 | Missing artifactId | DynamoDB schema |
| GET /gap-analysis/{jobId}/questions | 500 | Query key condition | DynamoDB query |
| GET /cv-tailoring/{id} | 502 | Internal server error | Lambda exception |
| POST /company-research/fetch | 503 | All sources failed | External API |

### Auth-Protected Endpoints Needing Token (Test Issue)
- GET /jobs/{jobId} - 401
- POST /vpr/generate - 401
- GET /vpr/{id} - 401
- GET /users/me/vprs - 401
- GET /cover-letter/{id} - 401
- GET /users/me/cover-letters - 401
- GET /interview-prep/{id} - 401
- GET /company-research/{jobId} - 401

---

## Required Fixes

### P0: Critical (Must Fix First)

#### 1. Gap Analysis DynamoDB Schema
- **Issue:** Missing `artifactId` in PutItem operation
- **Error:** `ValidationException: Missing the key artifactId in the item`
- **Fix:** Update `src/backend/careervp/dal/gap_analysis_dal.py` to include `artifactId` partition key
- **Also:** Fix query operation - currently using wrong partition key

#### 2. CV Tailoring Status 502
- **Issue:** Internal server error on GET /cv-tailoring/{id}
- **Fix:** Check Lambda logs, fix exception in `cv_tailoring_status_handler.py`

### P1: High Priority

#### 3. Missing API Routes (404s)
- **GET /users/me** - Check API Gateway route mapping
- **PUT /users/me** - Check API Gateway route mapping
- **GET /users/me/cvs** - Check API Gateway route mapping
- **GET /jobs** - Check API Gateway route mapping

#### 4. Health Endpoint
- **Issue:** Not deployed, returns 404
- **Fix:** Either deploy or confirm not required for prod stage

### P2: Test Infrastructure

#### 5. Auth Token in Tests
- **Issue:** Multiple endpoints return 401 because tests don't pass Bearer token
- **Fix:** Update test fixtures to:
  1. Login to get fresh tokens
  2. Pass Authorization header to all protected endpoints
  3. Store cv_id, job_id, vpr_id for dependent tests

#### 6. Async Polling
- **Issue:** Polling tests skipped - no ID available
- **Fix:** After generating async job, poll until status != "pending"
- **Example:**
```python
def wait_for_completion(job_id, endpoint, max_attempts=30):
    for _ in range(max_attempts):
        response = requests.get(f"{API_BASE}{endpoint}/{job_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "completed":
                return data
        time.sleep(2)
    raise TimeoutError("Job did not complete")
```

---

## Validation Workflow

### Each Feature Must Pass Full Stack Validation

For each of these features, verify the complete flow:

1. **VPR (Verification of Past Experience)**
   - POST /vpr/generate → Returns job_id, status "pending"
   - Poll GET /vpr/{id} until status="completed"
   - Verify DAL wrote to DynamoDB with correct partition key

2. **Gap Analysis**
   - POST /gap-analysis/questions → Creates questions
   - Verify DynamoDB has artifactId as partition key
   - POST /gap-analysis/responses → Submits answers
   - GET /gap-analysis/{jobId}/questions → Returns questions

3. **CV Tailoring**
   - POST /cv-tailoring/generate → Creates tailored CV
   - Poll GET /cv-tailoring/{id} until status="completed"
   - GET /users/me/tailored-cvs → Lists all

4. **Cover Letter**
   - POST /cover-letter/generate → Creates cover letter
   - Poll GET /cover-letter/{id} until status="completed"
   - GET /users/me/cover-letters → Lists all

5. **Interview Prep**
   - POST /interview-prep/generate → Creates prep
   - Poll GET /interview-prep/{id} until status="completed"

6. **Company Research**
   - POST /company-research/fetch → Fetches data
   - GET /company-research/{jobId} → Returns research

---

## Architecture to Validate

```
API Gateway (REST API)
    │
    ├── Lambda Handlers (careervp/handlers/)
    │   ├── auth_handler.py
    │   ├── user_handler.py
    │   ├── cv_upload_handler.py
    │   ├── job_handler.py
    │   ├── vpr_handler.py / vpr_submit_handler.py / vpr_status_handler.py
    │   ├── gap_handler.py
    │   ├── cv_tailoring_handler.py
    │   ├── cover_letter_handler.py
    │   ├── interview_prep_handler.py
    │   └── company_research_handler.py
    │
    ├── Application Layer (careervp/logic/)
    │   ├── vpr_logic.py
    │   ├── gap_analysis_logic.py
    │   ├── cv_tailoring_logic.py
    │   ├── cover_letter_logic.py
    │   ├── interview_prep_logic.py
    │   └── company_research_logic.py
    │
    └── DAL (careervp/dal/)
        ├── user_dal.py
        ├── job_dal.py
        ├── cv_dal.py
        ├── gap_analysis_dal.py (FIX: artifactId)
        ├── vpr_dal.py
        ├── tailored_cv_dal.py
        ├── cover_letter_dal.py
        ├── interview_prep_dal.py
        └── company_research_dal.py
```

---

## Deliverables

1. **Fixed Backend Code** - All DAL, Logic, Handler fixes
2. **Updated Tests** - Sequential execution with auth tokens and async polling
3. **Test Results** - test_results.log with ALL 27 endpoints returning 200/201
4. **Validation** - Confirmation of API → Application → DAL workflow

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Endpoints returning 200/201 | 27/27 (100%) |
| JSON responses captured | 100% |
| Async polling working | 6/6 features |
| DAL writes verified | All features |
| Test execution time | < 5 minutes |

---

## EXECUTION PROMPT

Execute the following steps in order:

### Step 1: Run Live Tests
```bash
cd /Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests
python -m pytest . -v -s --tb=long 2>&1 | tee test_results.log
```

### Step 2: Analyze Results
- Review test_results.log for all failures
- Categorize each failure by type: INFRASTRUCTURE, DYNAMODB_SCHEMA, AUTH, VALIDATION, EXTERNAL

### Step 3: Fix Issues (Priority Order)

**P0 - Fix First:**
1. Fix Gap Analysis DynamoDB schema in `src/backend/careervp/dal/gap_analysis_dal.py`
2. Fix CV Tailoring 502 error - check Lambda logs

**P1 - High Priority:**
3. Fix missing API routes (404s) - check API Gateway configuration
4. Deploy health endpoint or mark as not required

**P2 - Test Infrastructure:**
5. Update test fixtures to pass auth tokens
6. Implement async polling in tests
7. Execute tests sequentially with ID dependencies

### Step 4: Re-run Tests Until All Pass
Repeat Step 1 until ALL 27 endpoints return 200/201 with valid JSON.

### Step 5: Validate Full Workflow
For each feature, verify: API → Application → DAL → Async Job → Status Check

---

## Output Files

1. `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/REMEDIATION_PLAN.md` - Updated remediation plan
2. `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/test_results.log` - Full test output
3. Updated test scripts with proper sequencing and async polling

---

*Handed off from: Claude Code (Haiku)*
*Date: 2026-02-19*
*Priority: P0 - Immediate action required*
