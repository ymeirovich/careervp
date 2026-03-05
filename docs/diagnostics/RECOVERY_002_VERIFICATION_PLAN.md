# RECOVERY_002 Comprehensive Verification & Fix Strategy

## Current Status (as of latest deployment)

### Commits Deployed
- ✅ `ae059dd`: Gap questions table resolution + persistence gate (step_002 core fix)
- ✅ `3d365e4`: Enhanced error diagnostics in gap_handler (response layer)
- ✅ `d4047d1`: Enhanced error diagnostics in dynamo_dal_handler (DAL layer)

### Code Improvements
1. **Response Layer** (gap_handler.py):
   - Returns detailed error message including table_name, operation, error_code, error_message

2. **DAL Layer** (dynamo_dal_handler.py):
   - Comprehensive exception handling for all error types (not just ClientError)
   - Pre-save JSON serialization validation
   - Debug logging of item structure before put_item
   - Detailed error information in exception messages

## Expected Behavior After Deployment

### Successful Case (Code Path)
```
1. POST /jobs/{jobId}/gap-questions request arrives
2. gap_handler.generate_questions() processes request
3. AI generates questions ✅
4. save_gap_questions() called with:
   - pk = user_id
   - sk = ARTIFACT#GAP_ANALYSIS#{cv_id}#{job_id}
   - questions = [...generated questions...]
   - ttl = Unix timestamp
5. DynamoDB put_item succeeds ✅
6. Response: 200 OK with questions
7. Metrics: GapQuestionsGenerated incremented
```

### Failure Case (What We're Investigating)
```
1-3. Same as above
4. save_gap_questions() fails with one of:
   - ClientError with specific code (ValidationException, ResourceNotFoundException, AccessDeniedException, etc.)
   - Serialization error (TypeError, AttributeError, etc.)
   - Unexpected exception (any other type)
5. Enhanced logging captures:
   - Exact error type and message
   - Item structure (keys, estimated size)
   - Operation details (table_name, operation, key_names)
6. Response: 500 INTERNAL_SERVER_ERROR with detailed error message
7. Metrics: GapQuestionPersistenceFailures incremented
```

## Next Steps for Debugging

### Phase 1: Run Tests & Capture Error
```bash
cd careervp
python3 -m pytest docs/refactor/live_tests/test_05_gap_analysis.py::TestGapAnalysisEndpoints::test_generate_gap_questions -xvs 2>&1 | tee test_output.log
```

### Phase 2: Extract Error Details
Looking for the error response with this structure:
```json
{
  "error": "Failed to save gap questions. Details: table_name=... operation=... error_code=... message=...",
  "code": "DYNAMODB_ERROR" or specific code
}
```

### Phase 3: Diagnose Based on Error Type

**If serialization error detected:**
- Check: Are all question fields JSON-serializable?
- Fix: Ensure generate_gap_questions returns only primitive types (str, int, float, bool, list, dict)

**If ClientError with ValidationException:**
- Likely schema mismatch or invalid item structure
- Check: Do pk/sk fields match table definition (both strings)?
- Check: Are reserved words being used as attribute names?

**If ClientError with ResourceNotFoundException:**
- Table doesn't exist
- Check: `aws dynamodb describe-table --table-name <table_name>`
- Check: Verify GAP_QUESTIONS_TABLE_NAME env var value

**If ClientError with AccessDeniedException:**
- Lambda role lacks permissions
- Check: Lambda execution role has `dynamodb:PutItem` on users table

**If item size error:**
- Questions data exceeds 400KB
- Check: Reduce max_questions or compress question content

### Phase 4: Apply Targeted Fix

Based on error type, apply one of:
1. **Serialization fix**: Modify generate_gap_questions return type
2. **Schema fix**: Update item structure to match table schema
3. **Infrastructure fix**: Ensure table exists and env var is correct
4. **Permissions fix**: Update Lambda IAM role
5. **Size fix**: Reduce question content size

### Phase 5: Re-test & Verify

```bash
# Run single test
pytest docs/refactor/live_tests/test_05_gap_analysis.py::TestGapAnalysisEndpoints::test_generate_gap_questions -xvs

# Run full gap analysis suite
pytest docs/refactor/live_tests/test_05_gap_analysis.py -v

# Check regression delta
python3 scripts/spec_quality/check_regression_delta.py \
  --baseline live-test-results27.log \
  --current live-test-resultsXX.log \
  --out /tmp/delta.json
```

## Acceptance Criteria for RECOVERY_002 Complete

- [ ] test_generate_gap_questions returns 200 (not 500)
- [ ] Questions are persisted in DynamoDB
- [ ] test_get_gap_questions returns persisted questions (not empty array)
- [ ] Cross-user isolation verified (test_cross_user_does_not_leak_questions passes)
- [ ] GET endpoint returns 5xx on DAL failure (not masked as 200)
- [ ] Regression delta shows no new violations
- [ ] All 19 tests pass (6 unit + 6 integration + 7 existing)
- [ ] Evidence artifacts generated with 100% pass rate
- [ ] Architect verification obtained
- [ ] Yaml spec updated with confidence_score ≥ 85

## Rollback Plan (If Needed)

If fixes don't work:
1. Revert commits d4047d1, 3d365e4
2. Keep ae059dd (original step_002 logic is sound)
3. Investigate core infrastructure issue
4. Consider: Is table missing? Are permissions wrong? Is deployment stale?

## Key Files for Reference
- Code: src/backend/careervp/handlers/gap_handler.py (line 223-236)
- DAL: src/backend/careervp/dal/dynamo_dal_handler.py (line 526-570)
- Tests: src/backend/tests/integration/test_gap_read_after_write_roundtrip.py
- Diagnostics: docs/diagnostics/RECOVERY_002_DIAGNOSTIC_GUIDE.md
- Spec: docs/beta/fix-api/yaml3/step_002_gap_questions_read_after_write_recovery.yaml

---
**Last Updated**: 2026-03-05 18:55 UTC
**Status**: Deployment pending, awaiting test results with enhanced diagnostics
