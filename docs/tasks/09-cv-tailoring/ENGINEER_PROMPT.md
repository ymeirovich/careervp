# Phase 9: CV Tailoring - Engineer Implementation Prompt

**Date:** 2026-02-05
**Phase:** 9 - CV Tailoring
**Status:** Ready for Implementation
**Total Duration:** 19 hours | 11 tasks | 165-205 tests

---

## MISSION STATEMENT

You are implementing Phase 9: CV Tailoring for CareerVP. This phase adds an intelligent resume optimization engine that tailors master CVs to specific job descriptions while preserving factual accuracy through the Fact Verification System (FVS).

### 10 Critical Rules (From CLAUDE.md)

1. **Follow Layered Monarchy Pattern Strictly**: Handler → Logic → DAL (no cross-layer communication)
2. **Use Result[T] Pattern Everywhere**: All logic functions return `Result[T]` with success/error/code
3. **Enforce FVS Validation Always**: IMMUTABLE facts (dates, companies, roles) must NEVER be modified
4. **Synchronous Lambda Only**: Use synchronous pattern like cv_upload_handler.py (NOT async/SQS)
5. **AWS Powertools Integration**: Use Logger, Tracer, APIGatewayRestResolver for all handlers
6. **Haiku 4.5 via TaskMode**: Use Claude Haiku 4.5 for LLM calls (cost-optimized, template-based)
7. **Type Hints Mandatory**: Every function must have full type hints (run `mypy --strict` after each task)
8. **Test-After-Each-Task Enforcement**: Run pytest after EVERY task completion (do not batch tests)
9. **No Assumptions About APIs**: Always verify API contracts in official docs before implementation
10. **Coverage ≥ 90%**: Each task must achieve 90%+ code coverage before moving to next task

---

## PRE-IMPLEMENTATION READING CHECKLIST

Before starting ANY implementation, read these documents in order:

- [ ] **This File**: ENGINEER_PROMPT.md (you are reading it)
- [ ] **Architecture**: `/docs/architecture/CV_TAILORING_DESIGN.md` - System design decisions
- [ ] **Specification**: `/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md` - API contracts
- [ ] **Task Breakdown**: `/docs/tasks/09-cv-tailoring/README.md` - Task overview and dependencies
- [ ] **Existing Patterns**: `src/backend/careervp/handlers/cv_upload_handler.py` - Handler template
- [ ] **FVS Pattern**: `src/backend/careervp/logic/fvs_validator.py` - FVS validation example

**Estimated Reading Time:** 45 minutes
**Do NOT skip this step.** Architecture violations will cause late-stage failures.

---

## PHASE 0: RED TEST VERIFICATION (CRITICAL)

Before implementing ANY code, verify that ALL tests fail (RED state):

```bash
cd src/backend

# Verify all CV tailoring tests are RED (fail)
uv run pytest tests/cv-tailoring/ -v

# Expected: 0 passed, 165-205 failed
# If tests pass, someone already implemented code - investigate before proceeding
```

**Why This Matters:** TDD requires starting from RED. If tests pass before implementation, requirements weren't properly captured.

**Action if Tests Pass:** Stop and investigate. Review task documentation.

---

## TASK-BY-TASK IMPLEMENTATION GUIDE

### TASK 01: Validation Utilities

**File:** `src/backend/careervp/handlers/utils/validation.py` (new)
**Purpose:** Common validation functions for CV tailoring
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 15-20

#### Implementation Steps

1. **Create validation module** with these functions:
   ```python
   def validate_cv_id(cv_id: str) -> Result[str]:
       """Validate cv_id format (non-empty, max 255 chars)."""
       if not cv_id or len(cv_id) > 255:
           return Result(success=False, error="Invalid cv_id",
                        code=ResultCode.INVALID_INPUT)
       return Result(success=True, data=cv_id)

   def validate_job_description(job_desc: str) -> Result[str]:
       """Validate job description length (50-50,000 chars)."""
       if len(job_desc) < 50:
           return Result(success=False,
                        error="Job description too short (min 50 chars)",
                        code=ResultCode.JOB_DESCRIPTION_TOO_SHORT)
       if len(job_desc) > 50000:
           return Result(success=False,
                        error="Job description too long (max 50,000 chars)",
                        code=ResultCode.JOB_DESCRIPTION_TOO_LONG)
       return Result(success=True, data=job_desc)

   def validate_tailoring_preferences(
       preferences: Optional[TailoringPreferences]
   ) -> Result[Optional[TailoringPreferences]]:
       """Validate tailoring preferences (tone, length, emphasis)."""
       if preferences is None:
           return Result(success=True, data=None)
       # Validate enums
       valid_tones = {"professional", "casual", "technical"}
       if preferences.tone and preferences.tone not in valid_tones:
           return Result(success=False, error=f"Invalid tone: {preferences.tone}",
                        code=ResultCode.INVALID_INPUT)
       # Similar validation for length, emphasis
       return Result(success=True, data=preferences)
   ```

2. **Use Result[T] Pattern:** All functions return `Result[T]` with error handling
3. **Add Type Hints:** Every parameter and return type must be annotated
4. **Add Docstrings:** Every function needs a docstring with Args/Returns

#### Verification Commands

```bash
cd src/backend

# Format
uv run ruff format careervp/handlers/utils/validation.py

# Lint
uv run ruff check --fix careervp/handlers/utils/validation.py

# Type check
uv run mypy careervp/handlers/utils/validation.py --strict

# Run tests
uv run pytest tests/cv-tailoring/unit/test_validation.py -v

# Expected: 15-20 tests PASS, 100% coverage
```

#### Completion Criteria

- [ ] All validation functions implemented with type hints
- [ ] All 15-20 tests PASS (GREEN)
- [ ] `ruff format` passes with no changes
- [ ] `ruff check --fix` passes with no errors
- [ ] `mypy --strict` passes with no type errors
- [ ] Code coverage ≥ 100%

---

### TASK 02: Infrastructure (CDK)

**Files:** `infra/careervp/api_construct.py` (modify), `infra/careervp/constants.py` (modify)
**Purpose:** Define Lambda and API Gateway route for CV tailoring
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 10-15

#### Implementation Steps

