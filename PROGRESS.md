# Project Progress: CareerVP

## Current Phase: VPR Generator Complete

## Wave 1 Security — Step 1.3c

- [x] P-11 WebACL rate rules implemented for dev, staging, and prod with API-stage association tests.
- [x] P-07 authorization-code + S256 PKCE frontend path, Cognito Plus threat protection, OPTIONAL TOTP grace state, self-service TOTP enrollment, scope inventory, and 401 retry oracle implemented and tested.
- [x] ~~P-07 final cutover blocked on human deploy + 30-day soak~~ **Corrected 2026-07-22: the soak never started.** The PKCE commit `4228346` is on `db-redesign` only, and Amplify never built that branch, so the SPA was never served and the 30-day clock has no start date. Split into 1.6 (below) and P-07b.
- [ ] **Step 1.6 (new, blocks 1.1):** delete the hardcoded dev-pool fallbacks in `src/frontend/lib/pkce.ts` + `auth.ts`, register devx Amplify callback URLs, deploy the PKCE SPA to a `db-redesign` Amplify branch pointed at devx, and capture one verified end-to-end login as evidence.
- [ ] **P-07b (deferred, blocks staging promotion — not 1.1):** move browser-side password-change and TOTP enrollment behind backend proxies, then remove implicit grant + `COGNITO_ADMIN` and enforce MFA.

## Wave 1 — Step 1.1 (P-04/P-05) — split into two sessions

- [ ] **1.1-RED:** write the five P-04/P-05 tests (none exist today) plus the checked-in route×handler matrix. Tests only; zero implementation files touched.
- [ ] **1.1-GREEN:** fresh session, may not edit the test files. Removes the `x-user-id` fallback (`auth_utils.py:44`) and the dead `AUTHORIZER_DISABLED` env (`api_construct.py:2106`), and enforces owner checks on every authenticated route.
- Blocked until 1.6 closes green. Rationale: `docs/db-redesign/code/code-analysis/project/runbooks/wave-1-status.md` §"Soak reinterpretation (2026-07-22)".

## Wave 1 — P-26 devx (CLOSED, live-verified 2026-07-20)

- [x] O-9 custom-domain prerequisite human-executed and live-verified on `CareerVpCrudDev`.
- [x] `CareerVpCrudDevx` domain-claim guard and AC-P26-9 RED→GREEN infrastructure test landed; devx synthesizes with zero shared `DomainName`/`BasePathMapping` resources.
- [x] Human executed the devx creation change set: `CareerVpCrudDevx` is `CREATE_COMPLETE`, **211 physical resources**, zero replacements.
- [x] P-30 four-wire smoke green against devx's raw invoke URL (4/4, after seeding `/careervp/devx/anthropic-api-key`) — `docs/evidence/smoke-20260720T203735Z-019ff0.json`.
- [ ] The shared-domain BasePathMapping flip and old-dev decommission remain separate, later human-only actions. **No decommission date is set** — until one is, "run it on dev" is ambiguous, since `api.dev.careervp.com` still points at the old stack.

## Wave 2 Money — Steps 2.0b–2.1 (P-25/P-25b/P-14/P-15)

- [x] `StripeProvider` implements the payment-provider port, real Stripe REST calls, multi-`v1` webhook signature rotation, tamper/wrong-secret rejection, and stale-timestamp replay rejection.
- [x] P-25b freeze-line tests pass without network calls; P-25 mock regressions, full backend unit/integration, coverage, Ruff, and strict mypy are green.
- [x] `MockProvider` accepts any matching `v1` and produces a stable digest event id when the verified payload has no provider id; B-2-1 and B-2-2 are settled true.
- [x] P-14 webhook and company-research worker replays are suppressed by primary-key conditional claims against the shared idempotency table; successful webhook results replay deterministically and failed work releases its claim.
- [x] P-15 customer lookup uses `customer-id-index`; `BillingLambda` has no Scan permission, while the separate reconciliation Lambda and `scan_active_subscriptions` remain intact for step 2.5.
- [x] Devx synth count is unchanged at 499 across parent and active nested templates; naming, CDK diff, full backend/CDK tests, coverage, Ruff, and strict mypy are green.

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
- [x] F-01/F-06 frontend contract oracle: Zod FE mirror, Pydantic JSON Schema artifacts, AJV dual-truth validation, MSW contract tests, and all 10 §3 assertions
- [x] WORKER-LEGS-001 artifact chain VPR task-token signaling and CV direct Lambda invoke (`infra/careervp/artifact_chain_construct.py`, `src/backend/careervp/handlers/vpr_worker_handler.py`, `src/backend/careervp/handlers/cv_tailoring_handler.py`)
- [x] FE-UI-049 Tavily company research retrieval, WEB_API identity-gated confidence, and enriched CompanyContext (`src/backend/careervp/logic/company_research.py`, `src/backend/careervp/logic/utils/tavily_client.py`)
- [x] FE-UI-050 cross-user company-intel split-TTL cache with profile/news records, normalized keys, best-effort DynamoDB degradation, and in-flight miss locking (`src/backend/careervp/logic/company_intel_cache.py`)

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
| `src/backend/careervp/logic/company_intel_cache.py`, `src/backend/careervp/logic/company_research.py`, `src/backend/careervp/logic/utils/web_search.py` | FE-UI-050 shared company-intel cache: split profile/news TTL records, domain-first cache keys, news-only refresh, cache miss writes, and in-flight lock |
| `src/backend/tests/unit/test_company_intel_cache.py` | FE-UI-050 unit coverage for key normalization, TTL read/write, cache-first flow, degradation, miss writes, and lock behavior |
| `src/frontend/lib/contractSchemas.ts`, `src/frontend/lib/contractOracle.ts`, `src/frontend/tests/contract/oracleFixtures.ts` | F-01/F-06 executable frontend contract oracle: Zod mirror, AJV/Pydantic schema validation, fixture corpus, and all 10 §3 assertions |
| `src/frontend/tests/unit/frontend-oracle.contract.test.ts`, `src/frontend/tests/integration/frontend-oracle-msw.contract.test.ts` | F-01/F-06 RED→GREEN oracle coverage, including MSW-backed API paths, `vpr_id:null` vs absent, stale `base_version` 409, and 401 retry-once sign-out |
| `src/backend/scripts/emit_json_schemas.py`, `src/backend/contract/schemas/*.json`, `src/backend/tests/unit/test_frontend_oracle_schema_emission.py` | Backend Pydantic `model_json_schema()` emission and committed-schema freshness check for the frontend oracle |
