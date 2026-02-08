# Phase 11: Gap Analysis - Engineer Implementation Prompt

**Date:** 2026-02-04
**Engineer:** Minimax
**Architect:** Claude Sonnet 4.5
**Methodology:** Test-Driven Development (TDD) - RED → GREEN → REFACTOR

---

## 🎯 Mission: Implement Gap Analysis Feature

You are Minimax, the Implementation Engineer. The Architect has completed all design, specification, and test suite creation. Your job is to implement the code to make the tests pass.

**CRITICAL RULES (from CLAUDE.md):**

1. ✅ **ALWAYS run tests after completing each task**
2. ✅ **Follow strict TDD workflow: RED (tests fail) → GREEN (tests pass) → REFACTOR**
3. ✅ **Use oh-my-claudecode delegation for complex work** (e.g., `executor` agents)
4. ✅ **Follow "Layered Monarchy" pattern: Handler → Logic → DAL**
5. ✅ **All logic functions return `Result[T]`**
6. ✅ **Use AWS Powertools decorators: @logger, @tracer, @metrics**
7. ✅ **Validate all inputs via Pydantic models**
8. ✅ **NO AI detection patterns** - write natural, human-like code
9. ✅ **Run verification commands after EVERY change**
10. ✅ **Zero errors required before marking task complete**

---

## 📋 Pre-Implementation: Read Architecture

**MANDATORY READING ORDER:**

1. **Start Here:** Read [ARCHITECT_SIGN_OFF.md](./ARCHITECT_SIGN_OFF.md)
   - Complete handoff summary
   - All deliverables listed
   - Implementation checklist

