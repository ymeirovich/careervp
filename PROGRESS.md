# Project Progress: CareerVP

## Current Phase: VPR Generator Complete

- [x] Folder Structure Initialization
- [x] Environment Configuration
- [x] Command Center Setup (`CLAUDE.md`, `.clauderules`)
- [x] Result Object Pattern (`models/result.py`)
- [x] LLM Router with Hybrid Strategy (`logic/utils/llm_client.py`)
- [x] CV Pydantic Models (`models/cv.py`)
- [x] Base Infrastructure (DynamoDB Tables, S3 Buckets)
- [x] CV Parsing Logic (Haiku 4.5) (`logic/cv_parser.py`)
- [x] FVS Validator (`logic/fvs_validator.py`)
- [x] FVS Unit Tests (`tests/unit/test_fvs_validator.py`)
- [x] Remove Orders placeholder code
- [x] CDK Synth verification
- [x] CV Upload Handler (stub created)
- [x] VPR Pydantic Models (`models/job.py`, `models/vpr.py`)
- [x] VPR DynamoDB DAL extensions (`dal/dynamo_dal_handler.py`)
- [x] VPR Prompt + Generator Logic (`logic/prompts/vpr_prompt.py`, `logic/vpr_generator.py`)
- [x] VPR Lambda Handler (`handlers/vpr_handler.py`)
- [x] VPR Unit & Integration Tests (`tests/unit/test_vpr_generator.py`, `tests/unit/test_vpr_handler.py`, `tests/unit/test_dynamo_dal_handler.py`)
- [x] CV Parser helper unit tests (`tests/unit/test_cv_parser.py`)
- [x] FE-UI-010 New Application full-page form replacement (`src/frontend/app/applications/new/page.tsx`)
- [x] FE-UI-015 TailoredCVsListTable new list table (`src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx`)
- [x] FE-UI-017 BaseCVsTable multi-CV list table (`src/frontend/components/BaseCVsTable/BaseCVsTable.tsx`)
- [x] FE-UI-016 CVCenterContent table listing replacement (`src/frontend/app/cv-center/page.tsx`)
- [x] FE-UI-020 RichTextEditor TipTap Markdown editor (`src/frontend/components/RichTextEditor/RichTextEditor.tsx`)
- [x] FE-UI-021 BillingContent page restructure (`src/frontend/app/billing/page.tsx`)
- [x] FE-UI-045 inline rich-text editing + autosave-on-blur for Cover Letter, Tailored CV, and Interview Prep (`src/frontend/hooks/useArtifactAutosave.ts`, `src/frontend/app/applications/[id]/cover-letter/page.tsx`, `src/frontend/app/applications/[id]/cv-tailored/page.tsx`, `src/frontend/app/applications/[id]/interview-prep/page.tsx`)
- [x] FE-UI-048 API Gateway per-feature `{proxy+}` collapse with protected/public authorizer parity, explicit mixed-handler exceptions, and parent-stack resource headroom (`infra/careervp/api_construct.py`)
- [x] WORKER-LEGS-001 artifact chain VPR task-token signaling and CV direct Lambda invoke (`infra/careervp/artifact_chain_construct.py`, `src/backend/careervp/handlers/vpr_worker_handler.py`, `src/backend/careervp/handlers/cv_tailoring_handler.py`)
- [x] FE-UI-049 Tavily company research retrieval, WEB_API identity-gated confidence, and enriched CompanyContext (`src/backend/careervp/logic/company_research.py`, `src/backend/careervp/logic/utils/tavily_client.py`)

## Upcoming Phases (From Context Manifest)

- [ ] VPR Generator (Sonnet 4.5)
- [ ] CV Tailoring Logic (Haiku 4.5)
- [ ] Cover Letter Engine
- [ ] Gap Analysis Engine
- [ ] Stripe Integration / Trial Logic

## Completed This Session

