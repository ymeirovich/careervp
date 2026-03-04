# Codex Master Prompt - CareerVP Fix API Orchestrator

## Purpose

This master prompt orchestrates Codex agents to execute fix specs from `careervp/docs/beta/fix-api/yaml/*.yaml` in parallel or sequential order.

## Best Practices Compliance

All code changes MUST comply with the following best practices specifications:

### Handler Standards
Reference: `careervp/docs/best_practices/yaml/lambda_handler_spec.yaml`

| Rule ID | Requirement | Applies To |
|---------|-------------|------------|
| HANDLER_USE_POWERTOOLS | Use Logger, Tracer, Metrics | All handlers |
| REQ_VALIDATE_INPUT | Pydantic validation for requests | New endpoints |
| RESPONSE_STANDARD_FORMAT | Consistent {statusCode, headers, body} | All responses |
| AUTH_EXTRACT_FROM_CONTEXT | Extract user_id from auth context, never payload | All endpoints |
| ERROR_SPECIFIC_CATCHING | Catch specific exceptions before generic | Error handling |
| ERROR_RESULT_MAPPING | Map domain errors to HTTP statuses | All handlers |

### Testing Standards
Reference: `careervp/docs/best_practices/yaml/testing_spec.yaml`

| Rule ID | Requirement | Applies To |
|---------|-------------|------------|
| TEST_DIRECTORY_STRUCTURE | tests/{feature}/unit, integration, e2e | Test organization |
| TEST_UNIT_ISOLATION | Mock all external dependencies | Unit tests |
| TEST_UNIT_ENV_ISOLATION | Reset environment between tests | All tests |
| TEST_INTEGRATION_BOUNDARY | Test component boundaries | Integration tests |
| TEST_MOCK_CLIENTS | Use MagicMock for AWS clients | All AWS mocking |
| TEST_FIXTURE_AUTOMOCK | Auto-set test environment | All tests |

## Specs Available

| Spec ID | Title | Priority | Dependencies |
|---------|-------|----------|--------------|
| GAP_GET_001 | Gap Questions GET Returns Empty | high | - |
| COVER_LETTER_001 | Cover Letter List Returns Empty | high | - |
| INTERVIEW_PREP_001 | Interview Prep Status Returns 404 | high | - |
| CV_UPLOAD_001 | CV Upload 529 Error | high | - |
| TRIAL_001 | Trial Credits Consumed Too Fast | high | - |
| GAP_QUALITY_001 | Gap Question Quality Low | high | - |
| CV_TAILORING_001 | CV Tailoring ID Format + Delete | medium | - |
| HEALTH_CHECK_001 | Health Returns Degraded | medium | - |

## Execution Modes

### Mode 1: Sequential (Ordered by Priority)

Run specs in priority order, one at a time. Use when:
- Specs have dependencies on each other
- You want to monitor each fix individually
- Risk mitigation is important

```bash
# Run in sequential order
SPECS=("GAP_GET_001" "COVER_LETTER_001" "INTERVIEW_PREP_001" "CV_UPLOAD_001" "TRIAL_001" "GAP_QUALITY_001" "CV_TAILORING_001" "HEALTH_CHECK_001")
```

### Mode 2: Parallel (Independent Fixes)

Run independent specs in parallel. Use when:
- Specs have NO dependencies
- You want faster execution
- Resources allow parallel processing

Independent specs (can run in parallel):
- GAP_GET_001
- COVER_LETTER_001
- INTERVIEW_PREP_001
- CV_UPLOAD_001
- TRIAL_001
- GAP_QUALITY_001
- CV_TAILORING_001
- HEALTH_CHECK_001

### Mode 3: Parallel Groups (Recommended)

Run specs in groups based on complexity and risk:

**Group A (Quick Fixes - Can Run in Parallel):**
- GAP_GET_001
- COVER_LETTER_001
- INTERVIEW_PREP_001

**Group B (Moderate - Can Run in Parallel):**
- CV_TAILORING_001
- HEALTH_CHECK_001

**Group C (Complex - Run Sequentially):**
- CV_UPLOAD_001 (SDK configuration)
- TRIAL_001 (trial service logic)
- GAP_QUALITY_001 (prompt enhancement)

## Codex Agent Command Format

To execute a spec, Codex should:

```bash
# Read the spec file
cat careervp/docs/beta/fix-api/yaml/{spec_id}.yaml

# Analyze the code
# - Read files_to_modify
# - Understand root_cause
# - Review test_evidence

# Implement the fix
# - Follow fix_options
# - Make minimal changes
# - COMPLY with lambda_handler_spec.yaml rules

# Add tests
# - Create unit tests per testing_spec.yaml
# - Add integration tests to docs/refactor/live_tests/
# - Use TEST_UNIT_ISOLATION (mock external dependencies)
# - Use TEST_MOCK_CLIENTS pattern for AWS mocks

# Verify
# - Run tests
# - Check for regressions
```