2. **Architecture & Design:**
   - [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
   - [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md) (for context, not used in Phase 11)

3. **API Specification:**
   - [GAP_SPEC.md](../../specs/gap-analysis/GAP_SPEC.md)

4. **Task Documentation:**
   - [README.md](./README.md) - Master task list
   - Read each task file (task-01 through task-09) in order

---

## 🚦 Phase 0: Verify RED Tests (CRITICAL FIRST STEP)

**Before writing ANY code, verify all tests are currently FAILING.**

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run ALL gap analysis tests
uv run pytest tests/gap-analysis/ -v --tb=short

# Expected output: ALL TESTS FAIL
# This confirms you're starting from RED phase
```

**If tests don't fail:** STOP and investigate. The test suite should fail because no implementation exists yet.

---

## 📦 Implementation Tasks (Execute in Order)

### Task 01: Foundation - Validation Utilities

**File:** `src/backend/careervp/handlers/utils/validation.py`
**Task Doc:** [task-01-async-foundation.md](./task-01-async-foundation.md)
**Tests:** `tests/gap-analysis/unit/test_validation.py` (18 tests)

#### Implementation Steps:

1. Create the file with constants and functions:
   ```python
   # careervp/handlers/utils/validation.py
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   MAX_TEXT_LENGTH = 1_000_000  # 1M characters

   def validate_file_size(content: bytes) -> None:
       """Validate file size doesn't exceed 10MB."""
       if len(content) > MAX_FILE_SIZE:
           raise ValueError(f"File size {len(content)} bytes exceeds maximum {MAX_FILE_SIZE} bytes")

   def validate_text_length(text: str) -> None:
       """Validate text length doesn't exceed 1M characters."""
       if len(text) > MAX_TEXT_LENGTH:
           raise ValueError(f"Text length {len(text)} characters exceeds maximum {MAX_TEXT_LENGTH} characters")
   ```

2. **Run format/lint/type-check:**
   ```bash
   uv run ruff format careervp/handlers/utils/validation.py
   uv run ruff check --fix careervp/handlers/utils/validation.py
   uv run mypy careervp/handlers/utils/validation.py --strict
   ```

3. **Run tests for THIS task:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_validation.py -v
   # Expected: 18 tests PASS
   ```

4. **Verify coverage:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_validation.py --cov=careervp.handlers.utils.validation --cov-report=term-missing
   # Expected: 100% coverage
   ```

✅ **Task 01 Complete** when all 18 tests pass.

---

### Task 02: Infrastructure Setup (CDK)

**File:** `infra/careervp/api_construct.py`
**Task Doc:** [task-02-infrastructure.md](./task-02-infrastructure.md)
**Tests:** `tests/gap-analysis/infrastructure/test_gap_analysis_stack.py` (10 tests)

#### Implementation Steps:

1. Add Lambda function to `api_construct.py`:
   ```python
   # In ApiConstruct class
   self.gap_analysis_fn = _lambda.Function(
       self,
       "GapAnalysisFunction",
       function_name=f"careervp-gap-analysis-lambda-{props.stage}",
       runtime=_lambda.Runtime.PYTHON_3_14,
       handler="careervp.handlers.gap_handler.lambda_handler",
       code=_lambda.Code.from_asset("../src/backend"),
       timeout=Duration.seconds(120),
       memory_size=512,
       environment={
           "USERS_TABLE_NAME": props.users_table.table_name,
           "ANTHROPIC_API_KEY": props.anthropic_api_key,
           "LOG_LEVEL": "INFO",
       },
   )
   ```

2. Add API Gateway route:
   ```python
   # Add POST /api/gap-analysis route
   self.api.add_routes(
       path="/api/gap-analysis",
       methods=[apigwv2.HttpMethod.POST],
       integration=apigwv2_integrations.HttpLambdaIntegration(
           "GapAnalysisIntegration",
           self.gap_analysis_fn,
       ),
       authorizer=props.authorizer,
   )
   ```

3. Grant DynamoDB permissions:
   ```python
   props.users_table.grant_read_data(self.gap_analysis_fn)
   ```

4. **Run CDK synth:**
   ```bash
   cd /Users/yitzchak/Documents/dev/careervp/infra
   npx cdk synth
   # Expected: No errors, template generated
   ```

5. **Run infrastructure tests:**
   ```bash
   cd ../src/backend
   uv run pytest tests/gap-analysis/infrastructure/ -v
   # Expected: 10 tests PASS
   ```

✅ **Task 02 Complete** when CDK synth succeeds and all 10 infrastructure tests pass.

---

### Task 03: Gap Analysis Logic

**File:** `src/backend/careervp/logic/gap_analysis.py`
**Task Doc:** [task-03-gap-analysis-logic.md](./task-03-gap-analysis-logic.md)
**Tests:** `tests/gap-analysis/unit/test_gap_analysis_logic.py` (23 tests)

#### Implementation Steps:

1. Implement `calculate_gap_score()`:
   ```python
   def calculate_gap_score(impact: str, probability: str) -> float:
       """Calculate gap score using weighted formula."""
       score_map = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}
       impact_score = score_map[impact]
       probability_score = score_map[probability]
       gap_score = (0.7 * impact_score) + (0.3 * probability_score)
       return round(gap_score, 2)
   ```

2. Implement `generate_gap_questions()` (async):
   - Call LLM with user CV and job posting
   - Parse JSON response
   - Calculate gap_score for each question
   - Sort by gap_score descending
   - Return top 5 questions

3. **Follow task-03 documentation for complete implementation details.**

4. **Run format/lint/type-check:**
   ```bash
   uv run ruff format careervp/logic/gap_analysis.py
   uv run ruff check --fix careervp/logic/gap_analysis.py
   uv run mypy careervp/logic/gap_analysis.py --strict
   ```

5. **Run tests for THIS task:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_gap_analysis_logic.py -v
   # Expected: 23 tests PASS
   ```

✅ **Task 03 Complete** when all 23 tests pass.

---

### Task 04: Gap Analysis Prompt Generation

**File:** `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`
**Task Doc:** [task-04-gap-analysis-prompt.md](./task-04-gap-analysis-prompt.md)
**Tests:** `tests/gap-analysis/unit/test_gap_prompt.py` (15 tests)

#### Implementation Steps:

1. Implement system prompt:
   ```python
   def create_gap_analysis_system_prompt(language: str = 'en') -> str:
       """Create system prompt for gap analysis."""
       # Return complete system prompt as documented in task-04
   ```

2. Implement user prompt:
   ```python
   def create_gap_analysis_user_prompt(
       cv_data: dict,
       job_data: dict,
       language: str = 'en'
   ) -> str:
       """Create user prompt with CV and job posting."""
       # Format CV and job posting
       # Return complete user prompt
   ```

3. Implement formatting helpers:
   - `_format_cv_for_prompt()`
   - `_format_job_for_prompt()`

4. **Follow task-04 documentation for complete prompt templates.**

5. **Run tests:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_gap_prompt.py -v
   # Expected: 15 tests PASS
   ```

✅ **Task 04 Complete** when all 15 tests pass.

---

### Task 05: Gap Handler (Lambda Entry Point)

**File:** `src/backend/careervp/handlers/gap_handler.py`
**Task Doc:** [task-05-gap-handler.md](./task-05-gap-handler.md)
**Tests:**
- Unit: `tests/gap-analysis/unit/test_gap_handler_unit.py` (14 tests)
- Integration: `tests/gap-analysis/integration/test_gap_submit_handler.py` (20+ tests)

#### Implementation Steps:

1. Implement helper functions:
   ```python
   def _cors_headers() -> dict[str, str]:
       """Return CORS headers."""
       return {
           'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Headers': 'Content-Type,Authorization',
           'Content-Type': 'application/json'
       }

   def _error_response(status_code: int, message: str, code: str) -> dict:
       """Create error response."""
       return {
           'statusCode': status_code,
           'headers': _cors_headers(),
           'body': json.dumps({'error': message, 'code': code})
       }
   ```

2. Implement Lambda handler:
   ```python
   @logger.inject_lambda_context(log_event=True)
   @tracer.capture_lambda_handler(capture_response=False)
   @metrics.log_metrics(capture_cold_start_metric=True)
   def lambda_handler(event: dict, context: LambdaContext) -> dict:
       """POST /api/gap-analysis endpoint."""
       # 1. Extract and validate request
       # 2. Get user CV from DAL
       # 3. Call gap_analysis.generate_gap_questions()
       # 4. Return response
   ```

3. **Follow task-05 documentation for complete implementation.**

4. **Run unit tests:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_gap_handler_unit.py -v
   # Expected: 14 tests PASS
   ```

5. **Run integration tests:**
   ```bash
   uv run pytest tests/gap-analysis/integration/test_gap_submit_handler.py -v
   # Expected: 20+ tests PASS
   ```

✅ **Task 05 Complete** when all unit and integration tests pass.

---

### Task 06: Pydantic Models

**File:** `src/backend/careervp/models/gap_analysis.py`
**Task Doc:** [task-05-gap-handler.md](./task-05-gap-handler.md) (models section)
**Tests:** `tests/gap-analysis/unit/test_gap_models.py` (20 tests)

#### Implementation Steps:

1. Create Pydantic models:
   ```python
   from pydantic import BaseModel, Field
   from typing import Literal

   class GapAnalysisRequest(BaseModel):
       user_id: str
       cv_id: str
       job_posting: JobPosting
       language: Literal['en', 'he'] = 'en'

   class GapQuestion(BaseModel):
       question_id: str
       question: str
       impact: Literal['HIGH', 'MEDIUM', 'LOW']
       probability: Literal['HIGH', 'MEDIUM', 'LOW']
       gap_score: float = Field(ge=0.0, le=1.0)

   class GapAnalysisResponse(BaseModel):
       questions: list[GapQuestion]
       metadata: dict
   ```

2. **Run tests:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_gap_models.py -v
   # Expected: 20 tests PASS
   ```

✅ **Task 06 Complete** when all 20 tests pass.

---

### Task 07: DAL Extensions (OPTIONAL)

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py`
**Task Doc:** [task-06-dal-extensions.md](./task-06-dal-extensions.md)
**Tests:** `tests/gap-analysis/unit/test_gap_dal_unit.py` (10 tests)