| File                                                 | Purpose                                      |
| ---------------------------------------------------- | -------------------------------------------- |
| `src/backend/careervp/models/result.py`              | Universal Result[T] pattern                  |
| `src/backend/careervp/logic/utils/llm_client.py`     | Hybrid LLM Router (Sonnet/Haiku)             |
| `src/backend/careervp/models/cv.py`                  | CV Pydantic models with FVS tiers            |
| `src/backend/careervp/logic/cv_parser.py`            | CV Parser with Haiku 4.5 + Hebrew RTL        |
| `src/backend/careervp/logic/fvs_validator.py`        | FVS hallucination detection                  |
| `src/backend/tests/unit/test_fvs_validator.py`       | FVS validation test suite                    |
| `infra/careervp/constants.py`                        | Fixed to CareerVP naming                     |
| `infra/careervp/api_db_construct.py`                 | Users table + S3 CV bucket                   |
| `src/backend/pyproject.toml`                         | Added moto, anthropic, langdetect            |
| `.env`                                       | Environment variable template                |
| `infra/careervp/api_construct.py`                    | Updated to CareerVP (CV upload endpoint)     |
| `src/backend/careervp/handlers/cv_upload_handler.py` | CV upload handler stub                       |
| `infra/careervp/service_stack.py`                    | Added S3 NAG suppression for dev             |
| `src/backend/tests/unit/test_cv_parser.py`           | Unit tests for clean_text/detect_language/LLM parsing |
| `src/frontend/canvas-app/App.jsx`                    | Change Base CV modal upload/choice behavior   |
| `src/frontend/tests/ui/unit/ChangeBaseCVModal.test.tsx` | Modal spec verification                      |
| `src/frontend/components/ui/ProgressBar.tsx`         | Added optional visible label row and preserved rounded ends |
| `tests/ui/unit/ProgressBar.test.tsx`                 | Unit coverage for label row, clamping, ARIA, and backward compatibility |
| `tests/ui/integration/ProgressBar.test.tsx`          | Integration coverage for provider-wrapped rendering |
| `tests/regression/ProgressBar.regression.test.tsx`   | Regression coverage for no-label equivalence and existing behavior |
| `src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx` | Shared base CV picker with choice and upload-only modes |
| `src/frontend/tests/ui/unit/ChooseBaseCVModal.test.tsx` | FE-UI-011 unit coverage for selection, upload, accessibility, Hebrew copy, and empty state |
| `src/frontend/app/applications/new/page.tsx`         | FE-UI-010 full-page New Application form with Base CV picker |
| `src/frontend/app/dashboard/page.tsx`                | Routes New Application CTA to `/applications/new` |
| `src/frontend/app/applications/page.tsx`             | Routes applications list CTA to `/applications/new` |
| `src/frontend/tests/ui/unit/NewApplicationPage.test.tsx` | FE-UI-010 unit coverage for navigation, form states, CV picker, POST `/jobs`, errors, and Hebrew copy |
| `frontend/app/applications/new/page.tsx`             | Legacy frontend route parity for `/applications/new` |
| `frontend/app/dashboard/page.tsx`                    | Legacy dashboard CTA routes to `/applications/new` |
| `src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx` | FE-UI-015 Tailored CVs list table (sort/search/states/i18n) |
| `src/frontend/tests/ui/unit/TailoredCVsListTable.test.tsx` | FE-UI-015 unit coverage for TailoredCVsListTable |
| `src/frontend/lib/types.ts`                          | Added Tailored CV list types |
| `src/frontend/components/BaseCVsTable/BaseCVsTable.tsx` | FE-UI-017 Base CVs list table with sorting, soft status badges, actions, states, responsive layout, and Hebrew copy |
| `src/frontend/components/BaseCVsTable/index.ts`      | Barrel export for BaseCVsTable |
| `src/frontend/tests/ui/unit/BaseCVsTable.test.tsx`   | FE-UI-017 unit coverage for BaseCVsTable |
| `src/frontend/app/cv-center/page.tsx`                 | FE-UI-016 Base CVs page listing with React Query GET `/users/me/cv`, upload-only modal, POST `/users/me/cv`, retry, and Hebrew copy |
| `src/frontend/tests/ui/unit/CVCenterContent.test.tsx` | FE-UI-016 unit coverage for page structure, data states, upload/refetch flow, removed old single-CV UI, ErrorBoundary, and Hebrew copy |
| `src/frontend/components/RichTextEditor/RichTextEditor.tsx` | FE-UI-020 TipTap rich text editor with toolbar, controlled Markdown output, read-only state, ARIA attributes, paste sanitization, and focus styling |
| `src/frontend/components/RichTextEditor/markdownSerializer.ts` | FE-UI-020 Markdown-to-HTML and HTML-to-Markdown serializer with underline and sanitized paste support |
| `src/frontend/tests/ui/unit/RichTextEditor.test.tsx` | FE-UI-020 unit coverage for initialization, toolbar actions, Markdown output, controlled value updates, read-only mode, paste sanitization, and accessibility |
| `src/frontend/app/billing/page.tsx`                  | FE-UI-021 Billing page with stacked subscription, usage, billing-info cards and anchored Plans section |
| `src/frontend/tests/ui/unit/BillingContent.test.tsx` | FE-UI-021 unit coverage for page assembly, loading state, CTA API wiring, anchor scroll, and Hebrew RTL copy |
| `src/frontend/hooks/useArtifactAutosave.ts`, `src/frontend/components/ArtifactAutosaveField.tsx`, `src/frontend/components/RestoreDraftBanner.tsx`, `src/frontend/components/ConflictModal.tsx` | FE-UI-045 shared autosave, draft-restore, and 409 conflict handling primitives for artifact editors |
| `src/frontend/app/applications/[id]/cover-letter/page.tsx`, `src/frontend/app/applications/[id]/cv-tailored/page.tsx`, `src/frontend/app/applications/[id]/interview-prep/page.tsx` | FE-UI-045 inline artifact editing parity: rich-text read rendering, autosave-on-blur, structured CV field persistence, and editable interview-prep answers |
| `src/frontend/tests/ui/unit/useArtifactAutosave.test.tsx`, `src/frontend/tests/ui/unit/ArtifactAutosaveField.test.tsx` | FE-UI-045 unit coverage for draft restore and autosave blur behavior |
| `src/backend/careervp/logic/prompts/company_research_prompt.py`, `src/backend/careervp/handlers/cover_letter_handler.py` | FE-UI-032 prompt externalization parity locked with golden tests and persisted company research now flows into cover-letter prompt generation |
| `infra/careervp/artifact_chain_construct.py`, `infra/careervp/api_construct.py`, `infra/careervp/api_db_construct.py` | WORKER-LEGS-001 chain wiring: VPR task token without short heartbeat, CV direct Lambda invoke, and removal of unused CV tailoring queue/DLQ |
| `src/backend/careervp/handlers/vpr_worker_handler.py`, `src/backend/careervp/handlers/cv_tailoring_handler.py`, `src/backend/careervp/handlers/company_research_worker_handler.py`, `src/backend/careervp/handlers/gap_handler.py` | WORKER-LEGS-001 handler support for VPR task-token callbacks, CV SFN invoke entrypoint, CR output threading, and chain `cv_id` input |
| `src/backend/tests/unit/test_vpr_worker_task_token.py`, `src/backend/tests/unit/test_cv_tailoring_sfn_entrypoint.py`, `infra/tests/infrastructure/test_vpr_leg_wiring.py`, `infra/tests/infrastructure/test_cv_leg_wiring.py` | WORKER-LEGS-001 unit and infrastructure regression coverage |
| `infra/careervp/api_construct.py`, `infra/tests/infrastructure/test_apigw_proxy_collapse.py`, `infra/tests/infrastructure/test_api_construct.py`, `infra/tests/infrastructure/test_nested_split.py` | FE-UI-048 proxy-collapse implementation and regression coverage; parent synth reduced below the 400-resource gate while preserving the shared RestApi |
| `src/backend/careervp/logic/company_research.py`, `src/backend/careervp/logic/utils/tavily_client.py`, `src/backend/careervp/logic/utils/web_search.py`, `src/backend/careervp/models/company.py`, `src/backend/careervp/models/job.py` | FE-UI-049 Tavily-backed company research, WEB_API confidence identity gate, 2500-word prompt budget, and enriched CompanyContext |
| `src/backend/tests/unit/test_tavily_client.py`, `src/backend/tests/unit/test_web_search.py`, `src/backend/tests/unit/test_company_research.py`, `src/backend/tests/unit/test_vpr_company_research_binding.py` | FE-UI-049 regression coverage for Tavily key resolution, two-query retrieval, confidence gate, no-fabrication failure, and downstream context enrichment |