1. **Add CV Tailoring Lambda** to `api_construct.py`:
   ```python
   # Add constants
   CV_TAILORING_LAMBDA_MEMORY = 512  # MB
   CV_TAILORING_TIMEOUT = 60  # seconds
   CV_TAILORING_RESERVED_CONCURRENCY = 10

   # Create Lambda function
   cv_tailoring_lambda = aws_lambda.Function(
       self, "CVTailoringLambda",
       runtime=aws_lambda.Runtime.PYTHON_3_12,
       handler="careervp.handlers.cv_tailoring_handler.lambda_handler",
       code=aws_lambda.Code.from_asset(
           path=join(dirname(__file__), "../src/backend"),
           bundling=BundlingOptions(
               image=DockerImage.from_build_context(
                   path=join(dirname(__file__), "../src/backend")
               ),
               command=["bash", "-c", "cp -r /asset-input/* /asset-output/"]
           )
       ),
       memory_size=CV_TAILORING_LAMBDA_MEMORY,
       timeout=Duration.seconds(CV_TAILORING_TIMEOUT),
       reserved_concurrent_executions=CV_TAILORING_RESERVED_CONCURRENCY,
       environment={
           "TABLE_NAME": self.table.table_name,
           "BEDROCK_MODEL_ID": "claude-haiku-4-5-20251001",
       }
   )

   # Grant permissions
   self.table.grant_read_write_data(cv_tailoring_lambda)
   ```

2. **Add API Gateway route**:
   ```python
   api.add_routes(
       {
           "POST /api/cv-tailoring": cv_tailoring_lambda,
       }
   )
   ```

3. **Add constants** to `constants.py`:
   ```python
   CV_TAILORING_LAMBDA_NAME = "cv-tailoring-handler"
   CV_TAILORING_TIMEOUT_SECONDS = 60
   CV_TAILORING_MEMORY_MB = 512
   ```

4. **Test CDK synthesis**:
   ```bash
   cd infra
   npx cdk synth
   # Should generate CloudFormation without errors
   ```

#### Verification Commands

```bash
cd src/backend

# Type check infrastructure
uv run mypy ../infra/careervp/ --strict

# Run infrastructure tests
uv run pytest tests/cv-tailoring/infrastructure/test_cv_tailoring_stack.py -v

# Expected: 10-15 tests PASS
```

#### Completion Criteria

- [ ] Lambda function created with correct timeout and memory
- [ ] API Gateway route configured (POST /api/cv-tailoring)
- [ ] All environment variables set
- [ ] CDK synthesis completes without errors
- [ ] All 10-15 infrastructure tests PASS
- [ ] Code coverage ≥ 90%

---

### TASK 03: Tailoring Logic (CORE - HIGH RISK)

**File:** `src/backend/careervp/logic/cv_tailoring.py` (new)
**Purpose:** Core tailoring algorithm with relevance scoring
**Complexity:** High | **Duration:** 3 hours | **Tests:** 25-30

#### Implementation Steps

1. **Implement Relevance Scoring Algorithm**:
   ```python
   def calculate_relevance_score(
       cv_section: str,
       job_requirements: JobRequirements
   ) -> float:
       """
       Calculate relevance score (0.0 to 1.0) using weighted average.

       Weight distribution:
       - 40% keyword match score
       - 35% skill alignment score
       - 25% experience relevance score
       """
       keyword_score = _calculate_keyword_match_score(cv_section, job_requirements.keywords)
       skill_score = _calculate_skill_alignment_score(
           cv_section, job_requirements.required_skills
       )
       exp_score = _calculate_experience_relevance_score(
           cv_section, job_requirements
       )

       final_score = (0.40 * keyword_score) + (0.35 * skill_score) + (0.25 * exp_score)
       return min(max(final_score, 0.0), 1.0)  # Clamp to [0, 1]

   def _calculate_keyword_match_score(cv_text: str, keywords: list[str]) -> float:
       """Calculate TF-IDF style keyword match."""
       cv_tokens = set(cv_text.lower().split())
       keyword_tokens = set(k.lower() for k in keywords)
       matches = len(cv_tokens & keyword_tokens)
       if not keyword_tokens:
           return 0.0
       return min(matches / len(keyword_tokens), 1.0)

   def _calculate_skill_alignment_score(
       cv_text: str, required_skills: list[str]
   ) -> float:
       """Calculate skill alignment using fuzzy matching."""
       # Extract skills from CV text
       cv_skills = _extract_skills_from_text(cv_text)
       if not required_skills:
           return 0.5  # Neutral if no requirements

       matched = 0
       for req_skill in required_skills:
           for cv_skill in cv_skills:
               if _fuzzy_match(cv_skill, req_skill, threshold=0.80):
                   matched += 1
                   break

       return matched / len(required_skills)

   def _calculate_experience_relevance_score(
       cv_text: str, job_requirements: JobRequirements
   ) -> float:
       """Calculate experience relevance based on role, industry, seniority."""
       # Implementation with title similarity, industry match, seniority alignment
       # See CV_TAILORING_DESIGN.md for algorithm details
       pass
   ```

2. **Implement Job Requirements Extraction**:
   ```python
   def extract_job_requirements(job_description: str) -> Result[JobRequirements]:
       """Extract structured requirements from job description."""
       try:
           # Extract title, years, keywords, skills
           requirements = JobRequirements(
               title=_extract_title(job_description),
               required_skills=_extract_required_skills(job_description),
               preferred_skills=_extract_preferred_skills(job_description),
               years_experience=_extract_years(job_description),
               keywords=_extract_keywords(job_description),
               industry=_extract_industry(job_description),
               seniority_level=_extract_seniority(job_description)
           )
           return Result(success=True, data=requirements)
       except Exception as e:
           logger.error("Failed to extract job requirements", error=str(e))
           return Result(
               success=False,
               error="Failed to parse job requirements",
               code=ResultCode.JOB_PARSE_ERROR
           )
   ```

