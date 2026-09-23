# F-DEVX findings — Codex validation and implementation handoff for Claude Code

**Date:** 2026-08-01  
**Branch inspected:** `db-redesign`  
**Inspected commit:** `748af77`  
**Source handoff:** `docs/db-redesign/code/code-analysis/redesign/prompts/F-DEVX-findings-codex-validation-handoff.md` (inspected before it was relocated from `project/specs/amendments/`)  
**Purpose:** give Claude Code a self-contained, evidence-backed guide for correcting the validated F-DEVX failures without preserving the legacy storage split or violating Wave-3 ownership rules.

---

## 1. Executive result

The primary diagnosis is confirmed. Cover-letter and interview-prep submissions cannot resolve a completed VPR because the VPR worker writes the VPR to the legacy users table using `pk`/`sk`, while both submit handlers instantiate a DAL for the canonical artifacts table and then execute that same legacy `pk`/`sk` VPR query against a table keyed by `applicationId`/`artifactId`.

The live failure is not hypothetical. CloudWatch contains this exact DynamoDB error for both devx submit Lambdas:

```text
botocore.exceptions.ClientError: An error occurred (ValidationException)
when calling the Query operation:
Query condition missed key schema element: applicationId
```

The current flow is:

```text
VPR worker
  DYNAMODB_TABLE_NAME=careervp-users-table-devx
  generate_vpr(..., cv_dal)
    -> cv_dal.save_vpr(...)
    -> put {pk: application_id, sk: ARTIFACT#VPR#v1, ...}

Cover-letter / interview-prep submit
  ARTIFACTS_TABLE_NAME=careervp-artifacts-table-devx
  resolve_handler_dependencies(..., DynamoDalHandler(artifacts_table))
    -> get_vpr(application_id)
    -> Query Key('pk') / Key('sk') against applicationId/artifactId table
    -> ValidationException
    -> failed Result is converted to None
    -> resolver reports missing VPR
    -> HTTP 409 upstream_required
```

This is a launch blocker. The same validation also found three additional high-severity problems:

1. `interview_prep_submit_handler` logs the complete API Gateway event, including the bearer ID token.
2. The devx gap Lambda constructs `SubscriptionRepository()` without a table name; it falls back to the **dev** users table and treats the resulting `AccessDeniedException` as if no subscription exists.
3. The jobs-backed `CoreRepository` path does not materialize the VPR. Deployed VPR jobs have `result_key`/`result_url`, not an inline `result`, so the repository returns only an ID/application/user stub. Simply routing submit handlers through that adapter would make the 409 disappear while downstream prompts receive no real VPR content.

Do not implement a narrow table-pointer change. The correct repair must establish one canonical VPR identity, one canonical artifact record, and a repository read that returns the full owned VPR payload.

---

## 2. Mandatory context and guardrails

Before editing, read these files in full:

1. `AGENTS.md`
2. `.clauderules`
3. `docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md`
4. `docs/db-redesign/code/code-analysis/project/project-scope-lock.md` and its v2.7.0 amendment/decision source
5. `docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md`
6. `docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md`
7. `docs/db-redesign/code/code-analysis/project/specs/amendments/D-H2-harness-removal-amendment.md`
8. `docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md`

Non-negotiable constraints:

- Scope-lock v2.7.0 says all stored data is disposable test data. There is no migration, backfill, dual-read window, compatibility reader, or cutover. Legacy records are deleted and rewritten.
- `infra/` is owned by step 3.4. Do not modify it from a different task without an explicit ownership decision.
- `src/backend/tests/unit/test_dh4_p01_canonical_artifact.py` is a pinned RED test. Do not edit or weaken it.
- DAL internal key construction has ownership implications in later Wave-3 work. If the corrective slice needs those files, record the cross-owner decision rather than hiding the expansion.
- Do not point cover-letter/interview-prep back to the users table as a workaround.
- Do not convert `ValidationException` to “not found” or “upstream missing.”
- Do not use the current jobs-table ID stub as if it were a complete VPR.
- Do not persist a presigned URL as the durable artifact locator. Persist the S3 bucket/key or another stable locator and generate signed URLs only when needed.
- Do not invent `"Unknown"` for an immutable employer or role fact.
- Do not deploy until `make deploy-devx` preserves the deployed P-26 nested-stack topology.
- Do not update `PROGRESS.md` or `plan.md` until code and all required tests are green.