**Best Practices Verification Checklist:**
- [ ] Handler uses Powertools (Logger, Tracer, Metrics)
- [ ] Request validation with Pydantic (REQ_VALIDATE_INPUT)
- [ ] Response follows standard format
- [ ] User ID extracted from auth context (AUTH_EXTRACT_FROM_CONTEXT)
- [ ] Error handling catches specific exceptions first
- [ ] Tests follow directory structure (TEST_DIRECTORY_STRUCTURE)
- [ ] Unit tests mock external dependencies (TEST_UNIT_ISOLATION)
- [ ] Integration tests verify component boundaries (TEST_INTEGRATION_BOUNDARY)

## Example: Run Single Spec

```
Task: Execute spec GAP_GET_001

1. Read: careervp/docs/beta/fix-api/yaml/gap_get_fix.yaml

2. Root Cause:
   - File: dynamo_dal_handler.py
   - Line: 480
   - Issue: Strict job_id filter

3. Fix:
   - Remove or fix the filter at line 480
   - COMPLY with lambda_handler_spec.yaml (if adding new handlers)

4. Tests:
   - Add unit test for list_gap_questions_by_prefix
   - Use TEST_UNIT_ISOLATION (mock DynamoDB)
   - Add integration test in test_05_gap_analysis.py

5. Verify:
   - Run tests
   - Check GET returns questions
   - Ensure best_practices compliance
```

## Example: Run All in Parallel

```
Task: Run all 8 specs in parallel

1. Spawn 8 Codex agents, one per spec:
   - Agent 1: GAP_GET_001
   - Agent 2: COVER_LETTER_001
   - Agent 3: INTERVIEW_PREP_001
   - Agent 4: CV_UPLOAD_001
   - Agent 5: TRIAL_001
   - Agent 6: GAP_QUALITY_001
   - Agent 7: CV_TAILORING_001
   - Agent 8: HEALTH_CHECK_001

2. Each agent:
   - Reads its spec YAML
   - Implements the fix
   - Adds tests per testing_spec.yaml
   - Verifies best_practices compliance
   - Runs tests

3. Report results:
   - Pass/Fail per spec
   - Best practices checklist completed
   - Any issues found
```

## Progress Tracking

| Spec ID | Title | Status | Agent | Best Practices | Notes |
|---------|-------|--------|-------|----------------|-------|
| GAP_GET_001 | Gap GET Empty | pending | - | [ ] | - |
| COVER_LETTER_001 | Cover Letter List | pending | - | [ ] | - |
| INTERVIEW_PREP_001 | Interview Prep 404 | pending | - | [ ] | - |
| CV_UPLOAD_001 | CV Upload 529 | pending | - | [ ] | - |
| TRIAL_001 | Trial Exhausted | pending | - | [ ] | - |
| GAP_QUALITY_001 | Gap Quality | pending | - | [ ] | - |
| CV_TAILORING_001 | CV Tailoring | pending | - | [ ] | - |
| HEALTH_CHECK_001 | Health Degraded | pending | - | [ ] | - |

## Master Command

To execute all specs:

```bash
# Option 1: Sequential
for spec in GAP_GET_001 COVER_LETTER_001 INTERVIEW_PREP_001 CV_UPLOAD_001 TRIAL_001 GAP_QUALITY_001 CV_TAILORING_001 HEALTH_CHECK_001; do
  codex --spec careervp/docs/beta/fix-api/yaml/${spec}.yaml
done

# Option 2: Parallel (8 agents)
codex --parallel \
  --specs careervp/docs/beta/fix-api/yaml/GAP_GET_001.yaml \
          careervp/docs/beta/fix-api/yaml/COVER_LETTER_001.yaml \
          careervp/docs/beta/fix-api/yaml/INTERVIEW_PREP_001.yaml \
          careervp/docs/beta/fix-api/yaml/CV_UPLOAD_001.yaml \
          careervp/docs/beta/fix-api/yaml/TRIAL_001.yaml \
          careervp/docs/beta/fix-api/yaml/GAP_QUALITY_001.yaml \
          careervp/docs/beta/fix-api/yaml/CV_TAILORING_001.yaml \
          careervp/docs/beta/fix-api/yaml/HEALTH_CHECK_001.yaml
```

## Best Practices Reference Files

| File | Purpose |
|------|---------|
| `docs/best_practices/yaml/lambda_handler_spec.yaml` | Handler development standards |
| `docs/best_practices/yaml/testing_spec.yaml` | Testing standards |
| `docs/best_practices/yaml/dynamodb_spec.yaml` | DynamoDB patterns |
| `docs/best_practices/yaml/api_response_spec.yaml` | API response standards |