3. **Implement Relevance Scoring Across CV Sections**:
   ```python
   def score_cv_sections(
       master_cv: UserCV,
       job_requirements: JobRequirements
   ) -> Result[dict[str, float]]:
       """Score each CV section for relevance."""
       scores = {}

       # Score experience
       for i, exp in enumerate(master_cv.experience):
           score = calculate_relevance_score(
               f"{exp.company} {exp.role} {exp.description}",
               job_requirements
           )
           scores[f"experience[{i}]"] = score

       # Score skills
       for skill in master_cv.skills:
           score = calculate_relevance_score(skill, job_requirements)
           scores[f"skills.{skill}"] = score

       return Result(success=True, data=scores)
   ```

4. **Main Tailoring Orchestrator**:
   ```python
   def tailor_cv(
       master_cv: UserCV,
       job_description: str,
       preferences: Optional[TailoringPreferences] = None
   ) -> Result[TailoredCV]:
       """
       Main CV tailoring orchestrator.

       Flow:
       1. Extract job requirements
       2. Score CV sections
       3. Build LLM prompt
       4. Call LLM
       5. Parse response
       6. Validate with FVS
       7. Return tailored CV
       """
       # Step 1: Extract requirements
       req_result = extract_job_requirements(job_description)
       if not req_result.success:
           return Result(
               success=False,
               error=req_result.error,
               code=req_result.code
           )
       job_requirements = req_result.data

       # Step 2: Score sections
       score_result = score_cv_sections(master_cv, job_requirements)
       if not score_result.success:
           return Result(success=False, error=score_result.error, code=score_result.code)
       relevance_scores = score_result.data

       # Step 3-7: Continue implementation...
       # See CV_TAILORING_DESIGN.md for complete flow
       pass
   ```

#### Verification Commands

```bash
cd src/backend

# Run tests AFTER implementing each algorithm
uv run pytest tests/cv-tailoring/unit/test_tailoring_logic.py -v

# Run tests incrementally (don't wait until all complete)
uv run pytest tests/cv-tailoring/unit/test_tailoring_logic.py::test_calculate_keyword_match_score -v
uv run pytest tests/cv-tailoring/unit/test_tailoring_logic.py::test_calculate_skill_alignment_score -v

# Type check after each function
uv run mypy careervp/logic/cv_tailoring.py --strict

# Expected: 25-30 tests PASS (incrementally), 95%+ coverage
```

#### Completion Criteria

- [ ] All 3 scoring algorithms implemented (keyword, skill, experience)
- [ ] Job requirements extraction implemented
- [ ] Relevance scoring across all CV sections working
- [ ] Main tailoring orchestrator implemented
- [ ] All 25-30 tests PASS (GREEN)
- [ ] `ruff format` passes
- [ ] `mypy --strict` passes
- [ ] Code coverage ≥ 95%

**Critical Note:** This is the most complex task. Take time to verify each algorithm with unit tests BEFORE moving to the next task.

---

### TASK 04: Tailoring Prompt Engineering

**File:** `src/backend/careervp/logic/prompts/cv_tailoring_prompt.py` (new)
**Purpose:** LLM prompt construction with FVS rules enforcement
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 15-20

#### Implementation Steps

1. **Build System Prompt**:
   ```python
   SYSTEM_PROMPT = """You are a professional CV tailoring assistant. Your task is to optimize a candidate's CV for a specific job description while maintaining strict factual accuracy.

   # Core Principles
   1. NEVER modify IMMUTABLE facts (dates, companies, roles, contact info)
   2. Only use VERIFIABLE skills that exist in the source CV
   3. Exercise creative liberty in FLEXIBLE content (summaries, descriptions)
   4. Optimize for ATS (Applicant Tracking Systems) keyword matching
   5. Prioritize relevant experience over chronological completeness

   # Output Format
   Return a JSON object with TailoredCV structure...
   """
   ```

2. **Build User Prompt Template** with relevance scores:
   ```python
   def build_tailoring_prompt(
       master_cv: UserCV,
       job_description: str,
       relevance_scores: dict[str, float],
       job_requirements: JobRequirements
   ) -> Result[str]:
       """Build complete user prompt with FVS rules."""

       # Annotate CV sections with relevance scores
       annotated_experience = []
       for i, exp in enumerate(master_cv.experience):
           score = relevance_scores.get(f"experience[{i}]", 0.0)
           annotated = f"[Score: {score:.2f}] {exp.company} - {exp.role} ({exp.dates})"
           annotated_experience.append(annotated)

       # Build FVS rules section
       fvs_section = _build_fvs_rules_section(master_cv)

       # Build complete prompt
       prompt = f"""# Job Description
   {job_description}

   # Master CV (with relevance scores)
   Full Name: {master_cv.full_name}
   Contact: {master_cv.contact_info.email}, {master_cv.contact_info.phone}

   Experience:
   {chr(10).join(annotated_experience)}

   Skills:
   {', '.join(master_cv.skills)}

   # Tailoring Instructions
   - Emphasize experiences with score ≥ 0.80 (HIGH PRIORITY)
   - Include experiences with score ≥ 0.60
   - De-emphasize experiences with score 0.40-0.59
   - Exclude experiences with score < 0.40

   {fvs_section}

   # Output Requirements
   1. Return valid JSON (no markdown code blocks)
   2. Preserve all IMMUTABLE facts exactly
   3. Include "changes_made" array
   4. Optimize descriptions for target keywords
   5. Keep professional summary under 150 words
   """

       return Result(success=True, data=prompt)
   ```

3. **Build FVS Rules Section**:
   ```python
   def _build_fvs_rules_section(master_cv: UserCV) -> str:
       """Build CRITICAL FVS enforcement section."""
       immutable_dates = [exp.dates for exp in master_cv.experience]
       immutable_companies = [exp.company for exp in master_cv.experience]
       immutable_roles = [exp.role for exp in master_cv.experience]

       return f"""# FVS RULES (CRITICAL - STRICT ENFORCEMENT)
   IMMUTABLE Facts - NEVER modify these:
   - Dates: {', '.join(immutable_dates)}
   - Companies: {', '.join(immutable_companies)}
   - Roles: {', '.join(immutable_roles)}
   - Email: {master_cv.contact_info.email}
   - Phone: {master_cv.contact_info.phone}

   VERIFIABLE Skills - Can reframe but must exist in source:
   {', '.join(master_cv.skills)}

   FLEXIBLE Content - Full creative liberty:
   - Professional summary
   - Achievement descriptions (preserve IMMUTABLE facts)
   """
   ```

