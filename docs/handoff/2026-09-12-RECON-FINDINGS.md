# Recon findings — 2026-09-12

Evidence base for the three handoff prompts in this directory. Produced by five
parallel read-only agents against `tools/proof-harness` (tip `cea0799`, identical
to `db-redesign`).

**Status of every claim here: UNVALIDATED.** These are agent-reported findings
with citations. They have not been reproduced by execution. Prompt P1 exists to
validate them. Do not fix anything on the strength of this document alone —
see "Calibration" below for why.

---

## Calibration: one finding in this batch was already proven wrong

An earlier agent reported "10 devx DynamoDB tables exist but NO CloudFormation
stack owns them," sourced from a real `make preflight` FAIL with a real evidence
JSON. It was wrong.

`aws cloudformation get-template --stack-name CareerVpCrudDevx` shows all 11
tables declared and owned. The bug is in the tool: `scripts/preflight.py:366`
matches `AWS::DynamoDB::Table`, but CDK's `TableV2` synthesizes
`AWS::DynamoDB::GlobalTable`. Nothing matched, so everything read as unmanaged.

That is the failure mode to hunt: **a confident, specific, cited, reproducible
FAIL that is an artifact of the instrument rather than the system.** It survived
two analysis layers. Assume more of what follows is like it.

---

## The six root causes

Roughly 100 individual findings trace to six causes. Fixing a root cause
collapses its whole column.

| # | Root cause | Findings | Anchor |
|---|---|---|---|
| R1 | No single table authority. `self.db = self.users_table`, so the generic `DYNAMODB_TABLE_NAME` env var resolves to **users** on every Lambda that inherits it — while handlers read it as jobs, artifacts, or VPR. | ~12 | `infra/careervp/api_db_construct.py:114` |
| R2 | Two key schemes coexist. Canonical `applicationId/artifactId` vs legacy `pk/sk`, with `table_registry.py` maintaining *both* and callers picking either. | ~15 | `src/backend/careervp/dal/table_registry.py:75-90,114-135` |
| R3 | `except Exception: pass` is the default error idiom. Infra failure becomes "not found" becomes HTTP 404/200. | ~40 | pervasive; 17 in `interview_prep_handler.py` alone |
| R4 | `Limit=N` + `FilterExpression` misused. DynamoDB applies `Limit` **before** the filter, so these read N arbitrary items, filter them out, and return empty. | 8 | `dynamo_dal_handler.py:796` + 7 more |
| R5 | Synchronous LLM work behind API Gateway's hard 29s cap. VPR was moved async; gap-analysis, interview-prep and CV-tailoring were not. | ~6 | `gap_handler.py:184-191` |
| R6 | Auth has dev-mode escape hatches live in production code paths. | ~5 | `logic/auth_service.py:184-188,153-163` |

---

## SEV-0 — live cross-tenant data leaks

Both are on **registered, live routes**. Both are ~one-line guards. Fix first.

### S0a. `GET /jobs/{jobId}/artifacts/vpr/export` has no ownership check at all
`handlers/export_handler.py:124-133`. `user_id` is authenticated at `:61` and then
**dropped** for the `vpr` branch:
```python
def _read_artifact(module_type, job_id, user_id):
    if module_type == 'vpr':
        return _read_vpr(job_id)          # <-- user_id not passed
    if module_type == 'cover_letter':
        return _read_cover_letter(job_id, user_id)
```
`_read_vpr` reads `results/{job_id}.json` from S3 with no scoping. The other three
branches are correctly scoped (`canonical_item_key(user_id, ...)` /
`legacy_key_condition(user_id, ...)`) — `vpr` is the lone outlier.

Live: `infra/careervp/api_construct.py:3165` + `:3508`. No precondition, any VPR,
any age. **Any authenticated user can export any other user's VPR to DOCX and
receive a presigned S3 URL for it.**

