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

## Phase 6: Next Steps

- [ ] Complete CV upload handler implementation.
- [ ] Implement VPR Generator (Sonnet 4.5).
- [ ] Implement CV Tailor (Haiku 4.5).