#### Verification Commands

```bash
cd src/backend

# Run prompt tests
uv run pytest tests/cv-tailoring/unit/test_tailoring_prompt.py -v

# Verify prompt structure with specific tests
uv run pytest tests/cv-tailoring/unit/test_tailoring_prompt.py::test_prompt_includes_fvs_rules -v
uv run pytest tests/cv-tailoring/unit/test_tailoring_prompt.py::test_prompt_includes_relevance_scores -v

# Expected: 15-20 tests PASS, 90%+ coverage
```

#### Completion Criteria

- [ ] System prompt created and documented
- [ ] User prompt template builds correctly with relevance scores
- [ ] FVS rules section explicitly included in prompt
- [ ] All 15-20 tests PASS
- [ ] `mypy --strict` passes
- [ ] Code coverage ≥ 90%

---

### TASK 05: FVS Integration

**File:** `src/backend/careervp/logic/cv_tailoring.py` (extend Task 03)
**Purpose:** Validate tailored CV against FVS baseline
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 20-25

#### Implementation Steps

1. **Create FVS Baseline from Master CV**:
   ```python
   def create_fvs_baseline(master_cv: UserCV) -> dict[str, Any]:
       """Create FVS baseline from master CV for post-tailoring validation."""
       return {
           "full_name": master_cv.full_name,
           "immutable_facts": {
               "contact_info": {
                   "email": master_cv.contact_info.email,
                   "phone": master_cv.contact_info.phone
               },
               "work_history": [
                   {
                       "company": exp.company,
                       "role": exp.role,
                       "dates": exp.dates
                   }
                   for exp in master_cv.experience
               ],
               "education": [
                   {
                       "institution": edu.institution,
                       "degree": edu.degree
                   }
                   for edu in master_cv.education
               ]
           },
           "verifiable_skills": master_cv.skills,
           "flexible_content": {
               "professional_summary": master_cv.professional_summary
           }
       }
   ```

2. **Integrate FVS Validation into Tailoring Flow**:
   ```python
   def tailor_cv(
       master_cv: UserCV,
       job_description: str,
       preferences: Optional[TailoringPreferences] = None
   ) -> Result[TailoredCV]:
       """Main tailoring orchestrator with FVS validation."""

       # ... previous steps (extract requirements, score, build prompt, call LLM) ...

       # Create FVS baseline BEFORE calling LLM
       fvs_baseline = create_fvs_baseline(master_cv)

       # Parse LLM response into TailoredCV
       tailored_cv = _parse_llm_response(llm_output)

       # Step 6: Validate with FVS
       from careervp.logic.fvs_validator import validate_cv_against_baseline

       fvs_result = validate_cv_against_baseline(fvs_baseline, tailored_cv)

       if not fvs_result.success or fvs_result.data.has_critical_violations:
           logger.error(
               "FVS validation failed",
               violations=fvs_result.data.violations
           )
           return Result(
               success=False,
               error=f"FVS validation failed: {len(fvs_result.data.violations)} violations",
               code=ResultCode.FVS_HALLUCINATION_DETECTED
           )

       # If only warnings, log but continue
       if fvs_result.data.violations:
           logger.warning(
               "FVS warnings detected",
               violations=fvs_result.data.violations
           )

       # Store FVS result in tailored CV
       tailored_cv.fvs_validation = fvs_result.data

       return Result(success=True, data=tailored_cv)
   ```

3. **Test FVS Violations**:
   ```python
   def test_fvs_rejects_modified_company_name():
       """CRITICAL: FVS must reject modified company names."""
       # Create baseline with "Google"
       baseline = {"immutable_facts": {"work_history": [{"company": "Google"}]}}

       # Create tailored CV that changed it to "Alphabet"
       tailored = UserCV(experience=[Experience(company="Alphabet", ...)])

       # Should fail
       fvs_result = validate_cv_against_baseline(baseline, tailored)
       assert not fvs_result.success
       assert fvs_result.data.has_critical_violations
   ```

#### Verification Commands

```bash
cd src/backend

# Run FVS integration tests
uv run pytest tests/cv-tailoring/unit/test_fvs_integration.py -v

# Verify CRITICAL violation detection
uv run pytest tests/cv-tailoring/unit/test_fvs_integration.py::test_fvs_rejects_modified_dates -v
uv run pytest tests/cv-tailoring/unit/test_fvs_integration.py::test_fvs_rejects_modified_company -v
uv run pytest tests/cv-tailoring/unit/test_fvs_integration.py::test_fvs_rejects_modified_role -v

# Expected: 20-25 tests PASS, 95%+ coverage
```

#### Completion Criteria

- [ ] FVS baseline creation implemented
- [ ] FVS validation integrated into tailoring flow
- [ ] CRITICAL violations correctly reject tailoring
- [ ] WARNING violations logged but don't reject
- [ ] All 20-25 tests PASS
- [ ] `mypy --strict` passes
- [ ] Code coverage ≥ 95%

**CRITICAL ENFORCEMENT:** FVS validation MUST pass before moving to Task 06.

---

### TASK 06: Tailoring Handler (Lambda)

**File:** `src/backend/careervp/handlers/cv_tailoring_handler.py` (new)
**Purpose:** Lambda handler orchestrating entire CV tailoring request
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 15-20

#### Implementation Steps