### S0b. VPR status S3 fallback sits above the ownership check
`handlers/vpr_status_handler.py:543-551`. The `_try_build_response_from_s3(vpr_id)`
branch takes no `user_id` and returns the full enriched VPR plus a presigned
download URL. The owner comparison is at `:554-558` — **below** it, guarding only
the DynamoDB branch.

Trigger: the jobs-table row TTLs out at 24h (`jobs_repository.py:475`) while the
S3 object persists indefinitely. So for any VPR older than 24 hours, any
authenticated caller with the `vprId` gets the owner's content. Widened by A7.4 —
a transient `ClientError` in `get_job` also returns `None`, reaching the S3 branch
*inside* the 24h window.

Fix: pass `user_id` into `_read_vpr`; move the `job_owner` check above the
fallback.

---

## SEV-1 — data loss, silent wrong output, or security

### S1. True IDOR: cross-tenant VPR read
`handlers/cv_tailoring_handler.py:418-422` calls
`dal.get_vpr(application_id=vpr_id)` where `vpr_id` is **request-body supplied**,
and `dal/dynamo_dal_handler.py:318-340` takes no `user_id` and performs no
ownership check. The fetched VPR feeds the tailoring pipeline (`:476`) and its
`job_posting` fields are copied into the response artifact (`:432-440`).

`cover_letter_handler.py:356-358` does this correctly — it compares `vpr_owner`
to `user_id` and raises on mismatch. The two handlers disagree.

### S2. Unauthenticated identity via the SFN-invoke branch
`handlers/cv_tailoring_handler.py:301-318`. `_is_sfn_invoke` is evaluated
**first in `handler`** (`:68`), before any auth, and takes `user_id` verbatim
from the event body. Guard is `not event.get('httpMethod')`, which is also true
for API Gateway HTTP API **v2** payloads (those use `requestContext.http.method`).

### S3. Auth silently downgrades to self-signed JWT
`logic/auth_service.py:184-188`. Any `COGNITO_CLIENT_ID` starting with `test-`,
or empty/unset, routes `_use_cognito_auth` (`:191-194`) to the legacy
self-signed-JWT path (`:202-203,274-275,321-322`). No error, no alarm, no log.

### S4. Ephemeral RSA keys reachable outside local dev
`logic/auth_service.py:153-163`. The `ENV != 'local'` guard is on the `else`
branch only. In the `use_cognito` branch, missing JWT SSM params silently mint a
per-container throwaway keypair (`:84-93`, `@lru_cache`). Tokens from container A
fail in container B — random self-healing 401s.

### S5. JWT verified without issuer, audience, or jti
`logic/auth_service.py:369-374`. No `issuer=`, no `audience=`; `_mint_tokens`
(`:413-426`) emits no `iss`/`aud`/`jti`. Any RS256 token signed by the same key
is accepted on any route, and with no `jti` **revocation is impossible** — a
stolen refresh token is valid the full 7 days (`:36`). `exp` *is* enforced.

### S6. Gap-analysis fabricates questions and returns HTTP 200
`logic/gap_analysis.py:299-305`. LLM parse failure → `except Exception` →
`parsed_questions = []` → `_ensure_question_count` (`:308`) manufactures 10
template questions → handler returns **200 + `GAP_QUESTIONS_GENERATED`** and
persists them. Total LLM failure is indistinguishable from success.

### S7. VPR degrades to a placebo report, billed, with no error signal
`logic/vpr_generator.py:469-517` (10 sites). Each section falls back to canned
boilerplate on `ValidationError`; `:607` supplies
`'Candidate demonstrates relevant background for this role...'` with
`overall_fit_score=50`. Separately `:262-274` returns `success=True, code=SUCCESS`
for a VPR that failed the quality gate twice — `quality_warning=True` is set but
`vpr_handler.py:64` only checks `result.success`, so it never surfaces.