The worktree was already dirty before this validation. Preserve these user-owned changes:

```text
docs/beta/evidence/I1_generators/generator-output-audit.json
docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json
docs/beta/evidence/I3_auth/auth-abuse-matrix.json
docs/db-redesign/code/code-analysis/project/runbooks/wave-3-prompts.md
```

---

## 3. Live AWS facts independently verified

### 3.1 Account and stacks

- AWS account inspected: `788159322332`
- Region: `us-east-1`
- `CareerVpCrudDevx`: `UPDATE_COMPLETE`
- `CareerVpCrudDev`: `UPDATE_COMPLETE`
- `CareerVpCrudStaging`: `UPDATE_COMPLETE`
- No production stack or production resources exist in this account.

### 3.2 Relevant key schemas

The schemas are consistent across devx, dev, and staging:

| Table family | Key schema |
|---|---|
| users | `pk` / `sk` |
| artifacts | `applicationId` / `artifactId` |
| cvs | `userId` / `cvId` |
| jobs | `job_id` |
| applications | `userId` / `applicationId` |

### 3.3 VPR record counts

| Environment | VPRs in legacy users table | VPRs in canonical artifacts table | VPR jobs with application identity |
|---|---:|---:|---:|
| devx | 4 | 0 | 4 |
| dev | 83 | 0 | 8 |
| staging | 2 | 0 | 0 |

This establishes that the artifacts table is not merely missing one test record. No canonical VPR writes are occurring in any inspected environment.

### 3.4 Environment-variable split

The VPR workers receive both table names, but the code uses the legacy variable for VPR persistence:

```text
careervp-vpr-worker-lambda-{env}
careervp-vpr-sqs-worker-lambda-{env}

ARTIFACTS_TABLE_NAME = careervp-artifacts-table-{env}
DYNAMODB_TABLE_NAME  = careervp-users-table-{env}
```

Cover-letter and interview-prep submit Lambdas resolve the artifacts table:

```text
ARTIFACTS_TABLE_NAME = careervp-artifacts-table-{env}
DYNAMODB_TABLE_NAME  = careervp-artifacts-table-{env}
```

CV tailoring is the exception because its handler explicitly calls the legacy table-name resolver. Its success is evidence of divergent routing, not evidence that canonical VPR storage works.

---

## 4. Finding F-DEVX-1 — canonical VPR persistence and downstream resolution

### 4.1 Exact code path: legacy write

Relevant locations:

- `src/backend/careervp/handlers/vpr_worker_handler.py:400`
  - obtains `DYNAMODB_TABLE_NAME`
  - creates `cv_dal = DynamoDalHandler(cv_table)`
- `src/backend/careervp/handlers/vpr_worker_handler.py:438-440`
  - calls `cv_dal.get_next_vpr_version(...)`
  - passes the same `cv_dal` to `generate_vpr(...)`
- `src/backend/careervp/logic/vpr_generator.py:425-445`
  - generation also persists through the supplied DAL
- `src/backend/careervp/dal/dynamo_dal_handler.py:296-317`
  - `save_vpr` writes `pk` and `sk`
- `src/backend/careervp/dal/dynamo_dal_handler.py:320-386`
  - `get_vpr`/`get_latest_vpr` read `pk` and `sk`

The structural bug is that one generic DAL instance represents at least two different storage domains: CV data and generated VPR artifacts. The presence of `ARTIFACTS_TABLE_NAME` does nothing because this path never constructs a canonical artifacts repository for the output.