1. **Create Handler Structure** (follow cv_upload_handler.py pattern):
   ```python
   """
   CV Tailoring Handler.
   Per CLAUDE.md: Handler -> Logic -> DAL pattern.

   Handles CV tailoring requests, orchestrates logic and storage.
   """

   import json
   import time
   from http import HTTPStatus

   from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
   from aws_lambda_powertools.utilities.parser import ValidationError, parse
   from aws_lambda_powertools.utilities.typing import LambdaContext
   from aws_lambda_env_modeler import get_environment_variables

   from careervp.dal.dynamo_dal_handler import DynamoDalHandler
   from careervp.handlers.models.env_vars import CVTailoringEnvVars
   from careervp.handlers.utils.observability import logger, tracer
   from careervp.handlers.utils.validation import (
       validate_cv_id,
       validate_job_description,
       validate_tailoring_preferences
   )
   from careervp.llm.client import get_llm_client
   from careervp.logic.cv_tailoring import CVTailoringLogic
   from careervp.models.cv_tailoring import TailorCVRequest, TailoredCVResponse
   from careervp.models.result import ResultCode

   app = APIGatewayRestResolver()

   @app.post('/api/cv-tailoring')
   @tracer.capture_method(capture_response=False)
   def handle_cv_tailoring() -> Response:
       """Handle CV tailoring request."""
       start_time = time.time()

       # Get environment variables
       env_vars = get_environment_variables(model=CVTailoringEnvVars)

       # Parse and validate request
       try:
           body = app.current_event.json_body
           request = parse(event=body, model=TailorCVRequest)
       except (ValidationError, TypeError, json.JSONDecodeError) as e:
           logger.warning('Invalid request body', error=str(e))
           response = TailoredCVResponse(
               success=False,
               error=f'Invalid request: {e}',
               code=ResultCode.INVALID_INPUT
           )
           return Response(
               status_code=HTTPStatus.BAD_REQUEST.value,
               body=response.model_dump_json(),
           )

       logger.append_keys(user_id=request.user_id)
       logger.info('Processing CV tailoring request')

       # Validate request fields
       cv_id_result = validate_cv_id(request.cv_id)
       if not cv_id_result.success:
           response = TailoredCVResponse(
               success=False,
               error=cv_id_result.error,
               code=cv_id_result.code
           )
           return Response(
               status_code=HTTPStatus.BAD_REQUEST.value,
               body=response.model_dump_json(),
           )

       job_desc_result = validate_job_description(request.job_description)
       if not job_desc_result.success:
           response = TailoredCVResponse(
               success=False,
               error=job_desc_result.error,
               code=job_desc_result.code
           )
           return Response(
               status_code=_get_status_code(job_desc_result.code),
               body=response.model_dump_json(),
           )

       prefs_result = validate_tailoring_preferences(request.preferences)
       if not prefs_result.success:
           response = TailoredCVResponse(
               success=False,
               error=prefs_result.error,
               code=prefs_result.code
           )
           return Response(
               status_code=HTTPStatus.BAD_REQUEST.value,
               body=response.model_dump_json(),
           )

       # Initialize dependencies and delegate to logic layer
       # IMPORTANT: Handler does NOT access DAL directly - logic layer handles all storage
       dal = DynamoDalHandler(table_name=env_vars.TABLE_NAME)
       llm_client = get_llm_client(model_id=env_vars.BEDROCK_MODEL_ID)

       # Create logic instance with injected dependencies
       cv_tailoring_logic = CVTailoringLogic(dal=dal, llm_client=llm_client)

       # Delegate entire operation to logic layer
       # Logic layer handles: CV fetch, LLM call, FVS validation, artifact storage
       tailoring_result = cv_tailoring_logic.tailor_cv(
           cv_id=request.cv_id,
           user_id=request.user_id,
           job_description=request.job_description,
           job_id=request.job_id,
           preferences=prefs_result.data
       )

       if not tailoring_result.success:
           logger.warning('CV tailoring failed', error=tailoring_result.error)
           response = TailoredCVResponse(
               success=False,
               error=tailoring_result.error,
               code=tailoring_result.code
           )
           status_code = _get_status_code(tailoring_result.code)
           return Response(
               status_code=status_code,
               body=response.model_dump_json(),
           )

       tailored_cv = tailoring_result.data

       # Build success response
       processing_time_ms = int((time.time() - start_time) * 1000)
       response = TailoredCVResponse(
           success=True,
           tailored_cv=tailored_cv,
           code=ResultCode.CV_TAILORED_SUCCESS,
           processing_time_ms=processing_time_ms
       )

       logger.info('CV tailoring completed successfully', processing_time_ms=processing_time_ms)

       return Response(
           status_code=HTTPStatus.OK.value,
           body=response.model_dump_json(),
       )

   def _get_status_code(code: str) -> int:
       """Map result codes to HTTP status codes."""
       mapping = {
           ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST.value,
           ResultCode.JOB_DESCRIPTION_TOO_SHORT: HTTPStatus.BAD_REQUEST.value,
           ResultCode.JOB_DESCRIPTION_TOO_LONG: HTTPStatus.BAD_REQUEST.value,
           ResultCode.CV_NOT_FOUND: HTTPStatus.NOT_FOUND.value,
           ResultCode.FVS_HALLUCINATION_DETECTED: HTTPStatus.BAD_REQUEST.value,
           ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT.value,
           ResultCode.LLM_RATE_LIMITED: HTTPStatus.TOO_MANY_REQUESTS.value,
           ResultCode.STORAGE_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR.value,
       }
       return mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR.value)

   @logger.inject_lambda_context()
   @tracer.capture_lambda_handler(capture_response=False)
   def lambda_handler(event: dict, context: LambdaContext) -> dict:
       """Lambda entry point for CV tailoring."""
       return app.resolve(event, context)
   ```

2. **Add Environment Variables Model**:
   ```python
   # In src/backend/careervp/handlers/models/env_vars.py (extend existing)

   class CVTailoringEnvVars(BaseModel):
       """Environment variables for CV Tailoring Lambda."""
       TABLE_NAME: str
       BEDROCK_MODEL_ID: str = "claude-haiku-4-5-20251001"
   ```

#### Verification Commands

```bash
cd src/backend

# Run handler tests
uv run pytest tests/cv-tailoring/unit/test_tailoring_handler_unit.py -v

# Expected: 15-20 tests PASS, 90%+ coverage
```

#### Completion Criteria

- [ ] Handler follows cv_upload_handler.py pattern
- [ ] Request validation implemented
- [ ] Master CV fetch implemented
- [ ] Tailoring logic orchestration working
- [ ] Artifact storage implemented
- [ ] All 15-20 tests PASS
- [ ] `mypy --strict` passes
- [ ] Code coverage ≥ 90%

---

