# Active Sprint: Initial Infrastructure & CV Parser

## Phase 1: Environment Setup

- [x] Initialize `infra/` with CDK Python template.
- [x] Setup `src/backend/` with `uv` virtual environment.
- [x] Configure `CLAUDE.md` and `.clauderules` in project root.

## Phase 2: Foundation Models & Utilities (COMPLETED)

- [x] Create `src/backend/careervp/models/result.py` (Result object pattern).
- [x] Create `src/backend/careervp/logic/utils/llm_client.py` (Hybrid LLM Router).
- [x] Create `src/backend/careervp/models/cv.py` (Pydantic CV models).
- [x] Add `moto`, `anthropic`, `langdetect`, `python-docx`, `PyPDF2` to dependencies.

## Phase 3: Core Infrastructure

- [ ] Define `careervp-users` DynamoDB table.
- [ ] Define `careervp-job-search-assistant-cvs` S3 bucket with 7-day lifecycle.
- [ ] Deploy base stack to AWS.

## Phase 4: CV Parsing Implementation (IN PROGRESS)

- [ ] Implement `src/backend/careervp/logic/cv_parser.py`.
- [ ] Create `src/backend/careervp/handlers/cv_upload_handler.py`.
- [ ] Integrate language detection (Hebrew/English).

## Phase 5: Verification

- [ ] Write unit test for `cv_parser.py` using `moto` for S3/DynamoDB mocking.
- [ ] Write FVS validation tests using fixtures.
- [ ] Verify `cdk synth` success.