**NOTE:** This task is OPTIONAL for Phase 11 (synchronous implementation).

#### If Implementing:

1. Add methods to DynamoDalHandler:
   ```python
   def save_gap_analysis(
       self,
       user_id: str,
       cv_id: str,
       job_posting_id: str,
       questions: list[dict],
       version: int = 1
   ) -> Result[None]:
       """Save gap analysis to DynamoDB."""
       # Implementation with 90-day TTL

   def get_gap_analysis(
       self,
       user_id: str,
       cv_id: str,
       job_posting_id: str,
       version: int = 1
   ) -> Result[dict]:
       """Retrieve gap analysis from DynamoDB."""
       # Implementation
   ```

2. **Run tests:**
   ```bash
   uv run pytest tests/gap-analysis/unit/test_gap_dal_unit.py -v
   # Expected: 10 tests PASS
   ```

✅ **Task 07 Complete** when all 10 tests pass (if implemented).

---

### Task 08: Integration Testing

**Task Doc:** [task-07-integration-tests.md](./task-07-integration-tests.md)
**Tests:** `tests/gap-analysis/integration/` (20+ tests)

#### Verification Steps:

1. **Run all integration tests:**
   ```bash
   uv run pytest tests/gap-analysis/integration/ -v
   # Expected: All tests PASS
   ```

2. **Verify Handler → Logic → DAL flow:**
   - Test with mocked DynamoDB
   - Test with mocked LLM client
   - Test error scenarios

✅ **Task 08 Complete** when all integration tests pass.

---

### Task 09: E2E Verification

**Task Doc:** [task-08-e2e-verification.md](./task-08-e2e-verification.md)
**Tests:** `tests/gap-analysis/e2e/` (8 tests)

#### Verification Steps:

1. **Run E2E tests:**
   ```bash
   uv run pytest tests/gap-analysis/e2e/ -v
   # Expected: All tests PASS
   ```

2. **Run full test suite:**
   ```bash
   uv run pytest tests/gap-analysis/ -v --tb=short
   # Expected: 150+ tests PASS
   ```

3. **Check coverage:**
   ```bash
   uv run pytest tests/gap-analysis/ --cov=careervp --cov-report=html
   # Expected: ≥90% coverage
   ```

✅ **Task 09 Complete** when all E2E tests pass and coverage ≥90%.

---

## 🚀 Deployment

**Task Doc:** [task-09-deployment.md](./task-09-deployment.md)

### Deployment Steps:

1. **Final verification:**
   ```bash
   cd /Users/yitzchak/Documents/dev/careervp/src/backend

   # Format all files
   uv run ruff format .

   # Lint all files
   uv run ruff check --fix .

   # Type check
   uv run mypy careervp --strict

   # All tests
   uv run pytest tests/gap-analysis/ -v
   ```

2. **Deploy to AWS:**
   ```bash
   cd ../../infra
   cdk deploy --all
   ```

3. **Verify deployment:**
   ```bash
   # Check Lambda exists
   aws lambda get-function --function-name careervp-gap-analysis-lambda-dev

   # Tail logs
   aws logs tail /aws/lambda/careervp-gap-analysis-lambda-dev --follow
   ```

4. **Test live endpoint:**
   ```bash
   # Use curl or Postman to test POST /api/gap-analysis
   # See task-08-e2e-verification.md for test payloads
   ```

---

## ✅ Completion Checklist

### Code Quality (MANDATORY)

- [ ] All files formatted with `ruff format`
- [ ] All files pass `ruff check --fix`
- [ ] All files pass `mypy --strict`
- [ ] Zero linting errors
- [ ] Zero type errors

### Testing (MANDATORY)

- [ ] All 150+ tests pass (GREEN phase)
- [ ] Code coverage ≥90%
- [ ] Unit tests pass for each task
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Infrastructure tests pass

### Deployment (MANDATORY)

- [ ] CDK synth succeeds
- [ ] CDK deploy succeeds
- [ ] Lambda function exists in AWS
- [ ] API Gateway route accessible
- [ ] CloudWatch logs show successful invocations