### 4.2 Exact code path: canonical-table read with legacy grammar

Relevant locations:

- `src/backend/careervp/dal/table_registry.py:124-125`
  - full artifacts chain: `ARTIFACTS_TABLE_NAME`, `DYNAMODB_TABLE_NAME`, `TABLE_NAME`
  - legacy chain: `DYNAMODB_TABLE_NAME`, `TABLE_NAME`
- `src/backend/careervp/handlers/cover_letter_submit_handler.py:73,258-262`
  - resolves the artifacts table and passes `DynamoDalHandler(table_name)` to the dependency resolver
- `src/backend/careervp/handlers/interview_prep_submit_handler.py:73,140-144`
  - same behavior
- `src/backend/careervp/handlers/artifact_dependency_utils.py:40-46`
  - calls `self._dal.get_vpr(application_id=...)`
  - returns data only when `result.success` is true; otherwise returns `None`

The original handoff said an exception was swallowed by `except Exception`. The observed mechanism is slightly different and must be fixed at the correct layer:

1. `get_latest_vpr` catches `ClientError`.
2. It logs the exception.
3. It returns a failed `Result` with `DYNAMODB_ERROR`.
4. `DynamoArtifactDependencyRepos.get_artifact` converts that failed result to `None`.
5. The resolver short-circuits on `candidate is None`.
6. `_is_owned_by` and `_is_stale` are not reached.

This means the corrective work must preserve error classification across the Handler -> Logic -> DAL boundary. A schema failure is not a missing dependency.

### 4.3 Canonical invariant to implement

After the repair, a completed VPR journey must satisfy all of these:

1. The opaque VPR `artifact_id` is created once. The existing job ID is a reasonable candidate because the hub already stores it, but record that decision explicitly.
2. The artifacts table contains a VPR record at exactly:

   ```python
   {
       'applicationId': application_id,
       'artifactId': artifact_id,
   }
   ```

3. The record exposes the canonical artifact type required by the table's `type-index`, and an owner field understood by `CoreRepository`.
4. The record contains either:
   - the complete, bounded VPR payload; or
   - a stable S3 bucket/key plus enough metadata for an owned repository read to hydrate and validate the full payload.
5. `ApplicationRepository` stores that same opaque ID in `artifact_statuses.vpr_artifact_id`.
6. `CoreRepository.resolve_artifact_id(application_id, 'vpr', user_id=...)` returns that ID.
7. `CoreRepository.get_vpr_by_artifact_id(...)` returns the actual VPR payload, not an ID-only dictionary.
8. Cover-letter, interview-prep, and CV-tailoring use the same repository authority.
9. A wrong owner returns `FORBIDDEN`; a missing artifact returns successful `None`; a key-schema failure returns `TABLE_SCHEMA_MISMATCH` or another explicit infrastructure code.
10. The worker does not mark the job/hub completed until the canonical artifact write succeeds.

Example metadata shape, subject to the payload-location decision:

```json
{
  "applicationId": "application-uuid",
  "artifactId": "opaque-vpr-artifact-uuid",
  "artifactType": "vpr",
  "userId": "cognito-sub",
  "version": 1,
  "status": "completed",
  "resultKey": "results/opaque-vpr-artifact-uuid.json",
  "createdAt": "2026-08-01T09:55:00Z",
  "updatedAt": "2026-08-01T09:55:00Z"
}
```

Do not copy this mechanically if the authoritative spec defines different field casing. The invariant is one key grammar and one opaque ID, not the incidental casing in this example.

### 4.4 The jobs-repository trap

`src/backend/careervp/dal/core_repository.py:173-200` contains `_get_vpr_job`:

```python
payload = job.get('result')
resolved = dict(payload) if isinstance(payload, dict) else {}
resolved.setdefault('artifact_id', artifact_id)
resolved.setdefault('application_id', ...)
resolved.setdefault('user_id', ...)
```

