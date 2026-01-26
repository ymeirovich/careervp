# Active Sprint: Initial Infrastructure & CV Parser

## Phase 1: Environment Setup (COMPLETED)

- [x] Initialize `infra/` with CDK Python template.
- [x] Setup `src/backend/` with `uv` virtual environment.
- [x] Configure `CLAUDE.md` and `.clauderules` in project root.

## Phase 2: Foundation Models & Utilities (COMPLETED)

- [x] Create `src/backend/careervp/models/result.py` (Result object pattern).
- [x] Create `src/backend/careervp/logic/utils/llm_client.py` (Hybrid LLM Router).
- [x] Create `src/backend/careervp/models/cv.py` (Pydantic CV models).
- [x] Add `moto`, `anthropic`, `langdetect`, `python-docx`, `PyPDF2` to dependencies.

## Phase 3: Core Infrastructure (COMPLETED)

- [x] Fix infrastructure constants (rename from Orders to CareerVP).
- [x] Define `careervp-users` DynamoDB table (Single Table Design with GSI).
- [x] Define CV S3 bucket with 7-day lifecycle + CORS.
- [ ] Deploy base stack to AWS.

## Phase 4: CV Parsing Implementation (COMPLETED)

- [x] Implement `src/backend/careervp/logic/cv_parser.py` with Haiku 4.5.
- [x] Implement `src/backend/careervp/logic/fvs_validator.py` for hallucination detection.
- [x] Integrate language detection (Hebrew/English with langdetect).
- [x] Create `src/backend/careervp/handlers/cv_upload_handler.py` (stub).

## Phase 5: Verification (COMPLETED)

- [x] Write FVS validation tests using fixtures (`test_fvs_validator.py`).
- [ ] Write integration test for `cv_parser.py` using `moto` for S3/DynamoDB mocking.
- [x] Remove orders placeholder code.
- [x] Verify `cdk synth` success.

## Phase 6: CV Upload Handler (COMPLETED)

- [x] Complete CV upload handler implementation.
- [x] Write moto-based unit tests for CV upload handler (11 tests).
- [x] Fix ruff linting (import sorting, unused imports).
- [ ] cv_parser.py tests: Dedicated unit tests for clean_text(), detect_language(), parse_llm_response() (deferred).

## Phase 7: VPR Generator (IN PROGRESS)

**Spec:** [[docs/specs/03-vpr-generator.md]]
**Tasks:** [[docs/tasks/03-vpr-generator/]]

- [ ] Task 1: Create JobPosting and VPR Pydantic models.
- [ ] Task 2: Add VPR DAL methods to DynamoDB handler.
- [ ] Task 3: Implement VPR generator logic with Sonnet 4.5.
- [ ] Task 4: Design Sonnet prompt with anti-AI patterns.
- [ ] Task 5: Create VPR Lambda handler.
- [ ] Task 6: Write moto-based unit tests.

## Phase 8: Future

- [ ] Implement CV Tailor (Haiku 4.5).
- [ ] Implement Cover Letter Generator (Haiku 4.5).
- [ ] Deploy base stack to AWS.