### TASK 07: DAL Extensions (OPTIONAL)

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py` (extend)
**Purpose:** Add methods for storing and retrieving tailored CV artifacts
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 10-15

#### Implementation Steps

1. **Add methods to DynamoDalHandler**:
   ```python
   def save_artifact(self, artifact: dict[str, Any]) -> Result[str]:
       """Save tailored CV artifact to DynamoDB."""
       try:
           self.table.put_item(Item=artifact)
           return Result(success=True, data=artifact.get("sk", ""))
       except Exception as e:
           logger.exception("Failed to save artifact", error=str(e))
           return Result(
               success=False,
               error="Failed to persist artifact",
               code=ResultCode.STORAGE_ERROR
           )

   def get_tailored_cv(
       self, user_id: str, cv_id: str, job_id: str, version: int = 1
   ) -> Result[dict[str, Any]]:
       """Retrieve tailored CV artifact from DynamoDB."""
       try:
           response = self.table.get_item(
               Key={
                   "pk": user_id,
                   "sk": f"ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v{version}"
               }
           )
           item = response.get("Item")
           if not item:
               return Result(
                   success=False,
                   error="Tailored CV not found",
                   code=ResultCode.NOT_FOUND
               )
           return Result(success=True, data=item)
       except Exception as e:
           logger.exception("Failed to retrieve artifact", error=str(e))
           return Result(
               success=False,
               error="Failed to retrieve artifact",
               code=ResultCode.STORAGE_ERROR
           )
   ```

#### Verification Commands

```bash
cd src/backend

# Run DAL tests
uv run pytest tests/cv-tailoring/unit/test_tailoring_dal_unit.py -v

# Expected: 10-15 tests PASS
```

#### Completion Criteria

- [ ] Artifact storage method implemented
- [ ] Artifact retrieval method implemented
- [ ] All 10-15 tests PASS
- [ ] Code coverage ≥ 90%

---

### TASK 08: Pydantic Models

**File:** `src/backend/careervp/models/cv_tailoring.py` (new)
**Purpose:** Define all request/response models for CV tailoring
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 20-25

#### Implementation Steps

1. **Define Request Models**:
   ```python
   from pydantic import BaseModel, Field
   from typing import Optional

   class TailoringPreferences(BaseModel):
       """User preferences for CV tailoring."""
       tone: Optional[str] = Field(
           default="professional",
           description="'professional', 'casual', or 'technical'"
       )
       length: Optional[str] = Field(
           default="standard",
           description="'compact', 'standard', or 'detailed'"
       )
       emphasis: Optional[str] = Field(
           default="balanced",
           description="'skills', 'experience', or 'balanced'"
       )
       exclude_sections: Optional[list[str]] = None

   class TailorCVRequest(BaseModel):
       """Request to generate tailored CV."""
       user_id: str
       cv_id: str = Field(description="Master CV ID")
       job_description: str = Field(
           min_length=50,
           max_length=50000,
           description="Job description (50-50,000 chars)"
       )
       job_id: Optional[str] = None
       preferences: Optional[TailoringPreferences] = None
   ```

2. **Define Response Models**:
   ```python
   class TailoredCVResponse(BaseModel):
       """Response for CV tailoring request."""
       success: bool
       tailored_cv: Optional[dict] = None
       error: Optional[str] = None
       code: str
       processing_time_ms: int = 0
       cost_estimate: float = 0.00575  # Default Haiku cost
   ```

#### Verification Commands

```bash
cd src/backend

# Run model tests (validation)
uv run pytest tests/cv-tailoring/unit/test_tailoring_models.py -v

# Expected: 20-25 tests PASS, 100% coverage
```

#### Completion Criteria

- [ ] All request models defined with validation
- [ ] All response models defined
- [ ] All 20-25 tests PASS
- [ ] Code coverage ≥ 100%

---

### TASK 09: Integration Tests

**File:** `tests/cv-tailoring/integration/test_tailoring_handler_integration.py` (new)
**Purpose:** Test complete flow (Handler → Logic → DAL → LLM)
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 25-30

#### Implementation Steps

1. **Test Happy Path** (valid request → tailored CV):
   ```python
   def test_cv_tailoring_happy_path(aws_lambda_context, mocked_llm_client):
       """Test complete CV tailoring flow."""
       # Setup: mock LLM response
       mocked_llm_response = {
           "full_name": "John Doe",
           "experience": [...],
           "skills": [...],
           "changes_made": [...]
       }

       # Make request
       response = lambda_handler({
           "body": json.dumps({
               "user_id": "user123",
               "cv_id": "cv123",
               "job_description": "We seek a Senior Python Developer..."
           })
       }, aws_lambda_context)

       # Verify response
       assert response["statusCode"] == 200
       body = json.loads(response["body"])
       assert body["success"] is True
       assert body["tailored_cv"] is not None
   ```

2. **Test FVS Rejection**:
   ```python
   def test_cv_tailoring_rejects_fvs_violations(mocked_llm_client):
       """Test that FVS violations cause rejection."""
       # Mock LLM returning invalid CV (modified company name)
       # Should return 400 with FVS_HALLUCINATION_DETECTED
       pass
   ```

3. **Test Error Handling**:
   ```python
   def test_cv_not_found():
       """Test 404 when CV doesn't exist."""
       pass

   def test_invalid_job_description_too_short():
       """Test 400 when job description < 50 chars."""
       pass

   def test_llm_timeout():
       """Test 504 when LLM times out."""
       pass
   ```

#### Verification Commands

```bash
cd src/backend

# Run integration tests
uv run pytest tests/cv-tailoring/integration/test_tailoring_handler_integration.py -v

# Expected: 25-30 tests PASS, 85%+ coverage
```

#### Completion Criteria

- [ ] Happy path test passing
- [ ] FVS rejection test passing
- [ ] Error handling tests passing
- [ ] All 25-30 tests PASS
- [ ] Code coverage ≥ 85%

---

### TASK 10: E2E Verification

**File:** `tests/cv-tailoring/e2e/test_cv_tailoring_flow.py` (new)
**Purpose:** End-to-end tests against deployed infrastructure
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 10-15

#### Implementation Steps

1. **Test Against Lambda** (real deployed environment):
   ```python
   def test_e2e_cv_tailoring_api():
       """Test against actual API Gateway + Lambda."""
       # Make real HTTP POST to /api/cv-tailoring
       # Verify response format matches spec
       # Verify download URL is valid
       pass
   ```

2. **Test Artifact Storage**:
   ```python
   def test_e2e_tailored_cv_stored_in_dynamodb():
       """Verify tailored CV is actually stored in DynamoDB."""
       # Tailor CV
       # Query DynamoDB for artifact
       # Verify it exists with correct structure
       pass
   ```

#### Verification Commands

```bash
cd src/backend

