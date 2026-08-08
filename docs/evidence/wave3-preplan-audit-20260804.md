# Wave-3 Pre-Plan Audit — adversarial evidence review

- **Date:** 2026-08-04
- **Branch:** `db-redesign` @ `f3df729`
- **Environment:** AWS 788159322332 / us-east-1 / **devx**
- **Mode:** READ-ONLY. No file changed, nothing deployed, no product-table write, no
  artifact-creating POST, no live/e2e suite run, no authentication performed.
- **Status:** this audit proposes; a human disposes. No scope-lock twin, no
  `wave-3-status.md`, no spec was edited.

Metric window for all CloudWatch figures: `2026-01-01 → 2026-08-05`, summed across
**all** returned datapoints. (An earlier pass in this session read only
`Datapoints[0]` over a 93-day period and undercounted; every number below is the
corrected full-window sum.)

---

## 1. FINDINGS

### 1a. NEW findings (not in S1–S8), ranked by severity

---

#### N1 — CRITICAL — The CV-upload S3 worker has never once succeeded: 66/66 invocations fail, 22 uploads stranded in a DLQ

`careervp-cv-upload-worker-lambda-devx` is triggered by S3 `ObjectCreated` on the
CV bucket, but it is deployed with the *API-Gateway* handler and immediately calls
the API-Gateway resolver on an S3 event:

```
src/backend/careervp/handlers/cv_upload_handler.py:382
    response: dict[str, Any] = app.resolve(event, context)
```

Live failure, every invocation:

```
errorType: KeyError   errorMessage: 'httpMethod'
  cv_upload_handler.py:382 in lambda_handler -> app.resolve(event, context)
  aws_lambda_powertools/event_handler/api_gateway.py:2612 in _resolve
    method = self.current_event.http_method.upper()
  .../data_classes/common.py:237 in http_method -> return self["httpMethod"]
```

Evidence:
- **Invocations 66, Errors 66 — 100% failure rate.** Duration avg 5ms / max 23ms,
  i.e. it dies before doing any work.
- Repeating `requestId`s in the log (`3c563135…`, `7b7dce59…`) show Lambda's async
  retry: ~22 distinct S3 events × 3 attempts = 66 errors.
