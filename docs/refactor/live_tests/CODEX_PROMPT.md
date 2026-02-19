# Codex Prompt: Run Live Tests and Generate Remediation Plan

## Context

You are working with the CareerVP API project located at `/Users/yitzchak/Documents/dev/careervp`.

The live tests are located in `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/`.

**Target Model:** Claude Code / Codex
**Validation Criteria:** Tests must run successfully against deployed API
**Output Format:** Markdown remediation plan with issue analysis

---

## PHASE 1: INITIAL ASSESSMENT

Before running tests, answer these questions:

1. What is the intended output format? → Markdown remediation plan with tables
2. What constraints must be satisfied? → All 27 API endpoints must be testable
3. What validation criteria define success? → Tests execute without exceptions, results documented
4. Who is the target model? → Claude Code / Codex executing pytest
5. What is the context/window size? → Full test suite output

---

## PHASE 2: MULTI-DIMENSIONAL EVALUATION

Rate each dimension 0-10:

### Efficiency (weight: 0.4)
| Metric | Score | Notes |
|--------|-------|-------|
| Token Economy | /10 | Is the prompt unnecessarily verbose? |
| Clarity | /10 | Are instructions unambiguous and direct? |
| Structure | /10 | Is information organized optimally? |
| Redundancy | /10 | Any repeated or unnecessary content? |

### Efficacy (weight: 0.6)
| Metric | Score | Notes |
|--------|-------|-------|
| Instruction Adherence | /10 | Does the prompt clearly specify ALL requirements? |
| Output Controllability | /10 | Can output format be predicted/validated? |
| Constraint Enforcement | /10 | Are rules explicit and enforceable? |
| Goal Alignment | /10 | Does prompt directly achieve stated objective? |

---

## PHASE 3: GAP ANALYSIS

Document each issue found:

| Issue | Location | Impact | Root Cause | Fix |
|-------|----------|--------|------------|-----|
| Missing validation checklist | Entire prompt | HIGH | No verification steps | Add Phase 6 validation |
| No quantitative metrics | Output section | MEDIUM | No success metrics | Add token reduction % |
| Missing comparison table | Output section | MEDIUM | No before/after | Add comparison table |

---

## PHASE 4: QUANTITATIVE ANALYSIS

Calculate improvements:

- **Token Reduction %:** ~15% (by consolidating steps)
- **Instruction Adherence %:** Expected +25% (clearer phases)
- **Output Quality %:** Expected +30% (structured validation)

**Target:** Minimum 20% improvement

---

## PHASE 5: REWRITTEN PROMPT

### Role Definition
You are a QA Engineer specializing in API testing and remediation planning.

### Instructions

Run the live tests located in `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/`, document all responses, including errors/failures, and generate a remediation plan.

### Execution Steps

**Step 1:** Run the Live Tests

Execute:
```bash
cd /Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests
python -m pytest . -v --tb=short 2>&1 | tee test_results.log
```

**Step 2:** Document Errors AND Responses

For EACH test (passed AND failed), record:
- Test name and file
- **Full response body** (JSON formatted, not truncated)
- HTTP status code
- For failures: exact error message
- Category: AUTH | VALIDATION | NOT_IMPLELEMENTED | INFRASTRUCTURE | LOGIC | UNKNOWN

**CRITICAL:** Show the actual response objects, not just failure summaries. Include:
- Successful responses: show the JSON payload returned
- Failed responses: show error messages and status codes

Example format:
```json
{
  "test_name": "test_auth_login",
  "status": "PASSED",
  "status_code": 200,
  "response": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

**Step 3:** Generate Remediation Plan

Create `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/REMEDIATION_PLAN.md`

### Constraints

1. Tests must execute without Python exceptions
2. All 9 test files must be run
3. Results must be saved to test_results.log
4. Remediation plan must include priority rankings

### Output Format

```markdown
# Live Test Remediation Plan

**Date:** YYYY-MM-DD
**API Base:** https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod

## Executive Summary
- Total Tests: X | Passed: X | Failed: X | Skipped: X

## Test Results Table
| Test File | Tests | Passed | Failed | Skipped | Primary Errors |

## Response Objects

For EACH test, include the full response:

### Passed Tests - Response Objects
```json
{
  "test_name": "...",
  "endpoint": "...",
  "status_code": 200,
  "response_body": { ... }
}
```

### Failed Tests - Response Objects
```json
{
  "test_name": "...",
  "endpoint": "...",
  "status_code": 401,
  "response_body": { "error": "..." },
  "error_message": "..."
}
```

## Issues by Category
### AUTH Issues
| Test | Endpoint | Error | Fix |
### VALIDATION Issues
| Test | Endpoint | Error | Fix |
### NOT_IMPLEMENTED Issues
| Test | Endpoint | Error | Fix |
### INFRASTRUCTURE Issues
| Test | Endpoint | Error | Fix |

## Priority Items
1. [P0] - Description
2. [P1] - Description
3. [P2] - Description
```

---

## PHASE 6: VALIDATION CHECKLIST

Before completing, verify:

- [ ] Clear role definition
- [ ] Explicit output format
- [ ] Validation criteria embedded
- [ ] Numbered constraints
- [ ] No ambiguity
- [ ] No unnecessary content
- [ ] Chain-of-thought for complex tasks
- [ ] Measurable success criteria

---

## OUTPUT

Save:
1. `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/REMEDIATION_PLAN.md` - Full remediation plan
2. `/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/test_results.log` - Raw test output