### S8. Cover letters silently generated without gap answers
Write path: `gap_handler.py:74-76` → `gap_responses` table.
Read path: `cover_letter_handler.py:382` passes the DAL from `_get_dal()`
(`:63-66` → `ARTIFACTS_TABLE_NAME`) into `_resolve_gap_responses` (`:302-309`),
which queries `Key('userId') & Key('questionId')` against a table keyed
`applicationId/artifactId`. Always raises; swallowed to `[]` at `:310-312`.
`interview_prep_handler.py:881-883` reads the *correct* table. The two disagree.

### S9. Full CV and prompt context logged at INFO
`handlers/interview_prep_handler.py:834` logs `cv_payload=cv_dict` — entire
parsed CV. `:1003-1008` logs the full `generation_context` (CV facts, VPR data,
gap answers). Plus `:131,133,302,915,1057`. Same class as the already-closed
F-DEVX-2. `cv_tailoring_handler.py:83-90,1247-1252` log full request and
**response** bodies at DEBUG (tailored CV text).

### S10. Cancel reports success with every write swallowed
`handlers/vpr_status_handler.py:435-448`. `stop_execution`,
`update_chain_execution_status`, and the status write are each wrapped in
`except Exception: pass`; the caller returns `{'status': 'cancelled'}` (`:420-424`).
Generation and billing continue while the user is told it stopped.

### S11. Phantom-write cancel (upsert + TOCTOU)
`cover_letter_handler.py:1470-1476`, `cv_tailoring_handler.py:906-912`.
`update_item` with no `ConditionExpression`: (a) races the worker, (b) is an
**upsert** — if the item was found via the legacy schema this writes a brand-new
`{applicationId, artifactId, status: CANCELLED}` item while the real artifact
keeps running, and still returns 200.

### S11b. Fail-open idempotency: duplicate paid VPR generation
`dal/jobs_repository.py:259-265`. `get_job_by_idempotency_key` returns `None` on
`ClientError`. Caller `vpr_submit_handler.py:283-289` reads `None` as "no prior
job, proceed". **A single GSI throttle turns the idempotency guard off** and
enqueues a duplicate paid VPR. The one place idempotency is enforced on this path
fails open.

### S11c. Payment events lost permanently on a throttle
`dal/subscription_repository.py:288-294`. Both the
`ConditionalCheckFailedException` branch and the generic `ClientError` branch
`return False`. The caller's contract is "`True` = first delivery, process it", so
on a transient throttle the webhook is discarded as a duplicate — **never
processed, never retried**, because the handler acks. A subscription activation is
lost for good. The conditional branch is correct; the fall-through must raise or
return a tri-state.

### S11d. CV upload 500s whenever the parser extracts a GPA
`dal/dynamo_dal_handler.py:99-105`. `save_cv` does
`user_cv.model_dump(exclude_none=True, mode='json')` — `mode='json'` leaves Python
`float` as `float` — then `put_item`. `models/cv.py:92` declares
`gpa: float | None`. boto3 raises `TypeError: Float types are not supported`,
which is **not** in the `(ClientError, ValidationError)` catch, so it escapes
`save_cv` entirely. Since commit `7cdc5e5` made that write fatal, the whole upload
now 500s. The file already has `_convert_floats_to_decimal` at `:889`; `save_cv`
doesn't call it. Same omission in `save_vpr` (`:304-311`, `cost_usd: float`).

### S11e. The P-24 resolver identity is wired to nothing
`handlers/api_gateway_authorizer.py:126-134` emits `policy['context']` with a flat
`user_id`. REST API surfaces authorizer context as
`requestContext.authorizer.user_id` — never nested under `claims`. But
`auth_utils.extract_user_id` only inspects `authorizer.jwt.claims.sub` and
`authorizer.claims.sub`, so it returns `None` for every request once this custom
authorizer is activated. Fails closed (401s, not a bypass) — but the
`internal_user_id` surrogate the resolver computes is unreachable by any handler.