Deployed completed VPR jobs contain `result_key` and `result_url`, but no inline `result`. Therefore this method returns roughly:

```python
{
    'artifact_id': artifact_id,
    'application_id': application_id,
    'user_id': user_id,
    'language': language_if_present,
}
```

Cover-letter and interview-prep worker code sees a non-empty dictionary and does not necessarily fall back to the real VPR. A submit-only fix would therefore trade a visible 409 for silently degraded generated content.

Required regression test:

```text
Given a completed VPR job with result_key but no inline result
And a canonical VPR artifact owned by the application user
When cover-letter or interview-prep materializes context
Then the prompt input contains actual VPR sections/differentiators
And not merely artifact_id/application_id/user_id
```

### 4.5 Required tests for this finding

Add tests without changing the pinned D-H4 file:

- Worker writes a canonical VPR item into a moto artifacts table with the real `applicationId`/`artifactId` schema.
- Worker does not write a VPR-shaped item to the users table.
- Worker completion fails/retries if the canonical artifact write fails.
- Application hub and canonical artifact use the same opaque ID.
- Cover-letter submit returns 202 for an owned completed canonical VPR.
- Interview-prep submit returns 202 for an owned completed canonical VPR.
- Wrong-owner VPR returns the public forbidden envelope.
- A DynamoDB `ValidationException` is not converted to a 409/missing dependency.
- Cover-letter worker receives full VPR content.
- Interview-prep worker receives full VPR content.
- CV-tailoring resolves the same canonical VPR rather than the users-table copy.
- The repository never treats `result_url` as the durable data locator.

At least one test must use moto with the actual table key schema and real repository calls. Mocking `resolve_handler_dependencies` to return ready is insufficient.

---

## 5. Finding F-DEVX-2 — live suites use the wrong token

Validated locations:

- `src/backend/tests/integration/integration_helpers.py:146,154`
- `src/backend/tests/e2e/e2e_helpers.py:110,118`

Both helpers select `access_token` from register/login responses. The API authorizer accepts the ID token for these routes. The real frontend is correct:

- `src/frontend/lib/auth.ts:84-94` calls `session.getIdToken().getJwtToken()`
- `src/frontend/api/client.ts:68-74` sends it as `Authorization: Bearer ...`

The specified live suite was run unchanged and produced:

```text
8 failed, 4 passed, 12 skipped
```

Authenticated requests failed at the first application wire with 401. This prevented paid AI calls.

Required test-harness changes:

1. Return and use `id_token` for product API requests.
2. Keep `access_token` only where an OAuth/Cognito endpoint specifically requires it.
3. Add a token-use regression test that decodes claims without logging token values and asserts `token_use == 'id'` for the API client credential.
4. Never include the token value in assertion messages, captured logs, or generated evidence.

---

## 6. Findings F-DEVX-3/F-DEVX-4 — stale and misleading live contracts

The handoff was only partially correct here.

### 6.1 What is stale

The frontend polls these routes:

```text
/vpr/{id}/status
/cv-tailoring/{id}/status
/cover-letter/{id}/status
/interview-prep/{id}/status
```

See `src/frontend/api/methods.ts:165-269`.

Several backend live tests poll the bare `/{id}` variants. Those routes do not exist. API Gateway can return `403 DEFAULT_4XX` for an unrouted method, which is not evidence of authentication failure.

Company research tests that send only `{'domain': 'example.com'}` are stale. The active handler imports `careervp.models.company.CompanyResearchRequest`, where `company_name` is required, and separately obtains `job_id` from the raw payload. The frontend correctly sends:

```json
{
  "job_id": "application-id",
  "company_name": "Example Corp",
  "url": "https://example.com/jobs/123"
}
```

### 6.2 What the original handoff overstated

`POST /users/me/cv` does **not** exclusively require `{cv_content, file_name}`. `cv_upload_handler._normalize_request_payload` explicitly supports both:

