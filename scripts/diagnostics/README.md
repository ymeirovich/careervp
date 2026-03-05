# RECOVERY_002 Diagnostic Toolkit

Complete toolset for diagnosing, fixing, and validating RECOVERY_002 (gap questions read-after-write recovery).

## Quick Start

### 0. Reset Trial Credits (Required Before Testing)

**Before running tests**, reset trial credits to ensure you have credits available:

```bash
# Option A: Use the run_all_tests.py built-in reset (recommended)
python3 docs/refactor/live_tests/run_all_tests.py --test gap

# Option B: Manual reset via API (if you have network access to deployed API)
python3 -c "
import sys
import os
import requests
sys.path.insert(0, 'docs/refactor/live_tests')
sys.path.insert(0, 'docs/refactor3/scripts')
from conftest import get_auth_headers
from resolve_api_base import resolve_api_base

try:
    headers = get_auth_headers()
    api_base = os.environ.get('API_BASE') or resolve_api_base()

    # Reset trial credits
    reset_resp = requests.post(f'{api_base}/users/me/trial/reset', headers=headers, timeout=15)
    if reset_resp.status_code != 200:
        print(f'⚠️  Trial reset failed: {reset_resp.status_code}')
        print(f'Response: {reset_resp.text}')
        sys.exit(1)

    # Verify reset
    usage_resp = requests.get(f'{api_base}/users/me/usage', headers=headers, timeout=15)
    if usage_resp.status_code != 200:
        print(f'⚠️  Usage check failed: {usage_resp.status_code}')
        sys.exit(1)

    used = int(usage_resp.json().get('applications', {}).get('used', -1))
    if used != 0:
        print(f'⚠️  Trial reset verification failed: applications.used={used}')
        sys.exit(1)

    print('✓ Trial reset successful (applications.used=0)')
except Exception as e:
    print(f'⚠️  Trial reset error: {e}')
    print('Note: run_all_tests.py includes automatic reset before tests')
    sys.exit(1)
"
```

**Note**: `run_all_tests.py` automatically resets trial credits before running gap analysis tests via the `_reset_trial()` function (see line 176 in `run_all_tests.py`).

### 1. Run Live Tests & Capture Error
```bash
cd careervp
python3 -m pytest docs/refactor/live_tests/test_05_gap_analysis.py::TestGapAnalysisEndpoints::test_generate_gap_questions -xvs 2>&1 | tee test_output.log
```

### 2. Analyze Error
```bash
python3 scripts/diagnostics/analyze_gap_questions_failure.py test_output.log
```

### 3. Apply Fix (if needed)
```bash
# Replace <ERROR_CODE> with the actual error code from analysis (e.g., ValidationException)
python3 scripts/diagnostics/apply_gap_questions_fix.py <ERROR_CODE>
```

### 4. Validate Completion
```bash
python3 scripts/diagnostics/validate_recovery_002_complete.py test_output.log live-test-results27.log
```

---

## Tools Description

### 1. `analyze_gap_questions_failure.py`
**Purpose**: Extract and diagnose gap questions DynamoDB failures

**Input**: Live test log file
**Output**: JSON analysis file with diagnosis and recommended fixes

**Usage**:
```bash
python3 analyze_gap_questions_failure.py live-test-results29.log
```

**Output Example**:
```json
{
  "status": "ERROR_WITH_DETAILS",
  "error_code": "ValidationException",
  "details": "table_name=careervp-users operation=save_gap_questions error_code=ValidationException message=One or more parameter values were invalid: Number AttributeValue length is too big",
  "diagnosis": {
    "likely_cause": "Schema validation error",
    "checks": [
      "✓ Are pk and sk fields both strings?",
      "✓ Is artifact_type = 'gap_analysis'?",
      ...
    ],
    "fix": "Review item structure in save_gap_questions vs table schema",
    "reference": "infra/careervp/api_db_construct.py lines 85-89"
  }
}
```

**Error Code Reference**:
- `ValidationException`: Schema mismatch or invalid item structure
- `ResourceNotFoundException`: Table doesn't exist or wrong name
- `AccessDeniedException`: Lambda role lacks permissions
- `ItemCollectionSizeLimitExceededException`: Item exceeds 400KB
- `TypeError`: Data not JSON serializable

---

### 2. `apply_gap_questions_fix.py`
**Purpose**: Automatically apply targeted fixes based on error code

**Input**: Error code
**Output**: Fix verification and AWS CLI commands

**Usage**:
```bash
python3 apply_gap_questions_fix.py ValidationException
python3 apply_gap_questions_fix.py ResourceNotFoundException
python3 apply_gap_questions_fix.py All  # Check all possible fixes
```

**What It Does**:
1. Verifies code changes are in place
2. Provides targeted fix recommendations
3. Generates AWS CLI commands for infrastructure verification
4. Creates JSON report of applied fixes

**Example Output**:
```
AWS CLI Diagnostic Commands:
============================

1. Check table exists:
   aws dynamodb describe-table --table-name careervp-users --region us-east-1

2. Check table schema:
   aws dynamodb describe-table --table-name careervp-users --query 'Table.KeySchema' --region us-east-1

3. Check Lambda environment variables:
   aws lambda get-function-configuration --function-name careervp-gap-api --region us-east-1 | jq '.Environment.Variables'
```

