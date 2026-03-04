# Codex Prompt: Trial Credits Being Consumed More Than Expected

## Context

The live test suite is exhausting trial credits (3 free applications) when it should only consume 2:
- 1 credit for test_05_gap_analysis (POST /gap-questions)
- 1 credit for test_10_api_contract (POST /gap-questions in contract test)

But the test is getting 403 `trial_exhausted` indicating 3+ credits were consumed.

## Current Test Flow

```
1. Pre-flight reset    → Trial = 0
2. test_05_gap_analysis → POST /gap-questions → Trial = 1
3. (other tests run - NO credit consumption)
4. Pre-contract reset → Trial = 0 (supposedly)
5. test_10_api_contract → POST /gap-questions → Trial = 1
6. Trial exhausted??? (should still have 2 credits left)
```

## Your Task

### 1. Investigate Credit Consumption

Verify that ONLY these two endpoints consume credits:
- `POST /gap-questions` in gap_handler.py (only endpoint that calls `consume_credit()`)

Search the codebase for ALL calls to `consume_credit`:
```bash
grep -r "consume_credit" --include="*.py"
```

Confirm these handlers do NOT consume credits:
- CV Tailoring (test_06)
- Cover Letter (test_07)
- Interview Prep (test_08)
- VPR (test_04)
- Job Create (test_03)

### 2. Check Test Reset Logic

The reset IS called before the contract test:
- In `run_all_tests.py` line 187-189:
  ```python
  if test_name == "contract":
      print("\nPre-contract reset:")
      _reset_trial(api_base)
  ```

Verify that:
- The reset endpoint `POST /users/me/trial/reset` is actually working
- It's not silently failing (no network errors, no auth errors)
- The reset actually writes to DynamoDB

### 3. Check for Multiple Calls

Search for ALL calls to POST /gap-questions in the test files:
- `docs/refactor/live_tests/test_05_gap_analysis.py`
- `docs/refactor/live_tests/test_10_api_contract_success.py`

Are there any hidden calls like:
- Retry logic that retries failed requests?
- Test setup that generates extra questions?
- Other tests that might call this endpoint?

### 4. Fix the Issue

If the reset is failing:
- Add better error handling/logging to the reset endpoint
- Add a health check for trial status in the test to debug

If there are multiple calls:
- Remove duplicate calls
- Add proper state management to prevent re-generating questions

### 5. Add Tests

**Unit Test:**
- Add test to verify trial service correctly tracks and resets credits

**Integration Test:**
- Add test to verify that 2 POST /gap-questions calls work without exhausting trial (when properly reset between)

## Expected Behavior

With 3 free applications:
- test_05_gap_analysis: uses 1 credit
- test_10_api_contract: uses 1 credit
- Total: 2 credits used
- Remaining: 1 credit

Should NOT get `trial_exhausted` error.

## Test File Reference
- `careervp/live-test-results25.log` - contains test evidence showing 403 trial_exhausted
- `docs/refactor/live_tests/run_all_tests.py` - test runner with reset logic
- `docs/refactor/live_tests/test_05_gap_analysis.py` - gap analysis tests
- `docs/refactor/live_tests/test_10_api_contract_success.py` - contract tests
- `src/backend/careervp/logic/trial_service.py` - trial service implementation

## Hints
- Check if there's a bug in the consume_credit logic that increments by more than 1
- Check if there's a bug in the reset logic that doesn't actually reset
- Check if ColdStart or other issues cause the trial service to fail silently
- The gap_questions_history.json in contract test might be making an extra call