```text
Legacy:  file_content|text_content, file_type
OpenAPI: cv_content, file_name, optional file_type
```

Also, `job_handler._parse_create_job_request` accepts `company` as an alias for `company_name`. One E2E job variant is therefore compatible, while the integration variants remain stale in other fields.

### 6.3 Correct test posture

Even when compatibility paths exist, live contract tests should use the same canonical shapes as the frontend. Otherwise they only prove that transitional aliases still work.

Replace broad expected-status sets such as `{200, 401, 404}` with assertions that distinguish:

- authenticated happy-path status;
- explicit validation failure;
- explicit not-found;
- explicit unauthorized negative test;
- unrouted API Gateway response, which should fail the contract gate.

`test_e2e_contract_gate_validation.py` is not a reliable contract gate while 401 is accepted for authenticated cases and stale routes are permitted.

---

## 7. Finding F-DEVX-5 — gap analysis crosses the API Gateway deadline

Deployed configuration:

```text
POST /gap-analysis/questions integration timeout: 29,000 ms
careervp-gap-api-lambda-{env} timeout:             30 seconds
```

Live durations included 200 responses near 28 seconds and repeated 504 responses after roughly 29.2 seconds. CloudWatch also showed a successful Lambda invocation with `durationMs=29853.32`, proving that work can finish and persist after API Gateway has already returned 504 to the client.

This creates more than a latency problem:

1. Trial usage is checked/consumed before the LLM call.
2. The Lambda may persist questions after the client receives 504.
3. The frontend sees no question IDs and may continue with an empty list.
4. The later VPR request reports `gap_response_ids must not be empty`, obscuring the actual upstream timeout.
5. A user retry can repeat work and may affect trial attribution unless idempotency is explicit.

Recommended repair: make question generation asynchronous.

```text
POST questions -> 202 {request_id/status}
GET status/questions -> pending|completed|failed plus questions
```

Requirements:

- The operation must be idempotent per user/application/request identity.
- Trial charging must be exactly once under retries and worker redelivery.
- A failed generation must surface on the question-generation resource, not as a validation error on VPR.
- The frontend must not advance until completed questions are retrieved.
- Do not “fix” this by increasing only the Lambda timeout.
- Do not start background work in a Lambda process after returning; use the existing queue/Step Functions architecture or another durable async mechanism.

This is a public contract change and needs a human decision before implementation.

---

## 8. Finding F-DEVX-6 — extractor nulls become internal errors

`WorkExperience.company` and `WorkExperience.role` are required immutable strings:

- `src/backend/careervp/models/cv.py:60-71`

The parser currently uses:

```python
company=exp.get('company', 'Unknown')
role=exp.get('role', 'Unknown')
```

`dict.get(key, default)` returns `None` when the key exists with a null value, so the default does not apply. CloudWatch recorded the exact Pydantic failure for `company=None`. `parse_cv` catches it as a generic exception, returns `ResultCode.INTERNAL_ERROR`, and `cv_upload_handler` maps that to HTTP 500.

The same defect family can affect other required extractor fields such as role, education institution, and degree when the LLM returns explicit nulls.

Do not fix this with `exp.get('company') or 'Unknown'`: company and role are immutable facts, and inventing a placeholder violates the repository's fact-verification rules.

Choose one product policy:

1. **Recommended launch-safe policy:** return a structured 422 requiring correction when a required immutable fact is absent. Preserve the raw extraction diagnostics internally without exposing a stack trace.
2. Make selected immutable fields optional throughout every downstream model, prompt builder, validator, sorter, exporter, and `.lower()` call. This is broader and needs a complete impact audit.
3. Represent employer-less work using a separate explicit classification supported by the model and UI. Do not infer it from null without evidence.

Required mocked-LLM tests:

- `company: null` never returns 500.
- `role: null` never returns 500.
- missing company and explicit null are handled according to the same documented policy.
- no fabricated employer appears in the stored CV.
- downstream validation receives either a valid typed record or a structured correctable error.

---

## 9. Finding F-DEVX-7 — `make deploy-devx` synthesizes the wrong topology

The target at `src/backend/Makefile:125-127` omits:

```text
--context p26_rehome_features=true
```

The context is consumed at `infra/careervp/api_construct.py:92-97`. It is absent from `infra/cdk.json`, and the CDK invocation runs from `src/backend`, where there is no local `cdk.json` supplying it.

Independent synth comparison:

| Synth | Parent resources | Parent log groups | CrudFeatures nested log groups |
|---|---:|---:|---:|
| Without flag | 491 | 32 | 0 |
| With flag | 261 | 2 | 30 |
| Deployed devx parent | 261 | 2 | nested stack present |

The deployed topology matches the flagged synth. The unflagged target attempts to move resources back into the parent and approaches the 500-resource limit. It is not safe to deploy.

Required correction, owned by 3.4 unless reassigned:

```make
npx cdk deploy ... \
  --context "allowed_origins=$(_CDK_ALLOWED_ORIGINS)" \
  --context p26_rehome_features=true
```

Add a non-deploying regression check that fails unless the devx synth has the expected nested resource placement. Do not rely only on matching a command string.

Governance question: `.github/workflows/db-redesign-checks.yml` executes `make deploy-devx`, while the Makefile's P-28 comment says automation should create a change set without executing it. Confirm whether devx is an intentional exception. Do not silently resolve that policy conflict while fixing the context flag.

After any `infra/` edit, the mandatory naming validators are:

```bash
python src/backend/scripts/validate_naming.py --path infra --verbose
python src/backend/scripts/validate_naming.py --path infra --strict
```

No deployment was performed during Codex validation; the exact CloudFormation collision count was not reproduced destructively.

---

## 10. Additional launch-blocking issue — bearer token logged to CloudWatch

`src/backend/careervp/handlers/interview_prep_submit_handler.py:100-105` contains:

```python
logger.info(
    'Interview prep submit request received',
    api_gateway_event=event,
    endpoint=endpoint,
    request_id=_get_request_id(event, context),
)
```

Although the Powertools decorator uses `log_event=False`, this explicit field logs the whole event, including `headers.Authorization`, request body, identity/network metadata, and authorizer claims. A live bearer ID token was observed in the log. Never copy that token into issues, tests, evidence, or commits.

Required correction:

- Remove `api_gateway_event=event`.
- Log only allow-listed scalar metadata such as endpoint and request ID.
- If body observability is required, log only field names or a pre-redacted structure.
- Add a unit test with a sentinel token and sensitive body field and assert neither appears in captured log calls/output.
- Search all handlers for other whole-event logging before closing the issue.
- Assess CloudWatch access and remaining token validity. Current retention is one day, but retention is not a substitute for redaction.

Treat this as a security hotfix, but coordinate deployment with F-DEVX-7 so the fix is not delivered through the broken CDK topology.

---

## 11. Additional isolation issue — devx quota lookup addresses dev

Relevant code:

- `src/backend/careervp/dal/subscription_repository.py:70-80`
- `src/backend/careervp/handlers/gap_handler.py:896-904`
- `src/backend/careervp/logic/quota_service.py:49-72`

`SubscriptionRepository` resolves its users table from `TABLE_NAME` and then a `NamingUtils` fallback. The devx gap Lambda provides `USERS_TABLE_NAME=careervp-users-table-devx` but does not provide `TABLE_NAME`. With no explicit environment available to the fallback, the repository addresses `careervp-users-table-dev`.

Live devx log:

```text
AccessDeniedException ... is not authorized to perform dynamodb:GetItem on
arn:aws:dynamodb:us-east-1:788159322332:table/careervp-users-table-dev
```

