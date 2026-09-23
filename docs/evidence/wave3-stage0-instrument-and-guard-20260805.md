# Wave-3 Stage 0 — Instrument and Guard

- **Date:** 2026-08-05
- **Branch:** `db-redesign` @ `f3df729` (+ Stage 0 changes)
- **Environment:** AWS 788159322332 / us-east-1 / **devx** only. `dev` and `staging` untouched.
- **Companion to:** [`wave3-preplan-audit-20260804.md`](./wave3-preplan-audit-20260804.md) (N1–N21),
  [`wave3-preplan-remediation-20260804.md`](./wave3-preplan-remediation-20260804.md) (P0–P6)
- **Scope:** Stage 0 only. No repartition, no env-chain collapse, no
  `ARTIFACTS_TABLE_NAME` change on ai-assist, no F-DEVX-6 work.

---

## 0. Corrections to the inherited documents

Recorded first because later sections depend on them.

| # | inherited claim | verdict | evidence |
|---|---|---|---|
| C1 | "API Gateway access logging is not enabled on the devx stage" (audit §5, row 1) | **WRONG** | `aws apigateway get-stages --rest-api-id ymzhvcxod0` returns a populated `accessLogSettings` whose format already contains `"status": "$context.status"`. Logging has been on since the log group was created 2026-07-20T19:32:22Z. |
| C2 | — (not stated anywhere) | **the real cause** | The log group's retention was `ONE_DAY` and `storedBytes: 0`. Last event 2026-08-03T20:11:23Z; the audit ran 2026-08-04. The data was not missing because logging was off — it was **expired**. |
| C3 | N8 is "three sites" (audit N8; remediation P0.1) | **UNDERSTATED — 12 sites** | The corrected ratchet named 12. Full list in §2. |
| C4 | `cover_letter_handler.py:1441` | off by one — **:1442** | Same for the query form: audit says 1453, actual 1451. |
| C5 | CV reader census row 1: `cover_letter_handler:1052` "resolves via CVS_TABLE_NAME → lands on cvs" | **WRONG ORDER** | `_load_user_cv` appends `USERS_TABLE_NAME` **first** (:1055-1056), `CVS_TABLE_NAME` second (:1057-1058). It lands on **users-table**; cvs-table is only reached if the users lookup misses. |
| C6 | CV reader census row 9: `vpr_handler:54 → USERS (unconfirmed)` | **REFUTED — not deployed** | `careervp-vpr-generator-lambda-devx` does not exist among the 31 devx Lambdas. `_add_vpr_lambda_integration` (`infra/careervp/api_construct.py:1356`) is **defined and never called** — grep for call sites returns only the definition. `vpr_handler.py` is dead code in every environment. |
| C7 | `ENVIRONMENT=devx make deploy-devx` from the repo root | **fails** | The root `Makefile` forwards only 11 named targets and `deploy-devx` is not one of them → `No rule to make target 'deploy-devx'`. It must be run from `src/backend`. |

---

## 1. What changed (0.1 + 0.2)

### 0.1 Observability

**Access log format** — `infra/careervp/api_construct.py:481-505`. Added
`"path": "$context.path"` and `"responseLatency": "$context.responseLatency"`.
`$context.status`, `requestId` and `httpMethod` were already present.
`resourcePath` (the route template) is retained alongside `path` (what the
caller actually asked for).

**Access log retention** — `api_construct.py:465-476`, `ONE_DAY` → `ONE_WEEK`.
This is the change that actually fixes C1/C2: the fields were always there,
the window was too short to read them.

**Handler status codes** — new `log_response_status` decorator in
`src/backend/careervp/handlers/utils/observability.py:21`, applied to **20** API
entrypoints. It is placed closest to the function so it runs inside
`logger.inject_lambda_context` and inherits the correlation id, and it covers
every return path including early returns. Worker handlers that return no
`statusCode` are passed through untouched; an unhandled exception is logged as
`status_code=500` and re-raised unchanged.

### 0.2 Guardrails