---

### 3. `validate_recovery_002_complete.py`
**Purpose**: Verify RECOVERY_002 implementation is complete

**Input**: Test log files (optional)
**Output**: Validation report with completion status

**Usage**:
```bash
# Basic validation (checks code changes only)
python3 validate_recovery_002_complete.py

# Full validation (with test results)
python3 validate_recovery_002_complete.py test_output.log live-test-results27.log
```

**Validation Checks**:
1. ✓ Code changes in place (gap_handler, DAL, infra)
2. ✓ Test coverage present (unit, integration, live)
3. ✓ Tests passing
4. ✓ Regression delta acceptable
5. ✓ Yaml spec status updated
6. ✓ Confidence score ≥ 85

**Example Output**:
```
🔍 Running RECOVERY_002 Completion Validation
================================================================================
✓ Code Changes: PASS
✓ Test Coverage: PASS
✓ Spec Status: PASS
✓ Tests Passing: PASS
✓ Regression Delta: PASS

================================================================================
✅ RECOVERY_002 COMPLETE - All validation checks passed!
```

---

## Workflow Example

### Scenario: DynamoDB Error in Live Tests

**Step 1: Run tests and save output**
```bash
cd careervp
python3 -m pytest docs/refactor/live_tests/test_05_gap_analysis.py::TestGapAnalysisEndpoints::test_generate_gap_questions -xvs 2>&1 | tee results30.log
# Output: results30.log with error
```

**Step 2: Analyze the error**
```bash
python3 scripts/diagnostics/analyze_gap_questions_failure.py results30.log
# Output: results30_analysis.json showing the specific error code
```

**Step 3: Check the diagnosis**
```bash
cat results30_analysis.json | jq '.diagnosis'
# Shows: "likely_cause": "Table doesn't exist or wrong name"
```

**Step 4: Apply the fix**
```bash
python3 scripts/diagnostics/apply_gap_questions_fix.py ResourceNotFoundException
# Provides AWS CLI commands to verify table
# Shows: table exists and env var is correct
```

**Step 5: Run AWS CLI verification**
```bash
aws dynamodb describe-table --table-name careervp-users --region us-east-1
# Confirms: Table exists with correct schema
```

**Step 6: Identify root cause**
- Table exists ✓
- Env var set correctly ✓
- Schema matches code ✓
- **Issue found**: Lambda role missing dynamodb:PutItem permission

**Step 7: Fix the root cause**
```bash
# Update Lambda IAM role to add dynamodb:PutItem permission
# Then redeploy or restart lambda
```

**Step 8: Re-run tests**
```bash
python3 -m pytest docs/refactor/live_tests/test_05_gap_analysis.py -xvs 2>&1 | tee results31.log
# Tests should now pass
```

**Step 9: Validate completion**
```bash
python3 scripts/diagnostics/validate_recovery_002_complete.py results31.log live-test-results27.log
# Output: RECOVERY_002 COMPLETE - All validation checks passed!
```

---

## Important References

### Documentation Files
- **Diagnostic Guide**: `docs/diagnostics/RECOVERY_002_DIAGNOSTIC_GUIDE.md`
- **Verification Plan**: `docs/diagnostics/RECOVERY_002_VERIFICATION_PLAN.md`
- **Current Status**: `docs/diagnostics/RECOVERY_002_CURRENT_STATUS.md`

### Code Files
- **Gap Handler**: `src/backend/careervp/handlers/gap_handler.py` (lines 39-49, 223-236)
- **DAL Handler**: `src/backend/careervp/dal/dynamo_dal_handler.py` (lines 1-3, 526-570)
- **Infrastructure**: `infra/careervp/api_construct.py` (lines 1807-1816)
- **Table Schema**: `infra/careervp/api_db_construct.py` (lines 85-89)

### Test Files
- **Unit Tests**: `src/backend/tests/unit/test_gap_handler_persistence_required.py`
- **Integration Tests**: `src/backend/tests/integration/test_gap_read_after_write_roundtrip.py`
- **Live Tests**: `docs/refactor/live_tests/test_05_gap_analysis.py`

---

## Troubleshooting

### Q: Script says "Enhanced diagnostics not yet deployed"
**A**: Wait 2-5 minutes after commits are pushed. Check GitHub Actions to verify deployment.

### Q: Validation shows "test_coverage: FAIL"
**A**: One or more test files are missing. Create them from test_05_gap_analysis.py template.

### Q: Error says "analysis.json not found"
**A**: Run the analyze script with the correct log file path: `python3 ... full/path/to/logfile.log`

### Q: Can't find AWS CLI errors
**A**: Check CloudWatch logs directly: `aws logs tail /aws/lambda/careervp-gap-api --follow`

---

## Support

For issues with diagnostic tools:
1. Check the error message carefully
2. Cross-reference with RECOVERY_002_DIAGNOSTIC_GUIDE.md
3. Run AWS CLI verification commands
4. Check CloudWatch logs for full error details
5. Review the exact error message in the test output

---

**Last Updated**: 2026-03-05 18:55 UTC
**Status**: All diagnostic tools deployed and ready for use