`QuotaService` treats a failed subscription lookup as `sub=None` and proceeds to trial enforcement. Consequences include paid users being treated as trial users and cross-environment isolation depending accidentally on IAM denial.

Recommended correction:

- Explicitly inject the environment's `USERS_TABLE_NAME` into `SubscriptionRepository` from the handler/composition root.
- Prefer explicit dependency injection over another broad fallback chain.
- Distinguish “no subscription row” from “subscription lookup failed.” A DynamoDB failure should surface as an infrastructure/service-unavailable result, not silently become trial mode.
- Add tests for dev, devx, and staging names proving no repository addresses another environment.
- Add a paid-user test showing a repository error cannot consume trial credit or block an active subscriber as expired trial.

This area is likely owned by the Wave-6 auth/trial slice. Pull it forward only with an explicit ownership record or report it as a launch blocker to that owner.

---

## 12. Ordered implementation plan

### Step 1 — restore a safe delivery path

Owner: 3.4/infra.  
Size: XS.

- Add the P-26 context to `deploy-devx`.
- Add topology regression coverage.
- Resolve whether direct CI deploy is an authorized devx exception to P-28.
- Run both naming validators and relevant infrastructure tests.
- Do not deploy yet.

### Step 2 — remove live credential logging

Owner: backend/security or D-H4 corrective owner.  
Size: XS.

- Remove full-event logging.
- Add sentinel-secret log tests.
- Audit sibling submit handlers for the same pattern.

### Step 3 — fix subscription environment isolation

Owner: trial/billing/Wave-6, explicitly pulled forward if needed.  
Size: S.

- Inject the correct users table.
- Make subscription lookup errors distinct from absent subscriptions.
- Add environment-isolation and paid-user failure tests.

### Step 4 — land RED tests for the real VPR schema

Owner: D-H2/D-H4 corrective slice.  
Size: M.

- Use moto with actual users, artifacts, jobs, applications, and where necessary S3 schemas.
- Exercise the real worker persistence and submit resolution paths.
- Prove full VPR materialization.
- Do not edit the pinned D-H4 test.

### Step 5 — implement canonical VPR persistence

Owner: D-H2/D-H4 plus the owner of DAL key demolition if those internals change.  
Size: M/L.

- Separate CV reads from artifact writes.
- Persist canonical VPR metadata/payload before marking completion.
- Make the hub, jobs status, and canonical artifact share one ID.
- Remove the legacy VPR write; do not dual-write.

### Step 6 — make all downstream consumers use the canonical repository

Owner: D-H4 corrective slice.  
Size: M.

- Cover letter, interview prep, and CV tailoring resolve through `CoreRepository`.
- Ensure workers receive the full VPR.
- Preserve ownership and staleness checks.
- Propagate schema/infrastructure errors rather than returning 409.

### Step 7 — delete and recreate disposable legacy records

Owner: environment/data owner; human-gated destructive operation.  
Size: S operationally.

- Delete legacy VPR test records only after the canonical code is ready.
- Re-run fresh journeys in devx, then dev/staging as authorized.
- Do not migrate or backfill.

### Step 8 — repair live test contracts

Owner: backend QA.  
Size: M.

- Use ID tokens.
- Use frontend/canonical payloads.
- Poll `/status` routes.
- Assert exact outcomes.
- Separate contract tests from paid full-journey tests.

### Step 9 — make gap questions durable and asynchronous

Owner: API/product decision plus gap-analysis owner.  
Size: L.

- Decide the 202/poll contract.
- Implement durable state, idempotency, and exact-once trial attribution.
- Update the frontend flow and tests.

### Step 10 — implement the immutable-null parser policy

Owner: CV parser/product.  
Size: S for structured 422; M or larger for optional immutable fields.

- Decide the policy.
- Generalize beyond company to all required extractor fields.
- Add mocked-LLM regression tests.

---

## 13. Validation commands and observed baseline

### Already run by Codex