**D-H2 ratchet** — `src/backend/tests/unit/test_dh2_dh3_key_authority.py:191-202`.
The pattern covered only the *legacy* grammar (`pk`/`sk`) and `USER#`. The
*canonical* key names were unguarded, which is precisely why N8 passed CI.
Added `applicationId|artifactId` to both the dict-literal and `Key(...)`
alternations, plus a third branch for the raw
`applicationId = :` expression form.

**Fail-fast on a missing table env var** — new
`src/backend/careervp/handlers/utils/env_guard.py`. `require_table_env(*keys,
purpose=...)` returns the first non-empty value or raises `MissingTableEnvError`.
Applied to the N5 archetype, `artifact_cleanup_handler.py:130-137`, and the
`deps.jobs_repo is None → return {'status': 'ok', 'cleaned': 0}` branch was
deleted. `_make_cleanup_deps()` is now called **outside** the handler's
`try`, so the error reaches Lambda and registers on the Errors metric instead
of being folded into a returned status shape.

**Scope note.** The guard was applied to the archetype only. P0.2 warns to
"audit env vars across all 31 Lambdas before enabling" — a broad rollout is a
behaviour change on 31 live functions and is not Stage 0's to make. Other
silent-degrade sites found but **not** fixed are listed in §4.

---

## 2. Guardrail: proven RED, then GREEN

The deliverable is a test that fails against unmodified source. It did.

**BEFORE any handler was touched** — `uv run pytest
tests/unit/test_dh2_dh3_key_authority.py::test_dh2_all_artifact_keys_built_by_core_repository`:

```
E   AssertionError: AC-DH2-1: artifacts/core keys are still built outside the approved
E   careervp/dal/table_registry.py and careervp/dal/core_repository.py modules.
E     src/backend/careervp/handlers/cover_letter_handler.py:1442: get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
E     src/backend/careervp/handlers/cover_letter_handler.py:1451: KeyConditionExpression='applicationId = :uid AND begins_with(artifactId, :prefix)',
E     src/backend/careervp/handlers/cover_letter_handler.py:1472: Key={'applicationId': item_app_id, 'artifactId': item_artifact_id},
E     src/backend/careervp/handlers/interview_prep_handler.py:406: 'Key': {'applicationId': user_id, 'artifactId': artifact_id},
E     src/backend/careervp/handlers/interview_prep_handler.py:601: KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
E     src/backend/careervp/handlers/interview_prep_handler.py:937: KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(company_prefix),
E     src/backend/careervp/handlers/interview_prep_handler.py:1092: get_response = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
E     src/backend/careervp/handlers/interview_prep_handler.py:1111: KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
E     src/backend/careervp/handlers/interview_prep_handler.py:1256: get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
E     src/backend/careervp/handlers/interview_prep_handler.py:1265: KeyConditionExpression='applicationId = :uid AND begins_with(artifactId, :prefix)',
E     src/backend/careervp/handlers/interview_prep_handler.py:1286: Key={'applicationId': item_app_id, 'artifactId': item_artifact_id},
E     src/backend/careervp/handlers/interview_prep_submit_handler.py:211: Key={'applicationId': authenticated_user_id, 'artifactId': artifact_id},
FAILED tests/unit/test_dh2_dh3_key_authority.py::test_dh2_all_artifact_keys_built_by_core_repository
1 failed in 0.08s
```

Both prompt-named offenders are in that list (`cover_letter_handler.py:1442`,
`interview_prep_handler.py:406`), plus **10 the audit never enumerated**.

**AFTER** routing all 12 through the key authority:

```
tests/unit/test_dh2_dh3_key_authority.py ....                          [100%]
4 passed in 0.30s
```

Nine sites became `table_registry.canonical_item_key(...)` or
`table_registry.canonical_key_condition(...)` (both already existed); the two
raw-expression sites became a new
`table_registry.CANONICAL_PREFIX_KEY_CONDITION_EXPRESSION`. Every replacement
is value-identical, so this is a pure refactor: no behaviour changes today, and
the repartition becomes a change in one module instead of twelve call sites.

> **Deviation from the brief, recorded.** The brief said "fix those two sites
> and watch it go green". Two was not enough — the corrected ratchet catches
> twelve, and the test stays RED until all twelve are routed through the
> authority. Fixing all twelve is what makes it green.