### S12. ID token in a JS-readable cookie
`src/frontend/contexts/AuthContext.tsx:30-34`. No `Secure`, not `HttpOnly`
(can't be — it's JS-set). Any XSS exfiltrates a live Cognito ID token.

---

## SEV-2 — breaks at scale, wrong results, or cost

### S13. `Limit` + `FilterExpression` (R4) — 8 sites
`dynamo_dal_handler.py:796` (a full `scan`), `company_research_handler.py:430`,
`cv_tailoring_handler.py:1039`, `cover_letter_handler.py:1455`,
`interview_prep_handler.py:938,1112,1125,1269`.
Each reads N arbitrary items, filters, returns empty → "artifact not found" for
artifacts that exist. **Masked today because tables are small.** Breaks as
rows-per-user grows — i.e. exactly at launch.

### S14. Unpaginated query → 404 on real data
`export_handler.py:166`, `ai_assist_handler.py:462-468`,
`dynamo_dal_handler.py:1062-1066` (gap responses; `max()` over page 1 only, so a
user past 1MB silently loses their newest answers).

### S15. No idempotency claim on SQS workers
`dal/idempotency_repository.py:36-49` implements a correct atomic claim, but
**only `company_research_worker_handler.py:92` calls it**. `cover_letter_handler`,
`interview_prep_handler`, `vpr_worker_handler` do not. SQS redelivery re-runs
full LLM generation → duplicate spend against the 91% margin target, duplicate
artifact writes. `vpr_worker_handler.py:321-335` reads-then-skips
non-atomically; two concurrent redeliveries both pay.

### S16. LLM timeout accepted and discarded
`logic/llm_client.py:122-128`: `def generate(self, prompt, timeout=300, ...)` then
`_ = timeout`. Client built with no timeout at all (`:92`). SDK defaults (600s, 2
retries) wrapped in its own 3-attempt loop → **6 attempts × 600s**. The
`except TimeoutError` branch in `gap_analysis.py:286` is therefore dead code.

Two divergent LLM clients coexist: `logic/utils/llm_client.py:146-150` *does* set
`timeout=180.0, max_retries=3`, then stacks `@retry_on_transient_error(max_retries=3)`
at `:186` → 9 attempts × 180s ≈ **27 minutes worst case**.

### S17. Interview prep deterministically truncates its first attempt
`logic/interview_prep.py:96-101` + `:25` (`MAX_QUESTIONS = 15`, though CLAUDE.md
documents 10) against `max_tokens=4096` hardcoded at `logic/llm_client.py:288`.
15 questions × "150-300 word STAR answers" (`prompts/interview_prep_prompt.py:42`)
needs ~6000 output tokens. Attempt 1 always truncates into invalid JSON, burning
a full round-trip before the 5-question retry.

### S18. `HTTP 202 ACCEPTED` returned by a fully synchronous pipeline
`cv_tailoring_handler.py:205-207 → 472-477 → 566-573`. Its own docstring (`:333`)
says "synchronously". Returns `'estimated_time_seconds': 0`. On the API Gateway
path this runs three chained LLM calls plus ~8 round trips; past 29s the client
gets a 504 while the Lambda completes and persists — so the artifact exists, the
user saw failure, and the retry pays for a second pipeline.

### S19. Eight-table serial probe on the critical path
`cover_letter_handler.py:199-247`. `_jobs_table_candidates()` returns up to 8
names including **hardcoded `careervp-jobs-table-prod` / `-staging`** and
`careervp-vpr-jobs-table-dev` (never a real table — `vpr-jobs` is not a feature
per `constants.py:25`). Each iteration builds a fresh `JobsRepository` →
`boto3.resource` → `get_item`. `devx` is absent from the list entirely.

### S20. A new boto3 session per DAL call
`dal/dynamo_dal_handler.py:83-87` constructs `boto3.session.Session()` on **every**
`_get_db_handler` call; `cover_letter_handler.py:670,1511,1429` and
`cv_tailoring_handler.py:865,958` do `import boto3` inside function bodies and
build a resource per invocation. A single cover-letter POST constructs well over
a dozen clients.