```bash
cd src/backend
uv run pytest \
  tests/unit/test_table_registry_characterization.py \
  tests/unit/test_artifact_dependency_resolver.py \
  tests/unit/test_artifact_dependency_utils.py \
  tests/unit/test_dh4_p01_canonical_artifact.py \
  tests/unit/test_cv_parser.py \
  -q --tb=short
```

Result:

```text
28 passed
```

```bash
cd src/backend
uv run pytest ../../infra/tests/infrastructure/test_nested_split.py -q --tb=short
```

Result:

```text
13 passed
```

The green result does **not** clear F-DEVX-1; it demonstrates the coverage hole because no test executes the real VPR worker write against the artifacts-table schema and then passes that record through both submit handlers.

The handoff's live suite was also run:

```bash
cd src/backend
API_BASE=https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/ \
  uv run pytest tests/integration/test_full_pipeline_integration.py tests/e2e/ -v --tb=short
```

Result:

```text
8 failed, 4 passed, 12 skipped
```

This self-registered disposable devx users. Because the tests used access tokens, they stopped at authentication before paid AI calls.

### Required checks after implementation

For every changed Python file, immediately run:

```bash
cd src/backend
uv run mypy <changed-file> --strict
uv run ruff format <changed-file>
uv run ruff check <changed-file> --fix
```

Then run the relevant unit/integration tests, followed by the mandatory repository cleanup checks:

```bash
cd src/backend
uv run ruff format .
uv run ruff check --fix .
uv run pytest tests/ -v --tb=short
```

If frontend files change, run from `src/frontend`:

```bash
npm run typecheck
npm run test:unit
npm run test:integration
npm run test:e2e
npm run test:regression
```

Run the Vitest command required by `AGENTS.md` if any Vitest-covered file changes.

Do not run a paid full-journey probe without explicit authorization and an agreed budget. Source-level, moto, and mocked-provider tests must prove the contract first.

---

## 14. Done criteria

This corrective work is not complete until all of the following are true:

- A fresh VPR journey writes a canonical VPR artifact and no legacy users-table VPR.
- The hub's VPR artifact ID resolves to that exact canonical record.
- Cover-letter submit returns 202 for the owned VPR and its worker receives actual VPR content.
- Interview-prep submit returns 202 for the owned VPR and its worker receives actual VPR content.
- CV-tailoring resolves through the same canonical authority.
- Wrong-owner access remains forbidden.
- DynamoDB schema failures surface explicitly and never become 409/missing.
- No handler logs authorization tokens or complete API Gateway events.
- Devx never addresses a dev/staging table; equivalent isolation holds for every environment.
- Live test helpers use ID tokens and current routes.
- The devx synth matches the deployed P-26 nested topology.
- Gap generation no longer returns a client timeout after work/charging succeeds invisibly.
- Extractor nulls never produce HTTP 500 or fabricated immutable facts.
- Mandatory Ruff, mypy, backend, frontend, infra, and naming checks are green as applicable.
- No assertion was weakened and the pinned D-H4 test remains untouched.
- `PROGRESS.md` and `plan.md` are updated only after the implementation and tests land.

---

## 15. Human decisions still required

Claude Code must not guess these:

1. **Ownership:** reopen D-H4/3.2 for F-DEVX-1, or create a corrective slice spanning D-H2/D-H4 and the later DAL owner?
2. **Canonical VPR representation:** bounded full payload in DynamoDB, or canonical metadata with stable S3 key and repository hydration?
3. **Gap API contract:** authorize synchronous 200 -> asynchronous 202/poll?
4. **Immutable-null policy:** structured 422, optional fields with a full downstream audit, or an explicit employer-less work type?
5. **Deployment governance:** is direct devx CI execution an intentional exception to P-28's change-set-only automation rule?

If these decisions are not already recorded in an authoritative spec or amendment, emit a blocking report with the exact decision needed rather than implementing a compatibility workaround.