---

## 3. Census 0.3 — N8

**DO NOT FIX in this session.** Recorded for the Stage 7 repartition.

| # | subject | verdict | evidence |
|---|---|---|---|
| 1 | `cover_letter_status` handler | **ANOTHER-N8-SITE** | No inline dict in `get_cover_letter_status` itself — but the Lambda `careervp-cover-letter-status-lambda-devx` runs `cover_letter_handler.lambda_handler` (`api_construct.py:2984`), and the status route calls `_find_cover_letter_item(user_id=user_id, ...)` (:974), which passes **`application_id=user_id`** into `dal.read_cover_letter_by_artifact_id` → `dynamo_dal_handler.py:611` `get_item(Key={'applicationId': application_id, ...})`. The defect is the *value* — a Cognito sub in the `applicationId` slot — not the spelling. Post-repartition the canonical read misses **and** so does the `_list_cover_letter_items` fallback (`list_cover_letters_canonical(user_id)` → `dynamo_dal_handler.py:721` `Key('applicationId').eq(application_id)`). `GET /cover-letter/{id}/status` → 404 for every cover letter. |
| 2 | `interview_prep_status` handler | **ANOTHER-N8-SITE** | Same shape. `careervp-interview-prep-status-lambda-devx` runs `interview_prep_handler.lambda_handler` (`api_construct.py:3021`). `get_interview_prep_status` (:549) → `_get_interview_prep_item(user_id, ...)` (:1083), which tries three lookups, **all keyed by the sub**: :1093 canonical `get_item`, :1102 legacy `pk/sk`, :1111 `query applicationId = user_id`. `list_interview_preps` (:601) is a fourth. Post-repartition → 404. |
| 3 | `_find_cover_letter_item` / PATCH lookup | **ANOTHER-N8-SITE — does NOT survive** | `_patch_cover_letter` (:1507) calls `_find_cover_letter_item(user_id=..., ...)`, i.e. item 1's path. This **resolves the audit's open question** ("yes, conditionally … depends on `_find_cover_letter_item` locating the row first") to **no**. Worth noting the *write* half is genuinely safe: :1519-1525 is key-adaptive (`if 'applicationId' in item` → `canonical_item_key(item['applicationId'], item['artifactId'])`). Only the lookup breaks — but the lookup gates the write. |
| 4 | `application_repository.py:320-405` (hub projection) | **SAFE** | `update_artifact_with_id` never touches an artifacts-table key. It writes to the **applications** table under `key = {'userId': user_id, 'applicationId': application_id}` (:341) and stores the artifact id as a plain **non-key attribute**, `artifact_statuses.<type>_artifact_id` (:384-388). Repartitioning the artifacts table changes neither that key nor that value. **Caveat:** safety is conditional on the five callers passing a real application id — `interview_prep_handler:453`, `cover_letter_handler:765`, `vpr_worker_handler:575`, `cv_tailoring_handler:597`, `vpr_submit_handler:193`. Not verified per-caller; out of scope here. |

### 3a. Census finding not asked for: the ratchet has a blind spot

`test_dh2_dh3_key_authority.py:39-40` scans **only** `careervp/handlers` and
`careervp/logic`. `careervp/dal/` is not scanned, so these are invisible to the
guardrail even after the fix:

```
dal/dynamo_dal_handler.py:533   'applicationId': user_id,          <-- N8-shaped WRITE
dal/dynamo_dal_handler.py:611   get_item(Key={'applicationId': application_id, ...})
dal/dynamo_dal_handler.py:721   Key('applicationId').eq(application_id)
```

`:533` is the strongest of the three: `save_cover_letter` **writes**
`applicationId = user_id` into the artifact row, so the DAL is actively
manufacturing the wrong partition value. The `dal/application_repository.py`
hits (14 of them) are on the **applications** table, whose real key *is*
`userId`/`applicationId` — legitimate, not N8.

Flagged, not fixed.

---

## 4. Census 0.4 — CV readers