# Run E2E tests
uv run pytest tests/cv-tailoring/e2e/test_cv_tailoring_flow.py -v

# Expected: 10-15 tests PASS, 80%+ coverage
```

#### Completion Criteria

- [ ] All 10-15 tests PASS
- [ ] API integration verified
- [ ] DynamoDB storage verified
- [ ] Code coverage ≥ 80%

---

### TASK 11: Deployment & Verification

**File:** N/A (operational verification)
**Purpose:** Deploy infrastructure and verify in production
**Complexity:** Low | **Duration:** 1 hour

#### Implementation Steps

1. **Deploy Infrastructure**:
   ```bash
   cd infra
   npx cdk deploy CVTailoringStack
   ```

2. **Verify Lambda Function**:
   ```bash
   aws lambda list-functions | grep cv-tailoring
   ```

3. **Test API Endpoint**:
   ```bash
   curl -X POST https://api.careervp.com/api/cv-tailoring \
     -H "Authorization: Bearer <JWT>" \
     -H "Content-Type: application/json" \
     -d '{
       "cv_id": "cv_123",
       "job_description": "We seek a Senior Python Developer..."
     }'
   ```

4. **Verify Monitoring**:
   - Check CloudWatch logs for errors
   - Check X-Ray traces for latency
   - Verify DynamoDB write metrics

#### Completion Criteria

- [ ] Infrastructure deployed successfully
- [ ] Lambda function accessible
- [ ] API endpoint responding
- [ ] CloudWatch monitoring active
- [ ] No errors in logs
- [ ] Latency within SLA (< 30 seconds p95)

---

## DEPLOYMENT GUIDE

### Pre-Deployment Verification

Before deploying to production, complete this checklist:

```bash
cd src/backend

# 1. Run ALL tests
uv run pytest tests/cv-tailoring/ -v --cov=careervp --cov-report=html
# Expected: 165-205 tests PASS, ≥90% coverage

# 2. Format and lint
uv run ruff format careervp/
uv run ruff check --fix careervp/

# 3. Type check
uv run mypy careervp/ --strict

# 4. Build Lambda package
cd ../..
npx cdk synth

# 5. Verify CloudFormation
cat cdk.out/CVTailoringStack.json | jq '.Resources | keys'
```

### Deployment Commands

```bash
# Deploy to staging
cd infra
npx cdk deploy CVTailoringStack --environment staging

# Deploy to production (requires approval)
npx cdk deploy CVTailoringStack --environment production --require-approval never
```

---

## COMPLETION CHECKLIST

### Per-Task Checklist

After completing EACH task:

- [ ] Implementation complete
- [ ] All tests PASS (GREEN)
- [ ] `ruff format` passes
- [ ] `ruff check --fix` passes
- [ ] `mypy --strict` passes
- [ ] Code coverage ≥ required level
- [ ] Tests run with no warnings
- [ ] No TODOs or FIXMEs in code
- [ ] Docstrings complete
- [ ] Type hints complete

### Phase-Wide Checklist

Before claiming Phase 9 COMPLETE:

- [ ] Task 01-11 all completed
- [ ] All 165-205 tests PASS
- [ ] Code coverage ≥ 90% overall
- [ ] All code quality checks pass
- [ ] Infrastructure deployed
- [ ] E2E tests pass against deployed environment
- [ ] Architect verification obtained
- [ ] No open bugs or issues

---

## COMMON PITFALLS

### Pitfall 1: Skipping FVS Validation

**Problem:** Tailored CV returned without FVS validation
**Solution:** Always call `validate_cv_against_baseline()` before returning. CRITICAL violations must reject immediately.

**Test:** `test_fvs_rejects_modified_dates()` must PASS.

---

### Pitfall 2: Assuming Pydantic Model Exists

**Problem:** Using `TailoredCV` model before it's defined in Task 08
**Solution:** Define all models first (Task 08) before using in logic (Task 03).

**Dependency Order:** Task 08 must complete before Task 03 logic relies on it.

---

### Pitfall 3: Hardcoding LLM Model ID

**Problem:** Bedrock model ID hardcoded instead of using environment variable
**Solution:** Always read from `env_vars.BEDROCK_MODEL_ID` (set in Task 02).

**Code:** `bedrock_client.invoke_model(modelId=env_vars.BEDROCK_MODEL_ID, ...)`

---

### Pitfall 4: Missing Result[T] Wrapper

**Problem:** Logic functions returning plain values instead of Result[T]
**Solution:** Every logic function must return `Result[T]` with success/error/code.

**Pattern:**
```python
def my_function() -> Result[str]:
    if error:
        return Result(success=False, error="...", code=ResultCode.SOME_ERROR)
    return Result(success=True, data="...")
```

---

### Pitfall 5: Incomplete Error Handling in Handler

**Problem:** Handler doesn't map all error codes to HTTP status codes
**Solution:** Use `_get_status_code()` function to map result codes consistently.

**Coverage:** All ResultCode values must have HTTP status mapping.

---

### Pitfall 6: Type Hints Incomplete

**Problem:** Functions without type hints pass tests but fail `mypy --strict`
**Solution:** Add type hints to every parameter and return type BEFORE running tests.

**Command:** `mypy careervp/ --strict` must pass with 0 errors.

---

### Pitfall 7: Tests Not Run After Each Task

**Problem:** Code works in isolation but breaks when integrated
**Solution:** Run pytest IMMEDIATELY after completing each task (don't batch testing).

**Protocol:** Complete task → Run tests → Fix failures → Move to next task

---

### Pitfall 8: LLM Response Parsing Too Permissive

**Problem:** Invalid JSON from LLM crashes handler
**Solution:** Validate JSON structure before parsing. Use strict Pydantic validation.

**Code:**
```python
try:
    parsed = json.loads(llm_response)
    tailored_cv = TailoredCV(**parsed)  # Pydantic validates
