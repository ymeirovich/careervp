# Validate and Fix Live Test 2xx Responses

## Context
You are working on fixing the live E2E tests in `careervp/docs/refactor/live_tests/run_all_tests.py`. The goal is that ALL API endpoints return `status_code: 2xx`.

## Current Issues Found (from analysis)

### 1. Gap Analysis - Wrong Endpoint Paths
- **Issue**: Test uses `/gap-analysis/*` but API routes are `/jobs/{jobId}/gap-*`
- **Files**:
  - Test: `docs/refactor/live_tests/test_05_gap_analysis.py`
  - API Routes: `infra/careervp/api_construct.py`
  - Handler: `src/backend/careervp/handlers/gap_handler.py`

### 2. Gap Analysis - Uses boto3 Directly (NOT DynamoDALHandler)
- **Issue**: Gap handler calls boto3 directly instead of using DynamoDALHandler
- **Pattern**: VALIDATE ASSUMPTION: Other modules (VPR, CV-Tailoring, Cover Letter) use DynamoDALHandler, 
- **Files**:
  - Handler: `src/backend/careervp/handlers/gap_handler.py`
  - DAL: `src/backend/careervp/dal/dynamo_dal_handler.py`
  - Compare with: `src/backend/careervp/handlers/cover_letter_handler.py` (uses DynamoDALHandler)
- **Need to**: Refactor gap_handler to use DynamoDALHandler like other modules
- **Validation Steps**:
  1. Read `src/backend/careervp/handlers/gap_handler.py` - check for boto3.resource('dynamodb') or boto3.client('dynamodb')
  2. Read `src/backend/careervp/dal/dynamo_dal_handler.py` - understand the DAL interface
  3. Read `src/backend/careervp/handlers/cover_letter_handler.py` - see how it uses DynamoDALHandler
  4. Refactor gap_handler to:
     - Import DynamoDALHandler
     - Use dal.save_gap_analysis() / dal.get_gap_analysis() instead of boto3 calls
     - Add gap methods to DynamoDALHandler if missing

### 3. CV Endpoint - Wrong Plural Form
- **Issue**: Test uses `/users/me/cvs` but should use `/users/me/cv`
- **Files**: Check test files in `docs/refactor/live_tests/`

### 4. User Profile - Missing in DynamoDB
- **Issue**: GET /users/me returns 404 because no user profile exists after Cognito signup
- **Need to**: Validate whether user profile creation is handled

### 5. Cover Letter - Auth or Missing Data
- **Issue**: Returns 401 Unauthorized
- **Need to**: Validate auth flow and test setup

### 6. Health Endpoint - Missing Lambda Check
- **Issue**: `src/backend/careervp/handlers/health_handler.py` doesn't check Lambda health
- **Need to**: Add Lambda health check

## Your Task

### Phase 1: Validate Findings
1. Read `docs/refactor/live_tests/run_all_tests.py` to understand the test structure
2. Read `docs/refactor/live_tests/test_05_gap_analysis.py` - verify the endpoint paths used
3. Read `infra/careervp/api_construct.py` - verify the actual API routes defined
4. Read `src/backend/careervp/handlers/gap_handler.py` - verify it uses boto3 directly
5. Read `src/backend/careervp/dal/dynamo_dal_handler.py` - understand the DAL interface
6. Read `src/backend/careervp/handlers/cover_letter_handler.py` - see the pattern to follow

### Phase 2: Identify All Failing Endpoints
Run the tests and capture all non-2xx responses:
```bash
cd /Users/yitzchak/Documents/dev/careervp
python docs/refactor/live_tests/run_all_tests.py 2>&1 | tee live-test-fix.log
```

### Phase 3: Create Fix Plan
For each failing endpoint, determine:
1. Is it a TEST BUG (wrong path/method)?
2. Is it MISSING DATA (DynamoDB/S3)?
3. Is it a CODE BUG (handler missing, wrong DAL usage)?

### Phase 4: Refactor Gap Analysis to Use DynamoDALHandler
**This is critical - follow the pattern from cover_letter_handler.py:**
1. Remove boto3 direct calls from gap_handler.py
2. Add gap_* methods to DynamoDALHandler if not present
3. Use dal.save_gap_analysis() / dal.get_gap_analysis() pattern
4. Test that gap endpoints still work after refactor

### Phase 5: Implement Other Fixes
**Do NOT fix blindly. For each fix:**
1. Read the relevant source file
2. Understand the code
3. Make minimal fix
4. Re-run test to validate

### Phase 6: Final Validation
Run full test suite and confirm ALL endpoints return 2xx:
```bash
python docs/refactor/live_tests/run_all_tests.py
```

Expected output: All tests pass with 2xx status codes.

## Important Rules
- DO NOT assume - always read the actual code first
- Fix one issue at a time and validate
- If uncertain, ask for clarification
- Document each fix in a CHANGELOG section

## Success Criteria
- [ ] Gap handler refactored to use DynamoDALHandler (like VPR, CV-Tailoring, Cover Letter)
- [ ] All tests in run_all_tests.py pass
- [ ] Every API endpoint returns 2xx status code
- [ ] No 403, 404, 401, 500, 502 errors in test output