Verified independently: source line read **and** the live Lambda env var read
from `aws lambda get-function-configuration` on 2026-08-05. Table key schemas
confirmed by `describe-table`.

Live key schemas — these are **different grammars**, which is the pivotal fact
for Stage 1.3:

```
careervp-users-table-devx   HASH pk    RANGE sk        82 items   (legacy grammar)
careervp-cvs-table-devx     HASH userId RANGE cvId     28 items   (canonical grammar)
```

| # | reader | resolves via | lands on | verdict |
|---|---|---|---|---|
| 1 | `cover_letter_handler.py:1051-1064` `_load_user_cv` | **USERS_TABLE_NAME first**, CVS_TABLE_NAME second | **users** | **CORRECTED** — the brief's row says CVS→cvs; the code appends users first (:1055) and cvs second (:1057). Live: USERS=users-table, CVS=cvs-table. |
| 2 | `interview_prep_handler.py:817-825` | `_build_context_dal_candidates('CVS_TABLE_NAME', fallback_dal=dal)` — CVS first, artifacts dal second | **cvs** | CONFIRMED |
| 3 | `gap_handler.py:564-576` | `cv_table_name or users_table_name` | **cvs** | CONFIRMED (line **564**, brief says 563) |
| 4 | `ai_assist_handler.py:358-366` `_load_cv` | CVS_TABLE_NAME | **users** | CONFIRMED — live `CVS_TABLE_NAME = careervp-users-table-devx`. The N3 swap is real. |
| 5 | `vpr_worker_handler.py:411-413` | `DYNAMODB_TABLE_NAME` (default `careervp-users-dev`) | **users** | CONFIRMED — live `DYNAMODB_TABLE_NAME = careervp-users-table-devx` |
| 6 | `cv_tailoring_handler.py:382` and `:826` | `resolve_legacy_artifacts_table_name()` = DYNAMODB→TABLE_NAME; cvtailor has **no** DYNAMODB_TABLE_NAME, `TABLE_NAME = users-table` | **users** | CONFIRMED (lines **382/826**, brief says 380/824) |
| 7 | `logic/cv_tailoring_logic.py:200` | injected dal (row 6's) | **users** | CONFIRMED |
| 8 | `user_handler.py:239-244` `get_user_cv` | `TABLE_NAME` | **users** | CONFIRMED |
| 9 | `vpr_handler.py:43,55` | `os.environ['DYNAMODB_TABLE_NAME']` | **NOT DEPLOYED** | **REFUTED** — see C6. Not a live reader in any environment. |

### 4a. Sites not in the brief's list

| site | role | table |
|---|---|---|
| `user_handler.py:128-153` `_list_user_cvs` | **`GET /users/me/cv` — Stage 1 gate (f)** | `TABLE_NAME` → users |
| `user_handler.py:264` `delete_cv` | `DELETE /users/me/cv/{id}` | `TABLE_NAME` → users |
| `cv_upload_handler.py:188` `save_cv` | **writer** (primary, 500 on failure) | `TABLE_NAME` → users |
| `cv_upload_handler.py:209` `save_cv` | **writer** (secondary, swallowed) | `CVS_TABLE_NAME` → cvs |

Live `careervp-cv-parser-lambda-devx`: `TABLE_NAME = careervp-users-table-devx`,
`CVS_TABLE_NAME = careervp-cvs-table-devx` — confirms the dual write exactly as
the brief describes.

`save_cv` (`dynamo_dal_handler.py:90-105`) writes **both** grammars into
whichever table it is given: canonical `userId`/`cvId` (:101-102) plus legacy
`pk`/`sk` (:104). Confirmed.

### 4b. The trap in gate (f), found before it was sprung

`GET /users/me/cv` is the single most likely thing to break in Stage 1.3, and
it would break **silently**:

```python
# user_handler.py:138 — legacy grammar only, no canonical fallback
'KeyConditionExpression': table_registry.legacy_key_condition(user_id, table_registry.CV_SORT_KEY_PREFIX)
# user_handler.py:146-148 — and the resulting error is swallowed
except Exception as exc:
    logger.exception('Failed to list user CVs', ...)
    return [], None
```

cvs-table is keyed `userId`/`cvId`, so a `Key('pk')` condition raises
`ValidationException`. `_list_user_cvs` catches it and returns an **empty
list**, so repointing `TABLE_NAME` to cvs-table without also rewriting the key
condition produces "the user has no CVs" with a 200. Every sibling reader has a
canonical/legacy fallback pair (`get_cv` :120-130, `get_cv_by_id` :217-226);
`_list_user_cvs` is the one that does not.

Two things follow for Stage 1.3 step 1: the key condition must change with the
repoint, and `_list_user_cvs`'s blanket `except` is itself an N5-class
degrade-to-success.

### 4c. Other silent-degrade sites found (flagged, NOT fixed)

| site | degrades to |
|---|---|
| `user_handler.py:131-133` | `TABLE_NAME` unset → `return [], None` → 200 with an empty CV list |
| `user_handler.py:146-148` | any query error → `return [], None` → 200 with an empty CV list |
| `cv_upload_handler.py:211-212` | cvs-table write fails → `logger.warning(... 'non-fatal')` → still 201 (this is Stage 1 gate (h)) |
| `gap_handler.py:570-572` | no CV table configured → "CV not found" envelope, indistinguishable from a genuinely absent CV |

---

## 5. Consequence of the fail-fast, stated plainly

`careervp-artifact-cleanup-lambda-devx` has **no** `DYNAMODB_TABLE_NAME` in its
live environment (audit N5, re-confirmed 2026-08-05). It is therefore already
in the failing state, and after this deploy its hourly EventBridge run will
**raise instead of returning `{'status':'ok','cleaned':0}`**. That is the
intended effect and is what gate (c) measures — but it converts a silent
57-run no-op into a recurring visible Lambda error in devx.

The fix for the underlying config gap is P3.2 (set the var to the **jobs**
table). It is **not** in Stage 0's scope and was deliberately not applied here.

---

## 6. STAGE 0 GATE — all five hold

Deploy #1: `cd src/backend && ENVIRONMENT=devx make deploy-devx` → `CareerVpCrudDevx`
`UPDATE_COMPLETE`, exit 0, 872.33s.

### (a) A deliberate 401 and a deliberate 409 are distinguishable rows — **PASS**

Driven through the real API. The 409 costs no LLM spend and no trial credit: one
disposable artifact row was seeded with a terminal status, and cancelling a
terminal task is a 409 by contract (`interview_prep_handler.py:1281`). The row
was deleted afterwards.

```
HTTP 401  GET  /users/me                                  (no Authorization header)
HTTP 409  POST /interview-prep/stage0-gate-409/cancel     {"error": "Cannot cancel terminal task"}
HTTP 200  GET  /health                                    (control)
```

The resulting access-log rows:

```json
{"status": "401", "httpMethod": "GET",  "path": "/prod/users/me",                                "responseLatency": "10",  "requestId": "aa28d0f1-6cee-4450-a0a6-02cb1a37d091", "authorizerError": "Unauthorized", "integrationStatus": "-"}
{"status": "409", "httpMethod": "POST", "path": "/prod/interview-prep/stage0-gate-409/cancel",   "responseLatency": "261", "requestId": "ea203f87-f58a-4a0c-b47a-ba5b93141d1e", "authorizerError": "-",            "integrationStatus": "409"}
{"status": "200", "httpMethod": "GET",  "path": "/prod/health",                                  "responseLatency": "35",  "requestId": "9d82a84c-670e-4241-96a6-6467746a7a9d", "authorizerError": "-",            "integrationStatus": "200"}
```

All five required fields are present: `status`, `requestId`, `path`,
`httpMethod`, `responseLatency`.

**Better than the gate asked for.** The 4xx split the audit could not make is
now readable directly off two fields: a security 4xx has
`authorizerError: "Unauthorized"` with `integrationStatus: "-"` (the request
never reached a Lambda), while a contract 4xx has `authorizerError: "-"` with
`integrationStatus` equal to the status. The audit's §5 row 1 — "could not
separate security 4xx from contract 4xx" — is answerable now without a code
change.

**Lag observed, recorded.** The first run of this gate (19:19:10–19:19:24Z),
~1 minute after the stack reported `UPDATE_COMPLETE`, produced rows with the
**old** format — `path` and `responseLatency` absent. A probe at 19:20:5xZ
carried both. The stage's `accessLogSettings` update lags the stack the same
way the CodeDeploy alias shift does. The rows quoted above are from the re-run.

**Handler-side `status_code` confirmed live** (0.1's second deliverable):

```json
{"message": "request completed", "status_code": 409, "service": "careervp-interview-prep-status"}
{"message": "request completed", "status_code": 200, "service": "careervp-health-api"}
```

Note the route mapping, which is not obvious: `POST
/interview-prep/{interviewPrepId}/cancel` is served by
**`interview_prep_status_func`** (`api_construct.py:3494-3497`), not
`interview-prep-api`. `careervp-interview-prep-api-lambda-devx` logged nothing
because it was never invoked.

### (b) The guardrail FAILED before the fix and passes after — **PASS**

Full RED output in §2: 12 sites named, including both prompt-named offenders.
GREEN after: `4 passed in 0.30s`.

### (c) A Lambda with an unset table env var fails loudly — **PASS**

`careervp-artifact-cleanup-lambda-devx`, whose `DYNAMODB_TABLE_NAME` is
`<<< ABSENT >>>` and has been for all 57 prior runs:

```
FunctionError: "Unhandled"
{"errorType": "MissingTableEnvError",
 "errorMessage": "jobs table is not configured: none of DYNAMODB_TABLE_NAME is set",
 "stackTrace": ["artifact_cleanup_handler.py, line 157, in lambda_handler -> deps = _make_cleanup_deps()",
                "artifact_cleanup_handler.py, line 135 -> require_table_env('DYNAMODB_TABLE_NAME', purpose='jobs')",
                "utils/env_guard.py, line 36 -> raise MissingTableEnvError(...)"]}
```

Previously the identical configuration returned `{"status": "ok", "cleaned": 0}`
with no `FunctionError`. No env var was changed to produce this; the function
was already in the failing state.

### (d) Unit baseline intact — **PASS**

`cd src/backend && uv run pytest tests/unit/ -q` →
**`1424 passed, 15 skipped, 4 xfailed`**. Baseline was `1419 passed, 15 skipped,
4 xfailed`; the +5 are the new `test_env_guard_fail_fast.py`. Skips and xfails
unchanged, pass count rose and never fell.

Also clean: `ruff format` (419 files unchanged), `ruff check` (all passed),
`mypy careervp --strict` (137 files, no issues), `validate_naming.py --path infra
--strict` (exit 0), `infra` construct tests (23 passed).

CFN resource counts unchanged against scope-lock §4: parent **261**,
CrudFeatures **241**.

### (e) Both censuses written down — **PASS**

§3 (N8, 4 subjects) and §4 (CV readers, 9 rows + 4 unlisted sites) above.

---

## 7. Files changed

```
infra/careervp/api_construct.py                              access log format + retention
src/backend/careervp/handlers/utils/observability.py         log_response_status decorator
src/backend/careervp/handlers/utils/env_guard.py             NEW — require_table_env
src/backend/careervp/handlers/artifact_cleanup_handler.py    fail-fast (N5 archetype)
src/backend/careervp/dal/table_registry.py                   CANONICAL_PREFIX_KEY_CONDITION_EXPRESSION
src/backend/careervp/handlers/cover_letter_handler.py        3 N8 sites -> key authority
src/backend/careervp/handlers/interview_prep_handler.py      8 N8 sites -> key authority
src/backend/careervp/handlers/interview_prep_submit_handler.py  1 N8 site -> key authority
src/backend/tests/unit/test_dh2_dh3_key_authority.py         ratchet: canonical key names
src/backend/tests/unit/test_env_guard_fail_fast.py           NEW — 5 tests
+ 20 API handlers: one @log_response_status line each
```

Not touched, per the constraints: either project-scope-lock twin,
`test_dh4_p01_canonical_artifact.py`, ai-assist's `ARTIFACTS_TABLE_NAME`, any
`dev` or `staging` resource.