except (json.JSONDecodeError, ValidationError) as e:
    return Result(success=False, error=f"Invalid LLM response: {e}",
                 code=ResultCode.LLM_PARSE_ERROR)
```

---

### Pitfall 9: Relevance Scores Not Normalized

**Problem:** Relevance scores exceed [0, 1] range
**Solution:** Clamp all scores to [0, 1] range using `min(max(score, 0.0), 1.0)`.

**Test:** All relevance scores in response must satisfy `0.0 <= score <= 1.0`.

---

### Pitfall 10: Prompt Contains Unformatted Variables

**Problem:** LLM prompt has `{{variable}}` placeholders not replaced
**Solution:** Use f-strings or .format() to replace ALL placeholders before sending to LLM.

**Pattern:**
```python
prompt = f"""
{job_description}
{immutable_dates}
"""
# NOT: prompt = "{{job_description}}" (won't be replaced)
```

---

## REFERENCE FILES SECTION

### Architecture & Design Documents

| File | Purpose | Read Before Task |
|------|---------|-----------------|
| `/docs/architecture/CV_TAILORING_DESIGN.md` | Complete system design with algorithms | Task 03 |
| `/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md` | API specification and response models | Task 08 |
| `/docs/tasks/09-cv-tailoring/README.md` | Task overview and dependencies | Task 01 |

### Existing Code Patterns

| File | Pattern | Reference For |
|------|---------|---------------|
| `src/backend/careervp/handlers/cv_upload_handler.py` | Handler structure | Task 06 |
| `src/backend/careervp/logic/fvs_validator.py` | FVS validation | Task 05 |
| `src/backend/careervp/dal/dynamo_dal_handler.py` | DAL pattern | Task 07 |
| `src/backend/careervp/models/cv.py` | Pydantic models | Task 08 |
| `src/backend/careervp/models/result.py` | Result[T] pattern | All tasks |

### Test Patterns

| File | Pattern | Reference For |
|------|---------|---------------|
| `tests/conftest.py` | Pytest fixtures | All tasks |
| `tests/cv-upload/unit/test_*.py` | Unit test pattern | Task 01-08 |
| `tests/cv-upload/integration/test_*.py` | Integration test pattern | Task 09 |
| `tests/cv-upload/e2e/test_*.py` | E2E test pattern | Task 10 |

### Environment & Configuration

| File | Purpose |
|------|---------|
| `src/backend/careervp/handlers/models/env_vars.py` | Environment variable models |
| `infra/careervp/constants.py` | Infrastructure constants |
| `infra/careervp/api_construct.py` | CDK construct definitions |

### Key Constants & Configs

```python
# From CLAUDE.md & CV_TAILORING_DESIGN.md
CV_TAILORING_LAMBDA_TIMEOUT = 60  # seconds
CV_TAILORING_LAMBDA_MEMORY = 512  # MB
BEDROCK_MODEL_ID = "claude-haiku-4-5-20251001"
TIMEOUT_SECONDS = 300  # For LLM calls
JOB_DESCRIPTION_MAX_LENGTH = 50000  # characters
JOB_DESCRIPTION_MIN_LENGTH = 50  # characters
RELEVANCE_SCORE_THRESHOLD_HIGH = 0.80
RELEVANCE_SCORE_THRESHOLD_MEDIUM = 0.60
RELEVANCE_SCORE_THRESHOLD_LOW = 0.40
```

---

## VERIFICATION TEMPLATES

### Post-Task Verification Template

After completing each task, run this verification suite:

```bash
# Navigate to backend
cd src/backend

# 1. Format check
echo "=== Running ruff format ==="
uv run ruff format careervp/path/to/file.py
if [ $? -ne 0 ]; then echo "FAILED: ruff format"; exit 1; fi

# 2. Lint check
echo "=== Running ruff check ==="
uv run ruff check --fix careervp/path/to/file.py
if [ $? -ne 0 ]; then echo "FAILED: ruff check"; exit 1; fi

# 3. Type check
echo "=== Running mypy --strict ==="
uv run mypy careervp/path/to/file.py --strict
if [ $? -ne 0 ]; then echo "FAILED: mypy"; exit 1; fi

# 4. Run task tests
echo "=== Running task tests ==="
uv run pytest tests/cv-tailoring/unit/test_task_file.py -v
if [ $? -ne 0 ]; then echo "FAILED: tests"; exit 1; fi

# 5. Coverage check
echo "=== Running coverage check ==="
uv run pytest tests/cv-tailoring/unit/test_task_file.py --cov=careervp --cov-report=term-missing
# Look for ≥90% coverage

echo "=== ALL CHECKS PASSED ==="
```

### Phase-Wide Verification Template

After all 11 tasks complete:

```bash
cd src/backend

# 1. Full test suite
uv run pytest tests/cv-tailoring/ -v --cov=careervp --cov-report=html
# Expected: 165-205 PASSED, ≥90% coverage

# 2. Format all
uv run ruff format careervp/

# 3. Lint all
uv run ruff check --fix careervp/

# 4. Type check all
uv run mypy careervp/ --strict

# 5. Infrastructure
cd ../..
npx cdk synth

echo "=== PHASE 9 READY FOR DEPLOYMENT ==="
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Next Review:** After implementation completion

---

## Quick Reference: Task Sequence

1. **Task 01** → Validation Utilities (1h)
2. **Task 08** → Pydantic Models (1h)
3. **Task 03** → Tailoring Logic (3h) *CORE - HIGH RISK*
4. **Task 04** → Tailoring Prompt (2h)
5. **Task 05** → FVS Integration (2h)
6. **Task 06** → Tailoring Handler (2h)
7. **Task 02** → Infrastructure (2h)
8. **Task 07** → DAL Extensions (1h) *OPTIONAL*
9. **Task 09** → Integration Tests (2h)
10. **Task 10** → E2E Verification (2h)
11. **Task 11** → Deployment (1h)

**Total:** 19 hours | **Critical Path:** 01 → 08 → 03 → 06 → 09 → 10 → 11