### S21. Whole users table into memory
`dal/subscription_repository.py:403-422`. Correctly paginated, but accumulates
every row into one list to find active subscriptions. OOM at scale.

### S22. Cache key collision drops profile data
`logic/company_research.py:561-562`: key is the company name alone. The news-only
path (`:314`) and the full-profile path (`:229`) both `cache.set` under it
(`:535`), so a news refresh overwrites the full profile and the next full request
gets a partial result as a cache hit (`:477`).

### S23. O(n×m) tokenizer on the request path
`logic/vpr_generator.py:977-989`. `_text_tokens` (regex findall + set build) runs
`len(job_requirements) × len(evidence_pool)` times; `evidence_pool` is never
truncated and `:281-286` accumulates every achievement from every role with no cap.

### S24. Module-global request state leaks across warm invocations
`handlers/cors_utils.py:6,11-13,18`. `_current_request_origin` is a module global
set per invocation, but **only 20 of 35 handlers** call `set_request_origin` —
the other 15 reuse the previous request's origin.

### S25. Gap-analysis state machine has never advanced
`gap_handler.py:874-883` calls `update_state(..., user_id='')` where `user_id` is
the partition key (`application_repository.py:83-91`). Empty string never matches
→ `ConditionalCheckFailedException` **every time** → `except Exception: pass`.
Then `:260-279` depends on the state that was never set, also fails, also
swallowed, and returns `HTTPStatus.OK`. Applications stall at `cv_selected`
forever. Exact sibling of the class fixed in commit `7cdc5e5`.

### S26. Prompt injection, unbounded and undelimited
`logic/company_research.py:479-480` interpolates **scraped third-party web text**
plus a raw user `company_name` (`models/company.py:25` — bare `str`, no
`max_length`) with no delimiters (`prompts/company_research_prompt.py:14-19`).
Output is written to DynamoDB and later consumed as trusted `company_context`.
`vpr_generator.py:614-620` passes CV text, full job posting, and free-text
`gap_responses` with no `max_length` on `JobPosting` (`models/job.py:49-68`) or
`GapResponse.answer` (`:79`). Stage N output feeds Stage N+1 across six stages.
`gap_analysis.py:281-286` and `interview_prep.py:93` **concatenate system and
user prompt into one user-role message** — there is no privileged channel at all.
`cv_tailoring_handler.py:472-477`: `validate_job_description` is imported (`:37`)
but applied on the legacy path only (`:228`) — the OpenAPI async path never calls it.

---

## SEV-3 — dead code, contract drift, waste

- **Knowledge Base is entirely dead.** `knowledge_base_handler.py` and
  `dal/knowledge_repository.py` have zero infra references; `GET /knowledge-base`
  is served by `company_research_handler.py:55,305`. The `knowledge` table
  (`api_db_construct.py:434`) has zero live readers and zero live writers. It is
  a documented V1 feature that exists only as unreferenced code.
- **A second full frontend app is dead.** Root `frontend/` alongside
  `src/frontend/`. `amplify.yml` sets `appRoot: src/frontend`; all active CI runs
  `cd src/frontend`. Kept alive only by a path-trigger in
  `.github/workflows/cv-tailoring.yml` and `test_frontend_asset_hygiene.py`.
  The two copies of `app/applications/new/page.tsx` have genuinely diverged.
- **`src/frontend/canvas-app/App.jsx`** — referenced only by its own tests.
- **Three permanently unreachable routes**: `/users/me/vprs`
  (`vpr_status_handler.py:314`), `/users/me/cover-letters`
  (`cover_letter_handler.py:438`), `/users/me/tailored-cvs`
  (`cv_tailoring_handler.py:106`) — `/users/{proxy+}` (`api_construct.py:3507`)
  routes all of `/users/*` to `user_api_func` first.