- **`careervp-cv-upload-worker-dlq-devx` holds 22 messages**, undrained.
- Infra confirms the intent and the mistake in one place —
  [`infra/careervp/api_construct.py:1841-1856`](../../infra/careervp/api_construct.py#L1841-L1856):
  `"""Create cv_upload_worker (S3 event -> Lambda) with an explicit DLQ."""` with
  `handler="careervp.handlers.cv_upload_handler.lambda_handler"` — the same handler
  bound to the `POST /users/me/cv` route.
- `interview_prep_handler.py:79-83` shows the pattern that is missing here: it
  branches on `event.get('Records')` / `eventSource == 'aws:sqs'` before resolving.
- **Zero test coverage:** `grep -rl "aws:s3\|s3:ObjectCreated" src/backend/tests/`
  returns **0 files**. The entire unit suite cannot see this class of bug.
- The uncommitted working-tree diff to `cv_upload_handler.py` does **not** address
  it (it concerns taking `user_id` from the authorizer in `_normalize_request_payload`).

**Blast radius.** CV upload is the first step of the user journey and the root
dependency of VPR → gap → cover letter → interview prep. The synchronous API call
returns 2xx while the async post-processing behind it fails silently 100% of the
time. This is the single strongest counter-example to "every call returns 2xx" as a
health signal, and it is invisible to the unit suite, to the API-Gateway metrics,
and to any test that only checks response codes.

---

#### N2 — CRITICAL — Gap analysis is not "on the 29s ceiling", it is already through it at p95

The plan's reference point ("27,965ms then 29,222ms — it was on the ceiling and
nobody knew") understates the situation. Full-window `AWS/Lambda Duration` for
`careervp-gap-api-lambda-devx` (40 invocations):

| stat | ms | margin to 29,000ms |
|---|---:|---:|
| Average | 8,432 | +20,568 |
| **p95** | **29,140** | **−140** |
| **p99** | **29,728** | **−728** |
| **Max** | **29,853** | **−853** |

**More than 5% of gap-analysis calls exceed the API Gateway hard ceiling and 504.**
Corroborated at the gateway: `AWS/ApiGateway Latency` for
`careervp-core-api-devx` shows `Maximum` 29,037ms and 29,106ms in two separate
datapoints, and an August **p99 of 28,446ms — 554ms of margin API-wide**.

**Blast radius.** Session 3 (Gap → async) is not an improvement, it is a repair of
a currently-broken endpoint. This *raises* the priority of session 3 relative to
sessions 1 and 2 (see §3).

---

#### N3 — CRITICAL — `ai-assist` has `ARTIFACTS_TABLE_NAME` and `COMPANY_RESEARCH_TABLE_NAME` pointing at swapped tables, and has never been invoked

Live Lambda environment, `careervp-ai-assist-lambda-devx`:

```
ARTIFACTS_TABLE_NAME         = careervp-users-table-devx      <-- users table
COMPANY_RESEARCH_TABLE_NAME  = careervp-artifacts-table-devx   <-- artifacts table
CVS_TABLE_NAME               = careervp-users-table-devx
```

Every other Lambda in devx sets `ARTIFACTS_TABLE_NAME = careervp-artifacts-table-devx`.
`ai-assist` is the sole inversion. This is deliberate — it is exactly what
[`table_registry.py:12-15`](../../src/backend/careervp/dal/table_registry.py#L12-L15)
warns about:

> *"the ai-assist Lambda points `ARTIFACTS_TABLE_NAME` and
> `COMPANY_RESEARCH_TABLE_NAME` at different physical tables, so collapsing the
> chains would silently retarget reads."*

**This is direct, in-repo evidence against session 2's third deliverable
("collapse the env chain").** The env var name does not denote a table; it denotes
"wherever *this* Lambda's artifacts happen to live". Collapsing the chain without
first re-homing the data cross-wires ai-assist's CV/artifact reads onto the wrong
physical table.

Compounding it: **`ai-assist` has zero invocations and zero errors** — it has never
run. There is no live signal, and no test, that would catch a mis-set env var here.
The frontend *does* call it ([`api/methods.ts:333`](../../src/frontend/api/methods.ts#L333)
→ `POST /ai/assist`) and the route *is* deployed, so this is a live, reachable,
never-exercised path.

**Blast radius.** Session 2 changes the home of `cv_tailored`, which is precisely
what ai-assist reads via `ARTIFACTS_TABLE_NAME=users-table`. Session 2 must re-point
these two env vars in the same change, with no test and no metric to confirm it.

---

#### N4 — HIGH — Five of six artifact types have no delete path at all; the whole API exposes exactly one DELETE route

Enumerated from the deployed API (`aws apigateway get-resources`, 49 routes):

| artifact | Create | Read | Update | Delete |
|---|---|---|---|---|
| `company_research` | `POST /company-research/fetch` | `GET /company-research/{jobId}` | — | **none** (cancel only) |
| `vpr` | `POST /vpr/generate` | `GET /vpr/{vprId}/status`, `GET /vprs` | — | **none** (cancel only) |
| `gap_analysis` | `POST /gap-analysis/{proxy+}`, `POST /jobs/{jobId}/gap-questions` | `GET /jobs/{jobId}/gap-questions` | `POST /jobs/{jobId}/gap-responses` | **none** |
| `cv_tailored` | `POST /cv-tailoring/generate` | `GET /cv-tailoring/{id}/status`, `GET /cv-tailorings` | `PATCH /cv-tailoring/{id}` | **`DELETE /cv-tailoring/{id}`** |
| `cover_letter` | `POST /cover-letter/generate` | `GET /cover-letter/{id}/status`, `GET /cover-letters` | `PATCH /cover-letter/{id}` | **none** (cancel only) |
| `interview_prep` | `POST /interview-prep/generate` | `GET /interview-prep/{id}/status`, `GET /interview-preps` | `PATCH /interview-prep/{id}` | **none** (cancel only) |

`DELETE /cv-tailoring/{cvTailoringId}` is the **only** artifact DELETE in the API.
(`DELETE /users/me/cv/{cv_id}` exists for the *raw* CV via `@app.delete` in
`user_handler.py:251`, routed through `/users/{proxy+}` ANY.)

Cancellation is not deletion: `_cancel_cover_letter` / `_cancel_interview_prep` set
`status = 'CANCELLED'` and leave the row.

**The frontend never issues a DELETE at all** — `src/frontend/api/methods.ts`
contains PATCH for cover-letter/interview-prep/cv-tailoring and no `.delete(` for
any artifact. So even the one existing DELETE route is unreachable from the UI.

**Blast radius.** The 40% "Update + Delete work — full CRUD" number is not a
confidence about whether Delete is *correct*; Delete does not exist for 5 of 6
types. See §2.

---

#### N5 — HIGH — The scheduled artifact-cleanup reaper is a permanent no-op that reports success

`careervp-artifact-cleanup-lambda-devx` runs on an EventBridge schedule: **57
invocations, 0 errors, avg 6,305ms.** It has never cleaned anything.

```
src/backend/careervp/handlers/artifact_cleanup_handler.py:130-136
    jobs_table = os.environ.get('DYNAMODB_TABLE_NAME', '')
    ...
    jobs_repo=JobsRepository(jobs_table) if jobs_table else None,

artifact_cleanup_handler.py:152-155
    if deps.jobs_repo is None:
        logger.warning('No jobs table configured — reaper skipping')
        return {'status': 'ok', 'cleaned': 0, 'dry_run': dry_run}
```

`careervp-artifact-cleanup-lambda-devx` **has no `DYNAMODB_TABLE_NAME`** in its live
environment. Live log evidence — 6 of the 7 most recent runs:

```
  7  Artifact cleanup reaper starting
  6  No jobs table configured — reaper skipping
```

Two independent defects in one function:
1. It returns `{'status': 'ok', 'cleaned': 0}` — a *success* shape — for a
   total configuration failure. This is precisely the class of illegibility
   session 1 exists to fix, and is **evidence FOR session 1**.
2. Even when configured, `cleanup_cancelled_artifact` deletes only the **S3**
   result object (`_delete_s3_result` → `s3.delete_object`). It never deletes a
   DynamoDB artifact row. There is no DynamoDB reaper for any artifact type.

---

#### N6 — HIGH — `cv-tailor-worker` consumes an unfiltered DynamoDB stream on the artifacts table and silently no-ops on every write

An artifacts-table **stream consumer** exists that the plan does not enumerate:

```
function: careervp-cv-tailor-worker-lambda-devx
source:   arn:aws:dynamodb:...:table/careervp-artifacts-table-devx/stream/2026-07-20T19:32:05.337
state:    Enabled   BatchSize: 1   StartingPosition: LATEST
FilterCriteria: null          <-- no filter: every write invokes it
```

Its handler is the CV-tailoring **API** handler
(`careervp.handlers.cv_tailoring_handler.handler`). Given a stream record it does
`_is_sfn_invoke(event)` → false, then
`method = str(event.get('httpMethod','')).upper()` → `''` and
`path = str(event.get('path','')).rstrip('/')` → `''`, falls through every route
branch, and returns. Measured: **24 invocations, 0 errors, avg 3ms, max 15ms** —
a no-op on every single artifacts-table write.

**Blast radius.** Two things follow. (a) Investigation 6's enumeration of
artifacts-table readers is incomplete unless it includes a DynamoDB stream; after
session 2's repartition the stream's `Keys` payload changes shape, and this consumer
is the one place that would be silently affected. (b) Unlike N1 it fails *without*
erroring, so no error metric will ever surface it.

---

#### N7 — HIGH — TTL is live on the artifacts table under `expiration`, and three different TTL attribute names are in use

Live TTL configuration across devx:

| table | TTL status | attribute |
|---|---|---|
| **artifacts-table** | **ENABLED** | **`expiration`** |
| cvs-table | ENABLED | `expiration` |
| knowledge-table | ENABLED | `expiration` |
| gap-responses-table | ENABLED | `expiration` |
| jobs-table | ENABLED | `ttl` |
| company-research-cache-table | ENABLED | `expiresAt` |
| users-table | DISABLED | — |
| applications-table | DISABLED | — |
| identity-map-table | DISABLED | — |

Consequences visible in live data:
- Only **3 of 25** artifact rows carry `expiration` (all `interview_prep`,
  set to 2028-08-02 by `interview_prep_handler.py:1043`, a 730-day TTL). The other
  22 never expire. S7's "most artifacts have no TTL" — confirmed.
- One artifacts row carries a `ttl` attribute, which is **not** the artifacts TTL
  attribute — it will never expire.
- `ARTIFACT#GAP_ANALYSIS#…` rows in **users-table** carry `ttl`, but users-table TTL
  is DISABLED — also dead.

**Blast radius for session 2.** Session 2 moves `cv_tailored` and `gap_questions`
*into* the artifacts table, where TTL is **ENABLED on `expiration`**. Any moved item
that carries or acquires an `expiration` attribute will be silently deleted by
DynamoDB with no application log line. Conversely, items relying on `ttl` for
expiry silently become immortal. The plan does not mention TTL.

---

#### N8 — HIGH — The cover-letter and interview-prep cancel paths hardcode `applicationId = user_id` in raw dicts, bypassing the key authority

```
src/backend/careervp/handlers/cover_letter_handler.py:1441
    get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})

cover_letter_handler.py:1453-1457
    query_resp = table.query(
        KeyConditionExpression='applicationId = :uid AND begins_with(artifactId, :prefix)',
        ExpressionAttributeValues={':uid': user_id, ...})

interview_prep_handler.py:406
    'Key': {'applicationId': user_id, 'artifactId': artifact_id},
```

These construct `applicationId`/`artifactId` as **inline literal dicts**, not via
`table_registry.canonical_item_key()`. `table_registry`'s docstring claims it and
`core_repository` are *"the only approved builders"* of these key values, statically
enforced by `tests/unit/test_dh2_dh3_key_authority.py`. That enforcement is
evidently not catching these three sites.

**Blast radius.** Under session 2 the artifacts partition key changes from `user_id`
to `applicationId`. These three sites will look up `applicationId = <a Cognito sub>`
and find nothing — cancel returns 404 for every cover letter and interview prep.
Because they bypass the key authority, a session-2 change that correctly updates
`table_registry` will leave them broken, and the D-H2 static test will still pass.

---

#### N9 — MEDIUM — The legacy cover-letter fallback read is functionally broken: `Limit=1` is applied *before* the filter

```
src/backend/careervp/dal/dynamo_dal_handler.py:796
    response = table.scan(FilterExpression=Attr('pk').eq(pk) & Attr('sk').eq(sk), Limit=1)
```

In DynamoDB, `Limit` bounds the items **evaluated**, and `FilterExpression` is
applied afterwards. This scan evaluates exactly **one arbitrary item** and then
tests whether it happens to be the wanted one. Against the current 25-row table the
hit probability is ~1/25; it degrades as the table grows. The fallback therefore
returns `None` almost always.

This **restates S6 more accurately**: the defect is not scan cost, it is that the
fallback silently does not work. It is reached only on a `ValidationException` from
the canonical `get_item` and is gated by `COVER_LETTER_LEGACY_READ_ENABLED`
(defaulting to `'true'`).

---

#### N10 — MEDIUM — `jobs-table`'s `user_id-index` is HASH-only, so "newest first" VPR job ordering does not exist

```
GSI user_id-index KeySchema: [{ user_id, HASH }]      <-- no RANGE key
```

```
src/backend/careervp/dal/jobs_repository.py:157-160
    'IndexName': USER_ID_INDEX_NAME,
    'KeyConditionExpression': Key('user_id').eq(user_id),
    'Limit': page_size,
    'ScanIndexForward': False,  # newest first
```

`ScanIndexForward` has no meaning on an index with no range key — there is no sort
order to reverse. The comment `# newest first` is false; items return in internal
order. This makes S5 materially worse: the ≤100-job window that
`core_repository._resolve_vpr_job_id` filters in Python is not "the 100 newest
jobs", it is **100 arbitrary jobs**, and the subsequent
`matching_jobs.sort(key=updated_at)` only orders within that arbitrary window.

---

#### N11 — MEDIUM — `interview_prep` has two coexisting write grammars with different id semantics and different status casing

Two distinct writers key the same artifact type differently:

| | sync/worker `put_item` | submit/status `update_item` |
|---|---|---|
| site | `interview_prep_handler.py:1044-1059` | `interview_prep_handler.py:404-406` |
| id | `interview_prep_artifact_id(prep_id)` | `_normalize_interview_prep_artifact_id(job_id)` |
| id source | `prep_payload['prep_id']` or `prep-<ts>` | the request/job id |
| `status` | `'completed'` (lower) | `'COMPLETED'` (upper) |
| `expiration` | set (730d) | absent |
| `request_data` | absent | present |

Live data splits exactly along that line — 3 rows with `prep_id` + `expiration` +
lowercase `completed`, and 3 rows with `request_data` + no `expiration` + uppercase
`COMPLETED`.

I did **not** find a same-run duplicate pair: each path is internally consistent, so
this is not the "update writes a different key than the create" duplicate the audit
asked me to hunt for. The live defect is the **status-casing split** — any reader
comparing `status == 'completed'` or `status == 'COMPLETED'` without normalising
sees only half the rows. The cancel paths do normalise (`.upper()`); not all
readers were verified.

---

#### N12 — MEDIUM — VPR is dual-homed in two tables under two different grammars, and the plan's session-2 scope omits the users-table copy

| location | partition key | sort key / artifactId | rows |
|---|---|---|---|
| `users-table` | `<applicationId>` (bare) | `ARTIFACT#VPR#v1` | **9** |
| `artifacts-table` | `applicationId` | bare UUID, e.g. `374788f8-…` | **1** |

Note the artifacts-table VPR uses a **bare UUID** `artifactId`, matching *neither*
`VPR_SORT_KEY_PREFIX = 'ARTIFACT#VPR#v'` (declared in `table_registry.py:29`) nor
the `ARTIFACT#<TYPE>#<id>` shape every other artifact type uses. So the artifacts
table runs **three** grammars, not the two S2 claims (see §1b/S2).

The single artifacts-table VPR row was created by this branch's recent
`f5a869e fix(vpr): write the canonical VPR artifact…`; the 9 users-table rows were
not removed. Session 2's stated scope is "move `cv_tailored` and `gap_questions` off
the users table" — it does not mention the 9 `ARTIFACT#VPR#v1` rows that also live
there.

---

#### N13 — MEDIUM — P-24 is not "unstarted": the surrogate code and table exist, but the custom authorizer is not deployed and no Lambda can reach the table

The plan schedules sessions 4-5 for "P-24 identity surrogate (sub → internal
user_id)" and describes it as unstarted. Evidence says otherwise, in both
directions:

*Already built:*
- `src/backend/careervp/dal/identity_map_repository.py` (134 lines)
- `src/backend/careervp/logic/identity_resolver.py` — `get_user_id(sub)`, `link(...)`, `_user_id_factory()`
- `src/backend/careervp/handlers/api_gateway_authorizer.py` — wires both together
- `careervp-identity-map-table-devx` is **deployed**, `KeySchema: [{sub, HASH}]`
- Infra plumbing exists: `constants.IDENTITY_MAP_TABLE_NAME_ENV`,
  `api_construct.py:2473`, `api_db_construct.py:206`

*Not actually live:*
- `careervp-identity-map-table-devx` **ItemCount = 0** — never minted a mapping.
- The API's only authorizer is **`type: COGNITO_USER_POOLS`**. The custom Lambda
  authorizer is **not deployed** — `aws lambda list-functions` matching `author`
  returns nothing.
- **No devx Lambda has `IDENTITY_MAP_TABLE_NAME`** set (checked all 31).

**Blast radius.** Sessions 4-5 are less greenfield than priced, but they carry an
unpriced infra step the plan does not mention: **swapping the authorizer type on a
49-route API from `COGNITO_USER_POOLS` to a custom Lambda authorizer**, which
changes the claims shape every handler's `_extract_authenticated_user_id` reads.
That is a whole-surface change, not a two-session refactor.

---

#### N14 — MEDIUM — The measured 2xx rate is 23.7%, and the two async generate endpoints are at 6% and 12%

Full-window `AWS/ApiGateway`, `careervp-core-api-devx`, OPTIONS excluded:

| resource | method | count | 4xx | 5xx | 2xx |
|---|---|---:|---:|---:|---:|
| /users/me | GET | 500 | 408 | 0 | 18% |
| /users/me/subscription | GET | 396 | 345 | 0 | 13% |
| /users/me/usage | GET | 393 | 342 | 0 | 13% |
| /jobs | GET | 87 | 32 | 0 | 63% |
| /users/me/cv | POST | 86 | 51 | 4 | 36% |
| /jobs | POST | 52 | 27 | 0 | 48% |
| /vpr/generate | POST | 45 | 34 | 0 | 24% |
| **/interview-prep/generate** | POST | 31 | 28 | 1 | **6%** |
| **/cover-letter/generate** | POST | 26 | 23 | 0 | **12%** |
| /cv-tailoring/generate | POST | 21 | 13 | 0 | 38% |
| /company-research/fetch | POST | 19 | 5 | 0 | 74% |
| /users/me/trial/reset | POST | 19 | 0 | 0 | 100% |
| /health | GET | 17 | 0 | 0 | 100% |
| /users/me/cv | GET | 11 | 0 | 0 | 100% |
| /users/me | PUT | 8 | 4 | 0 | 50% |
| /vprs, /interview-preps, /cv-tailorings, /cover-letters | GET | 4 each | 0 | 0 | 100% |
| **TOTAL** | | **1,727** | **1,312** | **5** | **23.7%** |

**Caveat I could not resolve (see §5):** I could not separate security 4xx (401/403
from expired test tokens) from contract 4xx (400/404/409). The three
`/users/me*` GET rows at 13–18% 2xx are very likely dominated by 401s and are
plausibly out of scope for a "non-security" reading. The *generate* rows are the
decision-relevant ones, and 6%/12% 2xx on the two async generators cannot be
explained by auth alone given that both have completed artifacts in the table.

---

#### N15 — MEDIUM — Seven deployed Lambdas have never been invoked; every failure-handling path is among them

Zero `Invocations` datapoints across the full window:

| function | why it matters |
|---|---|
| `ai-assist` | frontend calls it, route deployed (see N3) |
| `artifact-failure-handler` | the artifact failure path has never run |
| `cr-failure-handler` | company-research failure path has never run |
| `vpr-dlq-handler` | the VPR DLQ handler has never run |
| `error-report` | `POST /errors` route deployed, never used |
| `export` | frontend calls it (`methods.ts:320`), never run |
| `vpr-worker` | superseded by `vpr-sqs-worker` (9 invocations) — deployed dead code |

Per the audit's own rule, a function with no metric data is itself a finding.
Notably **every failure/DLQ handler in the system is in this list** — the error
paths session 1 intends to make legible have no execution history whatsoever.

---

#### N16 — MEDIUM — Hebrew is V1 scope and has never been exercised: 52 live `language` values, all `en`

Code support exists — `cv_parser.detect_language() -> Literal['en','he']`
(`cv_parser.py:86`), RTL prompt instructions (`cv_parser.py:230-231`), and
`Literal['en','he']` on `models/job.py:67`, `models/gap_analysis.py:18`,
`models/vpr.py:592`, `models/cv.py:146,275`.

Live data across artifacts/users/applications/jobs tables: **48 `language: 'en'` in
users-table, 4 `language: 'en'` in artifacts-table, zero `'he'` anywhere.**

**Confirms the prompt's suspicion.** Hebrew is declared V1 scope in `CLAUDE.md` and
has never been run end-to-end on devx.

---

#### N17 — MEDIUM — Four synchronous API Lambdas have timeouts longer than API Gateway can wait, so work continues after the client gets a 504

| function | Lambda timeout | gateway ceiling | overhang |
|---|---:|---:|---:|
| `cvtailor` | 120s | 29s | 91s |
| `company-research` | 60s | 29s | 31s |
| `cover-letter-api` | 60s | 29s | 31s |
| `interview-prep-api` | 60s | 29s | 31s |
| `export` | 29s | 29s | 0s |

For any request exceeding 29s the client receives a 504 while the Lambda keeps
running, keeps billing, and **may still complete its DynamoDB write**. That is the
mechanism behind the plan's own gap-analysis observation (200 at 27,965ms, 504 at
29,222ms) and it is currently latent on four more endpoints. A 504 here does not
mean "no artifact was created" — which matters for both idempotency and for any
"did it work?" assertion in session 6's E2E.

---

#### N18 — LOW/MEDIUM — `ai-assist`'s in-process 25s timeout equals its Lambda timeout, so its graceful-timeout path is unreachable

```
src/backend/careervp/handlers/ai_assist_handler.py:50-51
    # One safety margin below the 29 s API Gateway hard ceiling.
    DEFAULT_ASSIST_TIMEOUT_SECONDS = 25
```

The live Lambda timeout for `careervp-ai-assist-lambda-devx` is also **25s**. The
in-process budget and the hard kill therefore expire simultaneously: the handler
cannot reliably catch its own LLM timeout and convert it into a 503/504, because
Lambda terminates it in the same instant. The comment's "safety margin" is real
with respect to API Gateway (25 < 29) and absent with respect to Lambda (25 = 25).
Never exercised (N15), so untested.

---

#### N19 — LOW/MEDIUM — `cover_letter_artifact_id(job_id)` is passed a cover-letter id, not a job id; and 3 of 10 rows carry no application reference at all

`table_registry.cover_letter_artifact_id(job_id: str)` names its parameter
`job_id`, but `cover_letter_submit_handler.py:145` generates
`job_id = str(uuid.uuid4())` — a fresh *cover-letter task* id — and passes that,
while the real application/job id goes into a separate non-key `job_id`
**attribute** (`'job_id': api_request.job_id`, line 161).

Live confirmation: of 10 `cover_letter`/`interview_prep` rows, the sort-key tails
are 9/10 **neither** a `jobs-table` `job_id` **nor** an `applications-table`
`applicationId`. The real application id sits in the body:

```
artifactId = ARTIFACT#COVER_LETTER#51fabb2a-…   <-- a cover_letter_id
pk/applicationId = 848834a8-…                   <-- a Cognito sub
job_id (attribute) = ef2ddfcc-…                 <-- the real application id
```

And **`job_id` is present on only 7 of 10** of those rows.

**Blast radius for session 2.** Repartitioning to `applicationId` needs an
`applicationId` per row. It is available at *write* time (`request_data` carries
`application_id`), so the forward path is fine — but the naming lie is an active
trap for anyone implementing session 2, and for 3 of 10 existing rows there is no
recoverable application id at all. Under the disposability premise that is
acceptable; it is stated here because it means "repartition in place" is *not*
available as a fallback if disposability is ever revisited.

---

#### N20 — LOW — `/knowledge-base` is served by the company-research Lambda; there is no knowledge-base Lambda

`GET /knowledge-base` is deployed and integrates with
`careervp-company-research-lambda-devx:live-devx`. No `knowledge-base` Lambda
exists in devx, though `src/backend/careervp/handlers/knowledge_base_handler.py`
does. Classified in §1c as *no dedicated surface*.

---

#### N21 — LOW — Two DLQs hold undrained messages and nothing watches them

```
careervp-cv-upload-worker-dlq-devx   ApproximateNumberOfMessages: 22
careervp-company-research-dlq-devx   ApproximateNumberOfMessages: 1
```

All other devx queues are at 0. The 22 are N1's stranded CV uploads. No alarm or
handler consumes either DLQ (`vpr-dlq-handler` has never been invoked, N15).

---

### 1b. Confirmations / refutations of S1–S8

| | verdict | evidence |
|---|---|---|
| **S1** | **CONFIRMED** | `_load_tailored_cv`'s own docstring ([`ai_assist_handler.py:447-453`](../../src/backend/careervp/handlers/ai_assist_handler.py#L447-L453)) states the artifact is at `pk=user_id, sk=ARTIFACT#CV_TAILORED#{request_id}` with the application id in the `job_id` *attribute*, so it filters on `job_id`, not the sk. Live: 6 `ARTIFACT#CV_TAILORED#cv-tail-…` rows in users-table, 0 in artifacts-table. Reinforced by N3: ai-assist's `ARTIFACTS_TABLE_NAME` *is* the users table. An artifacts repoint breaks this reader. |
| **S2** | **CONFIRMED, and understated** | Live artifacts-table scan (25 rows): `company_research` + `vpr` partitioned by `applicationId`; `cover_letter` + `interview_prep` partitioned by **Cognito sub** (`848834a8-…`). But there are **three** grammars, not two — VPR's `artifactId` is a bare UUID (`374788f8-…`), matching neither `VPR_SORT_KEY_PREFIX='ARTIFACT#VPR#v'` nor the `ARTIFACT#<TYPE>#<id>` shape. See N12. |
| **S3** | **CONFIRMED** | `read_cover_letter_by_artifact_id(self, application_id: str, artifact_id: str)` — [`dynamo_dal_handler.py:595-599`](../../src/backend/careervp/dal/dynamo_dal_handler.py#L595-L599) — takes **no `user_id`**. Today `application_id` *is* the user's sub for cover letters (S2), so the partition key accidentally enforces tenancy. Normalising S2 without adding an ownership check converts this into a cross-tenant read. This is the strongest argument in the plan and it holds. |
| **S4** | **CONFIRMED exactly** | users-table `CV#` ids: 31. cvs-table `cvId`s: 28. In **both: 28**. users-only: 3. cvs-only: 0. Union 31. The prior session's "28 of 31" is precisely right. |
| **S5** | **CONFIRMED in substance; one stated detail wrong; worse than described** | Wrong detail: the signature default is `limit: int = 20`, not 100 ([`jobs_repository.py:140`](../../src/backend/careervp/dal/jobs_repository.py#L140)); the `limit=100` comes from the *call site* [`core_repository.py:128`](../../src/backend/careervp/dal/core_repository.py#L128). Also the "first page dominated" bug the prior session described has **already been fixed** — the method now paginates and accumulates. What remains and confirms S5: `safe_limit = max(1, min(limit, 100))` is a hard 100-row cap, and `_resolve_vpr_job_id` filters by `application_id` **in Python** afterwards. Worse: N10 shows the index is HASH-only, so the 100 rows are arbitrary, not newest. |
| **S6** | **REFUTED as framed; RESTATED** | The scan exists ([`dynamo_dal_handler.py:796`](../../src/backend/careervp/dal/dynamo_dal_handler.py#L796)) and `type-index` **is** `ProjectionType: ALL` (confirmed). But the defect is not scan cost — it is `Limit=1` combined with a `FilterExpression`, which evaluates one arbitrary item and filters it, so the fallback almost never returns the row. See N9. It is also gated (`COVER_LETTER_LEGACY_READ_ENABLED`) and only reached after a `ValidationException`. |
| **S7** | **CONFIRMED** | cr-cache key is `cacheKey` HASH with values like `COMPANY#example.com#news` — keyed by company, shared across all users, no tenant scoping. Hot key: sub `848834a8-…` holds **10 of 25 (40%)** artifacts rows in one partition. TTL: only 3 of 25 artifact rows have `expiration`; see N7 for the three-attribute-name mess. |
| **S8** | **CONFIRMED, with a material restatement** | Cognito sub used directly as `user_id` — the API's only authorizer is `COGNITO_USER_POOLS`, and live partition keys are raw subs (`848834a8-4061-703d-419c-0294d4e88d66`). `_owner_id` tolerates both spellings: `str(item.get('user_id') or item.get('userId') or '').strip()` ([`core_repository.py:316-317`](../../src/backend/careervp/dal/core_repository.py#L316-L317)). **Restatement:** P-24 is not "unstarted" — the resolver, repository, authorizer handler and the deployed (empty) table all exist; what's missing is deployment. See N13. |

**What the prior session missed.** It audited one table and found eight problems; the
list was indeed incomplete. The eight findings are all about *data layout*. Every
one of N1, N2, N5, N6, N13, N15, N16 is a **liveness** defect — a path that has
never run, or runs and does nothing — and none of those are visible from a table
scan. The most consequential omissions are N1 (a 100%-failing worker at the head of
the journey) and N3 (an env var that already contradicts session 2's third
deliverable, documented in the repo's own key-authority docstring).

### 1c. Investigation 3 — what has ever run on devx

| V1 feature (CLAUDE.md) | verdict | evidence |
|---|---|---|
| Auth | **exercised** | auth-api 206 invocations, 4 errors; 202 succeeded |
| VPR | **exercised** | vpr-submit 26, vpr-sqs-worker 9 (avg 96.7s), vpr-status 155; 1 canonical artifact + 9 users-table rows |
| CV Tailoring | **exercised (sync only)** | cvtailor 37 invocations, 0 errors, p99 14,120ms; 6 `CV_TAILORED` rows. The **stream** worker no-ops (N6) |
| Cover Letter | **exercised** | cover-letter-worker 6, api 17; 4 completed artifacts. But only 12% of `generate` calls 2xx (N14) |
| Gap Analysis | **exercised, at/over the ceiling** | gap-api 40 invocations, 0 Lambda errors, **p95 29,140ms** (N2); 9 `GAP_ANALYSIS` rows |
| Interview Prep | **exercised** | worker 4 (avg 75.5s), api 23; 6 artifacts. Only 6% of `generate` calls 2xx (N14) |
| Company Research | **exercised** | worker 14, api 24; 13 artifacts — the healthiest path (74% 2xx) |
| Knowledge Base | **no dedicated surface** | `GET /knowledge-base` routes to `company-research-lambda`; no knowledge-base Lambda; `knowledge-table` deployed. Cannot attribute any invocation to it |
| English | **exercised** | 52 live `language: 'en'` values |
| **Hebrew** | **NEVER exercised** | zero `'he'` in live data (N16) |
| Export | **never exercised** | `export-lambda` 0 invocations; frontend calls it (`methods.ts:320`); route deployed |
| Billing | **exercised** | billing-lambda 51 invocations, 0 errors |
| Reconciliation | **exercised but vacuous** | billing-reconcile 12 invocations, **6 errors (50%)**; successful runs log `{'checked': 0, 'updated': 0, 'errors': 0}` — nothing to reconcile |
| Webhooks | **no-such-surface exercised** | `POST /billing/webhook` deployed; no invocation attributable; no Stripe traffic on devx |
| CV upload (async) | **NEVER succeeded** | 66/66 failures, 22 in DLQ (N1) |
| AI-Assist | **never exercised** | 0 invocations (N3/N15) |
| Error reporting | **never exercised** | `error-report` 0 invocations |

### 1d. Investigation 6 — does session 2 actually work?

Enumerated readers of `cover_letter` / `interview_prep` artifacts, and whether each
still resolves after the partition key changes from `user_id` → `applicationId`:

| reader | resolves after repartition? |
|---|---|
| `cover_letter_submit_handler.py:155` (create) | **yes** — writes both key shapes; `request_data.application_id` available |
| `cover_letter_handler.py:704-713` (worker status update) | **yes** — via `table_registry`, follows the authority |
| `cover_letter_handler.py:1441,1453` (**cancel**) | **NO** — hardcodes `applicationId = user_id` (N8) |
| `interview_prep_handler.py:406` (status update) | **NO** — hardcodes `applicationId = user_id` (N8) |
| `interview_prep_handler.py:1265-1286` (**cancel**) | **NO** — same inline pattern (N8) |
| `cover_letter_handler.py:1470-1530` (PATCH) | **yes, conditionally** — key-adaptive (`if 'applicationId' in item`), but depends on `_find_cover_letter_item` locating the row first |
| `interview_prep_handler.py:1405-1425` (PATCH) | **yes, conditionally** — same |
| `dynamo_dal_handler.py:595` `read_cover_letter_by_artifact_id` | **yes mechanically, NO for tenancy** — takes no `user_id`; becomes a cross-tenant read (S3) |
| `dynamo_dal_handler.py:778-800` legacy fallback | **already broken** (N9) |
| `cover-letter-status` / `interview-prep-status` Lambdas | **unverified** — not traced; both have `DYNAMODB_TABLE_NAME=artifacts-table` |
| **`cv-tailor-worker` DynamoDB stream** | **unenumerated by the plan** — consumes every artifacts write; `Keys` payload shape changes (N6) |
| frontend `PATCH /cover-letter/{artifactId}` etc. | **yes** — passes an opaque id; no key shape in the client |
| hub projection (`adapters/mapApplicationDataToHubState.ts`) | **unverified** — reads `GET /applications/{id}` server-side projection |

**Answer: session 2's premise is sound but its scope is incomplete.** Disposability
does remove the need for migration/backfill/dual-read — no reader needs to resolve
*old* rows. But **at least three readers cannot resolve even newly-written rows**
after the change (N8), because they hardcode `applicationId = user_id` outside the
key authority. Plus one unenumerated stream consumer (N6) and one TTL landmine (N7).

### 1e. Investigation 5 — the frontend, currently priced at zero

19 files reference `applicationId` / `artifactId` / `application_id` (156
occurrences). Endpoint surface from [`src/frontend/api/methods.ts`](../../src/frontend/api/methods.ts):

Pages: `app/applications/[id]/{vpr,cv-tailored,cover-letter,interview-prep,gap-analysis}/page.tsx`
Shared: `api/methods.ts`, `api/queryKeys.ts`, `lib/types.ts`, `lib/contractOracle.ts`,
`lib/contractSchemas.ts`, `hooks/useApplicationHub.ts`, `hooks/useArtifactAutosave.ts`,
`hooks/useGenerateModule.ts`, `types/hub-state.ts`,
`components/{ArtifactAutosaveField,ExportDropdown,TailoredCVsListTable,CoverLettersListTable,GapQuestionCard}`.

**Good news — session 2 (key changes) is close to free on the frontend.** Every
artifact call passes an **opaque id** in a path segment
(`/cover-letter/${artifactId}/status`, `PATCH /cover-letter/${artifactId}`). No
client code constructs `ARTIFACT#…`, reads a `pk`/`sk`, or composes a composite key.
I found no string-literal key grammar in the client.

**Real, unpriced frontend work:**
1. **Session 3 (Gap → async) is a genuine frontend change.** Gap is currently
   *synchronous*: `getGapQuestions` does `GET /jobs/${jobId}/gap-questions` returning
   `{questions}`, and `generateGapAnalysis` does `POST /gap-analysis/questions`
   returning `GapAnalysisResponse` — a **result**, not an `AsyncTaskResponse`. Every
   other generator returns `AsyncTaskResponse` and is polled via a `…/status`
   endpoint. Session 3 must add a gap status endpoint, a polling hook, and a pending
   state to `gap-analysis/page.tsx` + `GapQuestionCard` + `useGenerateModule`.
   `lib/contractSchemas.ts` / `contractOracle.ts` also encode the current
   synchronous contract.
2. **Sessions 4-5 (identity surrogate)** change the authorizer type (N13), which
   changes token/claims handling in `middleware.ts` and `contexts`/`auth` — not
   costed.
3. **No DELETE exists client-side** (N4), so any session-1 "ownership" work has no
   UI counterpart to verify against.

**Quantification:** ~2 files for session 2 (nil-to-trivial), **~6-8 files for
session 3**, plus contract-schema and test updates. The plan's zero is right for
session 2 and wrong for session 3.

---

## 2. CONFIDENCE VERDICT

| # | claim | plan | verdict | my number |
|---|---|---:|---|---:|
| 1 | data architecture correct going forward | 85% | **TOO HIGH** | **60%** |
| 2 | all 6 artifacts write/read correct location | 85% | **TOO HIGH** | **55%** |
| 3 | Create + Read work for every artifact | 80% | **TOO HIGH** | **60%** |
| 4 | Update + Delete work — full CRUD | 40% | **CATEGORY ERROR — far too high** | **5%** |
| 5 | every call returns 2xx (non-security) | 25% | **ABOUT RIGHT** | **20%** |
| 6 | one user completes one journey | 65% | **TOO HIGH** | **35%** |

**1 — 85% → 60%, TOO HIGH.** The target grammar is right, but three things the plan
does not account for sit inside "going forward": the `ARTIFACTS_TABLE_NAME` inversion
on ai-assist (N3), which the repo's own key-authority docstring says must not be
collapsed; live TTL on the destination table under a third attribute name (N7); and
an unfiltered stream consumer on the artifacts table (N6). Also the artifacts table
runs three grammars, not two (N12), so "one grammar" has one more case to collapse
than the plan states.

**2 — 85% → 55%, TOO HIGH.** Correct *location* is not the binding constraint;
correct *key within* the location is. Three write/read sites hardcode
`applicationId = user_id` outside the key authority (N8) and will target a
non-existent partition after session 2, and the static D-H2 test that is supposed to
prevent exactly this does not catch them. Add the interview_prep two-grammar/two-casing
split (N11) and the VPR bare-UUID `artifactId` (N12).

**3 — 80% → 60%, TOO HIGH.** Create+Read is the best-evidenced part of the system,
but "for every artifact" fails today: the CV-upload async create path is 0-for-66
(N1), and `/interview-prep/generate` and `/cover-letter/generate` return 2xx on 6%
and 12% of calls (N14). Company research (74% 2xx) and the four list endpoints (100%)
are genuinely healthy.

**4 — 40% → 5%. This is a category error, not a calibration error.** 40% reads as
"Update+Delete probably has bugs". The evidence is that **Delete does not exist**:
one DELETE route in a 49-route API, no artifact-type DynamoDB reaper (the reaper
deletes S3 objects only, and is a no-op anyway — N5), no frontend DELETE call at all
(N4). Update is in better shape than Delete — PATCH exists for 3 of 6 types and the
PATCH key-resolution is adaptive — but 5 of 6 types have no delete path. The honest
statement is not a probability, it is: *Delete is unimplemented for 5 of 6 artifact
types; the question of whether it "works" is not yet meaningful.* This is the row the
plan flagged as least examined, and it deserved that flag.

**5 — 25% → 20%, ABOUT RIGHT.** The measured aggregate non-OPTIONS 2xx rate is
**23.7%** (1,727 calls, 1,312 4xx, 5 5xx). Landing at 25% for this is well
calibrated — the closest of the six. I nudge down only because the number I can
measure is a *rate* while the claim is *"every call"*, and because two of the
generate endpoints (6%, 12%) are worse than the aggregate. Caveat in §5: I could not
split 401-security 4xx from contract 4xx, and the three high-volume `/users/me*` GET
rows are likely auth-dominated and arguably excluded by the "non-security" carve-out.

**6 — 65% → 35%, TOO HIGH.** Two independent blockers the plan does not address.
(a) The journey starts with a CV upload whose async worker has never succeeded and
has 22 messages in a DLQ (N1) — whether the journey can complete depends on whether
the sync `cv-parser` path (39 invocations, 0 errors) fully substitutes for the S3
worker, which I could not establish (§5). (b) Gap analysis sits at p95 29,140ms
(N2), so a mid-journey 504 is the >5% case, not the tail. Session 6 also assumes
Hebrew is out of the E2E, but Hebrew is declared V1 scope and has never run (N16).

---

## 3. PLAN VERDICT

| session | verdict | reasoning |
|---|---|---|
| 0. This audit | **KEEP** | It changed six numbers and found N1, which no table scan would have surfaced. |
| 1. Legible failures + ownership | **KEEP — strengthen** | Best-justified session in the plan. N5 is the archetype: a reaper returning `{'status':'ok','cleaned':0}` for a total config failure, 57 times. Add: (a) **fail-fast on missing table env vars** — this single check catches N5 and would have caught N3; (b) `user_id` required in `read_cover_letter_by_artifact_id` (S3) **must land before** session 2, not alongside it. |
| 2. One grammar, one home, one env var | **SPLIT — 3 sessions** | The three deliverables have different risk and different prerequisites. **2a Repartition** `cover_letter`/`interview_prep` — must also fix the three hardcoded `applicationId = user_id` sites (N8) and re-point the `cv-tailor-worker` stream (N6). **2b Re-home** `cv_tailored`/`gap_questions` — must include the 9 `ARTIFACT#VPR#v1` users-table rows the plan omits (N12) and must handle the artifacts-table `expiration` TTL (N7). **2c Env collapse — DEFER to last.** `table_registry.py:12-15` documents why collapsing is unsafe, and N3 proves it live. It is only safe *after* 2b re-homes the data ai-assist reads, and ai-assist has zero invocations, so nothing will catch a mistake. |
| 3. Gap Analysis → async (F-DEVX-5) | **KEEP — PROMOTE to first implementation session** | N2 reclassifies this from hardening to repair: p95 **29,140ms**, already past the ceiling. It is also the only session with real, unpriced frontend work (§1e) — gap is the one generator with a synchronous contract. |
| 4-5. P-24 identity surrogate | **MODIFY — re-scope** | Not unstarted (N13): resolver, repository, authorizer handler and table all exist; the table is empty and the custom authorizer is undeployed. Re-scope from "build" to "deploy + cut over", and **add the unpriced step**: swapping a 49-route API from `COGNITO_USER_POOLS` to a custom Lambda authorizer, which changes the claims shape every handler reads. |
| 6. E2E + delete legacy rows | **MODIFY** | Cannot pass as written while N1 stands — a real-CV E2E begins with a CV upload whose async worker is 0-for-66. Sequence N1's fix before it. "Delete legacy rows" also has no tooling: there is no DynamoDB reaper (N4/N5), so this is a manual step needing an explicit, reviewed script. |

### MISSING sessions

1. **MISSING-A (blocks session 6): fix the CV-upload S3 worker.** N1. Branch on
   `Records`/`eventSource` as `interview_prep_handler.py:79-83` already does, add the
   first S3-event test fixture in the repo (currently **zero**), and drain the
   22-message DLQ. Small, and it gates the journey.
2. **MISSING-B (belongs in session 1): a deployed-surface liveness gate.** Seven
   Lambdas have never been invoked and every failure/DLQ handler is among them (N15).
   Session 1 makes failures legible in *code*; nothing in the plan establishes that
   the failure handlers **run**. An untested error path is not a legible one.
3. **MISSING-C: decide Delete.** The plan treats CRUD as one deliverable, but Delete
   is absent for 5 of 6 types (N4) — a scope decision (implement, or explicitly
   defer to V2), not a bug fix. It should be an explicit decision, not a 40%.
4. **MISSING-D (optional, cheap): TTL/attribute-name reconciliation.** Three TTL
   attribute names, one live TTL on session 2's destination table (N7).

### Is any surface where the target grammar cannot be applied?

**Yes — one.** `company_research`'s cache table is keyed `cacheKey =
COMPANY#<domain>#<facet>`, deliberately **shared across users** for cost reasons
(the 91% margin target in `CLAUDE.md`). It cannot be application-partitioned without
destroying the cache-hit economics. The target grammar applies to the
company-research *artifact* (already `applicationId`-partitioned) but must **not** be
applied to the cache. The plan should state this exception explicitly, or session 2's
"one grammar" will be read as covering it.

### Cheaper ordering

Current order is 1 → 2 → 3. Evidence supports **1 → 3 → 2a → 2b → 6 → 4/5 → 2c**,
with MISSING-A before 6:

- Session 1 before 2 **is** justified, and more strongly than the plan argues — but
  the reason is S3/tenancy, not legibility. `read_cover_letter_by_artifact_id` takes
  no `user_id` and is protected today only by S2's accidental user-partitioning.
  Session 2 removes that protection. **Ownership must land first or session 2 opens a
  cross-tenant read.** That is a correctness ordering constraint, not a preference.
- Session 3 should move ahead of 2 because gap is *already failing* (N2) while the
  key grammar is merely *wrong*. Wrong-but-working outranks broken.
- Session 2c (env collapse) should be last: it is the one deliverable with in-repo
  documentation saying it is unsafe (N3), and it is safe only once the data has moved.

---

## 4. THE THREE THINGS MOST LIKELY TO MAKE THE PLAN FAIL

**1. The plan reasons about data layout; the system's live failures are liveness
failures.** All eight prior findings and all three session-2 deliverables concern
where bytes sit. But the CV-upload worker is 0-for-66 (N1), the cleanup reaper is a
57-times no-op that reports success (N5), the artifacts-table stream consumer no-ops
on every write (N6), and seven Lambdas — **including every failure and DLQ
handler** — have never run at all (N15). None of that is visible from a table scan,
and none of it is fixed by moving keys. A plan that lands all seven sessions
perfectly still leaves a system whose first journey step has never worked.

**2. "Disposable data" is true and is being over-applied.** Disposability correctly
removes migration, backfill, dual-read and shims — that part of the premise survives
contact with evidence. But it says nothing about **code that cannot address the new
grammar**, and the plan appears to treat the two as one. Three sites hardcode
`applicationId = user_id` in raw dicts outside the key authority (N8); they break on
*newly written* rows, where disposability offers no protection. Worse, the static
test that exists to prevent this (`test_dh2_dh3_key_authority.py`) does not catch
them, so the guardrail will report green. Add the unenumerated stream consumer (N6)
and the live TTL on the destination table (N7).

**3. The sequencing risk is concentrated in a change with no observability.** Session
2's env collapse touches `ai-assist`, whose `ARTIFACTS_TABLE_NAME` points at the
**users** table and whose `COMPANY_RESEARCH_TABLE_NAME` points at the **artifacts**
table (N3) — an inversion the repo's own key-authority docstring documents as
load-bearing. ai-assist has **zero invocations**, no test that would catch a mis-set
env var, and a self-timeout equal to its Lambda timeout so its error path cannot
even run (N18). This is the highest-blast-radius edit in the plan attached to the
least-instrumented Lambda in the account. The prior session was "wrong twice in ways
it only discovered by deploying" — this is the most likely place for a third.

---

## 5. WHAT I COULD NOT DETERMINE

| question | why | what would settle it |
|---|---|---|
| **Split of 4xx into security (401/403) vs contract (400/404/409)** | API Gateway access logging is not enabled on the devx stage; the Lambdas log no `statusCode` field (a `filter-log-events` pass for `statusCode` across interview-prep-api, cover-letter-api, vpr-submit, cv-upload-worker returned no matches). This is the main caveat on confidence #5. | Enable access logging with `$context.status` on the devx stage, or add a `status_code` key to the Powertools logger. Read-only alternative: X-Ray traces, if sampling captured any. |
| **Whether the journey can complete despite N1** — i.e. does the sync `cv-parser` path (39 invocations, 0 errors) fully substitute for the dead S3 worker, or is some post-processing permanently missing? | Determining it needs either a real CV upload (a mutating POST that consumes trial credit — excluded) or a trace of one successful end-to-end run, and there is none. Directly gates confidence #6. | Read the 22 DLQ messages **without deleting** (`sqs receive-message` with `VisibilityTimeout=0`) to see what work was dropped; or one supervised upload on a throwaway devx account. |
| **Whether `cover-letter-status` / `interview-prep-status` Lambdas survive session 2** | Not traced — I ran out of surface before reading them. Both have `DYNAMODB_TABLE_NAME=artifacts-table`, so they are plausible additional instances of N8. | Read `cover_letter_status`/`interview_prep_status` handlers for inline `{'applicationId': user_id}` construction. Pure code read — no access needed. |
| **Whether the hub projection (`GET /applications/{id}`) resolves cover_letter/interview_prep after repartition** | `adapters/mapApplicationDataToHubState.ts` consumes a server-side projection I did not trace to its DAL source. | Trace `application_handler` → `application_repository.py:324-387` (`artifact_statuses.#at_id`) and confirm which key it resolves artifact ids through. Pure code read. |
| **Whether `_find_cover_letter_item` locates rows post-repartition** | The PATCH key handling is adaptive and safe, but it depends on this lookup, which I did not read. | Code read of `_find_cover_letter_item`. |
| **Why `/interview-prep/generate` is 6% 2xx yet 6 completed artifacts exist** | The 4xx codes are unavailable (row 1). Possibly 409 `UpstreamMissingError`, possibly 401. | Same fix as row 1. |
| **Whether any *other* Lambda shares N1's shape** (non-HTTP trigger + API-only handler) | I checked cv-upload (broken), cv-tailor (stream, no-ops), interview-prep (correct `Records` branch), artifact-cleanup (EventBridge, handled). Two never-invoked handlers — `artifact-failure-handler`, `cr-failure-handler` — were not verified, and being never-invoked, an N1-shaped bug in them would be invisible. | Read both handlers for a `Records`/`eventSource` branch; or a controlled synthetic invoke (a **mutating** action — not taken, needs approval). |

### Unit-test baseline

`cd src/backend && uv run pytest tests/unit/ -q` — **baseline confirmed exactly as
stated: `1419 passed, 15 skipped, 4 xfailed, 118 warnings in 77.46s`.**

**No source file was modified in this session.** `git status --porcelain` shows only
the seven pre-existing uncommitted paths listed in the task brief (`CLAUDE.md`,
`PROGRESS.md`, `wave-3-status.md`, `plan.md`, `cv_upload_handler.py`,
`test_async_submit_handlers.py`, `test_cv_upload_handler.py`) — unchanged by this
audit. The only file this session created is this evidence document.

Note that the suite passes at 1419 green **while** the CV-upload S3 worker is
0-for-66 in production (N1), the cleanup reaper is a 57-times no-op (N5), and the
artifacts-table stream consumer no-ops on every write (N6). A green unit suite is
currently uninformative about liveness — which is the substance of §4.1. Relevant
here:
**zero test files in `src/backend/tests/` contain an S3 event fixture**
(`grep -rl "aws:s3\|s3:ObjectCreated"` → 0), which is why N1 is invisible to the suite.

---

## Appendix — commands used

All read-only. AWS calls limited to `describe`/`list`/`get`/`scan`/`query` plus
CloudWatch metrics and logs.

```bash
aws sts get-caller-identity
aws dynamodb list-tables --region us-east-1
aws dynamodb describe-table --table-name careervp-<t>-devx
aws dynamodb describe-time-to-live --table-name careervp-<t>-devx
aws dynamodb scan --table-name careervp-{artifacts,users,cvs,applications,jobs,identity-map}-table-devx
aws lambda list-functions / get-function-configuration / get-policy / list-event-source-mappings
aws cloudwatch get-metric-statistics --namespace AWS/Lambda   --metric-name Duration|Invocations|Errors \
    --statistics Average Maximum SampleCount --extended-statistics p95 p99
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway --metric-name Count|4XXError|5XXError|Latency
aws cloudwatch list-metrics --namespace AWS/ApiGateway
aws apigateway get-rest-apis / get-resources / get-integration / get-authorizers
aws logs tail | filter-log-events
aws sqs list-queues / get-queue-attributes
```

Not done, per the brief: no file edited, no deploy, no `make deploy-devx`, no
DynamoDB/S3 write, no artifact-creating or credit-consuming POST, no live or e2e
suite, no commit, no authentication.