### Documentation (MANDATORY)

- [ ] All task docs read and followed
- [ ] Implementation matches architectural design
- [ ] "Layered Monarchy" pattern followed
- [ ] Result[T] pattern used for all logic functions
- [ ] AWS Powertools decorators applied

---

## 🚨 Common Pitfalls to Avoid

1. **Don't skip tests after each task** - Run tests immediately after implementing each task
2. **Don't guess at implementation details** - Follow task documentation exactly
3. **Don't modify architectural decisions** - Implement as designed (synchronous, not async)
4. **Don't skip validation commands** - Run ruff/mypy after every file change
5. **Don't create new patterns** - Follow existing VPR handler pattern
6. **Use correct model** - Use Claude Sonnet 4.5 (TaskMode.STRATEGIC) for complex reasoning
7. **Don't exceed question limit** - Maximum 5 questions
8. **Don't skip error handling** - All scenarios must handle errors gracefully

---

## 📚 Reference Files

### Architecture & Design
- [ARCHITECT_SIGN_OFF.md](./ARCHITECT_SIGN_OFF.md)
- [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
- [GAP_SPEC.md](../../specs/gap-analysis/GAP_SPEC.md)

### Task Documentation (Read in Order)
1. [task-01-async-foundation.md](./task-01-async-foundation.md)
2. [task-02-infrastructure.md](./task-02-infrastructure.md)
3. [task-03-gap-analysis-logic.md](./task-03-gap-analysis-logic.md)
4. [task-04-gap-analysis-prompt.md](./task-04-gap-analysis-prompt.md)
5. [task-05-gap-handler.md](./task-05-gap-handler.md)
6. [task-06-dal-extensions.md](./task-06-dal-extensions.md) (OPTIONAL)
7. [task-07-integration-tests.md](./task-07-integration-tests.md)
8. [task-08-e2e-verification.md](./task-08-e2e-verification.md)
9. [task-09-deployment.md](./task-09-deployment.md)

### Test Files (150+ tests)
- `tests/gap-analysis/unit/test_validation.py`
- `tests/gap-analysis/unit/test_gap_analysis_logic.py`
- `tests/gap-analysis/unit/test_gap_prompt.py`
- `tests/gap-analysis/unit/test_gap_handler_unit.py`
- `tests/gap-analysis/unit/test_gap_dal_unit.py`
- `tests/gap-analysis/unit/test_gap_models.py`
- `tests/gap-analysis/integration/test_gap_submit_handler.py`
- `tests/gap-analysis/infrastructure/test_gap_analysis_stack.py`
- `tests/gap-analysis/e2e/test_gap_analysis_flow.py`

### Existing Patterns to Follow
- **Handler pattern:** `careervp/handlers/vpr_handler.py`
- **Logic pattern:** `careervp/logic/vpr_generator.py`
- **DAL pattern:** `careervp/dal/dynamo_dal_handler.py`

---

## 💬 Questions?

If you encounter issues:

1. **Check task documentation first** - All implementation details are provided
2. **Review test files** - Tests show expected behavior
3. **Follow existing patterns** - VPR handler is the reference implementation
4. **Verify prerequisites** - Ensure previous tasks completed successfully

---

## 🎯 Success Criteria

**You are DONE when:**

1. ✅ All 150+ tests pass (GREEN phase)
2. ✅ Code coverage ≥90%
3. ✅ Zero ruff/mypy errors
4. ✅ CDK deployment successful
5. ✅ Live endpoint returns gap analysis questions
6. ✅ CloudWatch logs show successful processing

**Estimated Time:** 12-16 hours (based on task documentation estimates)

---

**Good luck, Minimax! The architecture is solid and the tests are comprehensive. Follow the TDD workflow, run tests after each task, and you'll have this feature working in no time.** 🚀

---

*Created by: Claude Sonnet 4.5 (Lead Architect)*
*Date: February 4, 2026*
*Phase: 11 - Gap Analysis*
*Status: Ready for Implementation*