- **Every sign-out 404s.** `AuthContext.tsx:81` calls
  `POST /api/proxy/auth/logout`; no such handler exists. Swallowed by `.catch()`.
- **Frontend overwrites the server's `job_id`** with `crypto.randomUUID()` —
  `src/frontend/api/methods.ts:161,179`.
- **Write-only CV rows.** `cv_upload_handler.py:187` writes the users table and
  `:211` the cvs table; all readers use `CVS_TABLE_NAME` only
  (`table_registry.py:194-202`). Every users-table CV row is never read.
- **Dead table literals**: `'cv-tailoring'` (`dal/cv_tailoring_dal.py:16`),
  `'vpr_table'` (`dal/api_storage_adapter.py:56-61`), `cv_dal.py:76-79` keys on a
  bare `cv_id` that no live table uses.
- **`artifact_cleanup_handler.py:135`** requires `DYNAMODB_TABLE_NAME`, which its
  infra env (`api_construct.py:2717-2722`) never sets. **Raises on every invocation.**
- **`COVER_LETTER_LEGACY_READ_ENABLED` defaults `'true'`**
  (`dynamo_dal_handler.py:618,780`) and infra pins `"true"` on three Lambdas
  (`api_construct.py:2079,2923,3000`) — every canonical miss escalates to a full
  legacy **scan**.
- **`_build_default_cover_letter_status_payload`**
  (`cover_letter_handler.py:1405-1421`) — a hardcoded fake cover letter marked
  `'status': 'completed'`. Zero references repo-wide, including tests.
- **`_normalize_tailoring_status`** (`cv_tailoring_handler.py:1063-1068`) returns
  `'completed'` for any unrecognized status — including `'cancelled'`, which
  `_handle_cv_tailoring_cancel` (`:910`) writes.
- **Interview prep cap drift**: `logic/interview_prep.py:25` `MAX_QUESTIONS = 15`
  vs CLAUDE.md "10 Q max".
- **WAF body-size fix is devx-only**: `waf_construct.py:20-42,61` gates the 64KB
  inspection limit to `_LARGE_BODY_ENVIRONMENTS = frozenset({"devx"})`.
  dev/staging/prod still enforce 8KB — **prod would launch with the bug that
  blocked every real CV upload**.
- **`deploy.yml:37`** hardcodes `STACK_NAME: 'CareerVpCrudDev'` at file level,
  feeding the `push: branches: [main]` job unconditionally. The correct
  environment→stack mapping exists at `:279` but applies to `workflow_dispatch`
  only. This is both the cause of the devx→dev stack overwrite and the live P-28
  enforcement hole ("automation must never `ExecuteChangeSet`").

---

## Confirmed-good (do not "fix")

- `handlers/auth_utils.py:16-49` — identity from Cognito claims only, header
  fallback removed, fails closed. **F-DEVX-8 looks genuinely closed.** No
  body/query `user_id` reaches a write; `cv_upload_handler.py:283` strips it
  before the spread at `:301`.
- `_verify_password_pbkdf2` uses `hmac.compare_digest` (`auth_service.py:508`);
  `PBKDF2_ITERATIONS = 200_000` (`:37`) meets current guidance;
  `_register_user_legacy` uses a `ConditionExpression` for atomic uniqueness (`:259`).
- `_update_artifact_status` (`cover_letter_handler.py:718-720`) is the one place
  that inspects `ConditionalCheckFailedException` correctly.
- `_list_cover_letter_items` / `_list_tailored_cv_items` delegate to DAL methods
  that **do** paginate correctly.
- Infra operability is genuinely strong: Powertools, X-Ray, custom metrics, DLQs
  on every async path, PITR on all tables, budget + cost-anomaly alarms, and
  `DeployedGitSha` really is wired (`service_stack.py:177-182`).
- Zero bare `except:` and zero mutable default arguments repo-wide.
