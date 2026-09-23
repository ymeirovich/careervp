# Wave-3 Pre-Plan Audit — remediation steps

- **Date:** 2026-08-04
- **Companion to:** [`wave3-preplan-audit-20260804.md`](./wave3-preplan-audit-20260804.md) (findings N1–N21, S1–S8)
- **Status:** proposal. Nothing here has been applied. No file was changed to produce it.

Finding IDs (`N1`, `S3`, …) refer to the audit document. Each fix below states
**what to change → how to verify → what it risks**.

---

## Ordering, and why

Three hard constraints fix most of the order; everything else is preference.

1. **Ownership before repartition.** `read_cover_letter_by_artifact_id` takes no
   `user_id` (S3); tenancy currently rests on cover letters being *accidentally*
   partitioned by Cognito sub (S2). Session 2 removes that accident. If ownership
   does not land first, session 2 **opens a cross-tenant read**. This is a
   correctness constraint, not sequencing taste.
2. **Guardrails before the change they guard.** The regex fix in P0.1 is what makes
   the session-2 work safe to do at all. Doing it after is doing it for nothing.
3. **Env collapse last.** `table_registry.py:12-15` documents why collapsing is
   unsafe, and N3 proves it live. It is safe only *after* the data ai-assist reads
   has moved.

Recommended sequence:

```
P0  guardrails + fail-fast        (0.5 day, no behaviour change)
P1  delete dead wiring            (1 day, pure subtraction)
P2  the 29s ceiling               (2-3 days, user-visible today)
P3  ownership + delete policy     (2 days)  <-- gates P4
P4  repartition, split in three   (4-6 days)
P5  identity surrogate            (re-scoped)
P6  E2E
```

P1 and P2 are independent of P3/P4 and can run in parallel with them.

---

## P0 — Two changes to make first (half a day, no behaviour change)

### P0.1 — Close the guardrail hole that lets N8 through

This is the highest-leverage change in the whole plan: one regex, and it converts
N8 from "three sites someone must remember" into "CI fails".

**Why it currently passes.** The ratchet greps for `USER#` literals and for
`'pk':`/`'sk':`, i.e. the **legacy** grammar. The **canonical** grammar's own key
names are unguarded:

```python
# src/backend/tests/unit/test_dh2_dh3_key_authority.py:191-197
_ARTIFACT_KEY_BUILD_PATTERN = re.compile(
    r"""(?x)
    (?:['"](?:pk|sk)['"]\s*:)                                  # <-- legacy only
    |(?:Key\(\s*['"](?:pk|sk)['"]\s*\))
    |(?:(?:=|:|return)\s*f?['"](?:ARTIFACT|COMPANY_RESEARCH)\#)
    """
)
```

N8's three sites contain neither `USER#` nor `'pk'`/`'sk'` — they use a bare sub as
`applicationId`, so nothing matches:

```python
# cover_letter_handler.py:1441
get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
# interview_prep_handler.py:406
'Key': {'applicationId': user_id, 'artifactId': artifact_id},
```

**Change.** Add the canonical key names to the alternation:

```python
    (?:['"](?:pk|sk|applicationId|artifactId)['"]\s*:)
    |(?:Key\(\s*['"](?:pk|sk|applicationId|artifactId)['"]\s*\))
```

**Verify.** `uv run pytest tests/unit/test_dh2_dh3_key_authority.py -v` must now
**fail**, naming the three N8 sites plus `cover_letter_handler.py:1453` (the
`KeyConditionExpression='applicationId = :uid …'` string form — add a fourth
alternation branch for `applicationId\s*=\s*:` if you want that one caught too).
A failing test here is the deliverable. Then either fix the sites (P4.1) or add them
to an explicit, dated baseline set with a removal owner — the same ratchet pattern
the file already uses for `USER#`.

**Risk.** May surface legitimate sites in `core_repository`/`table_registry`; those
roots are already excluded by `_HANDLERS_ROOT`/`_LOGIC_ROOT` scoping. Low.

### P0.2 — Fail fast on a missing table env var

One check that catches N5 and would have caught N3.

**Change.** In `table_registry.py`, `resolve_artifacts_table_name(required=True)`
already raises. The gap is the callers that tolerate empty. Make the *worker/handler
bootstrap* raise rather than degrade:

```python
# artifact_cleanup_handler.py:130-136 — currently degrades to a silent no-op
jobs_table = os.environ.get('DYNAMODB_TABLE_NAME', '')
...
jobs_repo=JobsRepository(jobs_table) if jobs_table else None
```

becomes an explicit raise (or, minimally, `return {'status': 'error', ...}` with a
non-2xx-equivalent and a `metrics.add_metric(name='MissingEnvError')`). The rule to
adopt: **a handler that cannot reach its table must fail loudly, never return a
success shape.**

**Verify.** Unit test that constructs the handler with the env var unset and asserts
it raises / returns an error code — not `{'status': 'ok'}`.

**Risk.** Turns a silent no-op into a visible alarm on any Lambda with a missing
var. That is the point, but expect noise on first deploy; audit env vars across all
31 Lambdas (the table in the audit appendix) before enabling.

---

## P1 — Delete dead wiring (1 day, pure subtraction)

### P1.1 — N1: delete the CV-upload S3 worker; do **not** add a `Records` branch

**This is a correction to my own first instinct in the audit.** I initially framed
the fix as "branch on `Records` like `interview_prep_handler.py:79-83` does". Reading
the synchronous route changes the answer:

```python
# cv_upload_handler.py:129-138   uploads to S3
# cv_upload_handler.py:154       parse_cv(...)          <-- the LLM parse
# cv_upload_handler.py:196-207   persists to CVS_TABLE_NAME
#   "Also persist to the dedicated CVs table so AI Assist and other services
#    that query CVS_TABLE_NAME can find the CV without depending on the async
#    S3-triggered worker (which may not be reachable when text_content is used)."
```

Three consequences:

1. **The sync path is already complete and authoritative.** Someone previously hit
   the dead worker and wrote around it — that comment *is* the workaround. This also
   answers an open question from the audit's §5: yes, the sync path fully
   substitutes.
2. **There is no correct S3 branch to restore.** `cv_upload_handler` contains no code
   that reads an S3 object. The worker's intended behaviour was never implemented —
   it is not misrouted, it is absent. "Fixing" it means building a feature.
3. **A naive `Records` branch would be actively harmful**: it would re-run `parse_cv`
   (an LLM call) and re-persist what the sync path just wrote — duplicate LLM spend
   against the 91% margin target, and duplicate rows.

**Change.**
- Remove `_add_cv_upload_worker_lambda` and its call site
  ([`infra/careervp/api_construct.py:247-257,1834+`](../../infra/careervp/api_construct.py#L1834)).
- Remove the S3 → Lambda notification on the CV bucket.
- Keep the DLQ resource until drained (P1.4), then remove.
- Leave `cv_upload_handler.py` alone. It is correct as an API handler.

**Verify.** `cd infra && cdk synth` clean; `validate_naming.py --path infra --strict`;
confirm no remaining S3 notification targets the removed function; the 66-error
metric stops accruing.

**Risk.** Low, and it is the *reversible* direction — you are deleting a component
that has never once succeeded. If async CV parsing is genuinely wanted later, build
it deliberately (see P2.4).

### P1.2 — N6: remove or filter the artifacts-table stream mapping

`cv-tailor-worker` consumes **every** artifacts-table write (`FilterCriteria: null`,
`BatchSize: 1`) into the CV-tailoring *API* handler, which falls through every route
branch and returns in 3ms. 24 invocations, 0 errors, zero effect.

**Change — pick one, deliberately:**
- **(a) Delete the event-source mapping** if nothing is meant to react to artifact
  writes. Recommended: it is what the evidence supports.
- **(b) If a reaction *is* intended**, it needs a real handler plus
  `FilterCriteria` on `artifactType` — and it must be written *after* P4, because
  the stream's `Keys` payload changes shape when the partition key changes.

Do not leave it as-is: it is a live consumer that will silently start seeing a
different key shape mid-migration.

**Verify.** `aws lambda list-event-source-mappings --function-name
careervp-cv-tailor-worker-lambda-devx` returns `[]` (option a), or shows non-null
`FilterCriteria` (option b).

### P1.3 — N15: delete the superseded `vpr-worker`

`careervp-vpr-worker-lambda-devx` has zero invocations; `vpr-sqs-worker` (9
invocations) does the work. Deployed dead code that still holds IAM grants and
table env vars. Remove from infra.

**Do not** delete the other never-invoked Lambdas — `artifact-failure-handler`,
`cr-failure-handler`, `vpr-dlq-handler`, `error-report`, `export`, `ai-assist` are
never-invoked because they are *unexercised*, not because they are redundant. Those
are P2.5.

### P1.4 — N21: drain the two DLQs, reading before deleting

```
careervp-cv-upload-worker-dlq-devx   22 messages
careervp-company-research-dlq-devx    1 message
```

**Read them first** — `receive-message --visibility-timeout 0` is non-destructive and
tells you what work was dropped, which also confirms P1.1's reasoning. Only then
purge. Deleting before reading throws away the only record of 22 dropped uploads.

**Then add the missing alarm:** a CloudWatch alarm on
`ApproximateNumberOfMessagesVisible > 0` for every DLQ. Nothing watches them today,
which is why 22 messages sat unnoticed.

---

## P2 — The 29s ceiling (2-3 days; user-visible today)

### P2.1 — N2: Gap Analysis → async (this is the plan's session 3, promoted)

p95 **29,140ms** against a 29,000ms ceiling: >5% of gap calls 504 **now**. Treat as
a repair, not hardening.

**Backend change** — follow the existing, working shape rather than inventing one.
The four other generators all use it: `vpr_submit_handler.py` /
`cover_letter_submit_handler.py` are the templates.
1. `POST /gap-analysis/questions` returns `202` + `AsyncTaskResponse` (a task id),
   enqueues to `careervp-gap-analysis-queue-devx` (**already deployed, currently
   idle**), and returns immediately.
2. Add a gap worker Lambda consuming that queue — and give it an SQS `Records`
   branch (`interview_prep_handler.py:79-83` is the correct pattern; N1 is what
   happens when it is omitted).
3. Add `GET /gap-analysis/{id}/status`, mirroring
   `/cover-letter/{id}/status`.
4. Write the PENDING row on submit and update it in the worker **through
   `table_registry`**, not inline dicts (that is N8's mistake).

**Frontend change — this is the plan's one genuinely unpriced frontend cost
(~6-8 files).** Gap is currently the only *synchronous* generator:

```ts
// src/frontend/api/methods.ts:151  — returns a RESULT, not an AsyncTaskResponse
generateGapAnalysis: (data) =>
  apiClient.post<GapAnalysisResponse>('/gap-analysis/questions', data)
// :144 — GET returns {questions} directly
getGapQuestions: (jobId) => apiClient.get<{questions: RawGapQuestion[]}>(...)
```

Every other generator returns `AsyncTaskResponse` and is polled. Work needed:
`api/methods.ts` (return type + a `getGapStatus`), `api/queryKeys.ts`,
`hooks/useGenerateModule.ts` (polling), `app/applications/[id]/gap-analysis/page.tsx`
(pending/failed states), `components/GapQuestionCard`, and **`lib/contractSchemas.ts`
+ `lib/contractOracle.ts`**, which encode the current synchronous contract and will
fail until updated.

**Verify.** `gap-api` p99 drops under ~3,000ms (submit-only). Worker duration is then
bounded by its own 300s timeout, not the gateway. Frontend: `npm run typecheck &&
npm run test:unit && npm run test:integration`.

**Risk.** Medium — it is a contract change on a route the frontend actively uses.
It is also the change most likely to be worth doing first, because the endpoint is
already failing.

### P2.2 — N17: lower the four sync Lambda timeouts below 29s

| function | now | set to | measured p99 |
|---|---:|---:|---:|
| `cvtailor` | 120s | **29s** | 14,120ms |
| `company-research` | 60s | **29s** | 1,015ms |
| `cover-letter-api` | 60s | **29s** | 3,219ms |
| `interview-prep-api` | 60s | **29s** | 2,179ms |

**Why.** Today a >29s request gets a client 504 while the Lambda keeps running,
keeps billing, and **may still complete its DynamoDB write**. That makes "did it
work?" unanswerable from the client — which will directly undermine session 6's E2E
assertions. Capping at 29s makes the Lambda die when the client gives up.

All four have ≥15s of measured headroom, so this is a safe change. Note it does not
*prevent* the 504; it prevents the invisible half-completed write behind it.

### P2.3 — N18: separate ai-assist's in-process budget from its Lambda timeout

`DEFAULT_ASSIST_TIMEOUT_SECONDS = 25` ([`ai_assist_handler.py:51`](../../src/backend/careervp/handlers/ai_assist_handler.py#L51))
and the Lambda timeout is **also 25s**, so the graceful-timeout path can never run —
Lambda kills the process in the same instant. The comment's "one safety margin below
the 29s ceiling" is true of the gateway and false of Lambda.

**Change.** Keep the in-process budget at 25s, raise the Lambda timeout to **29s**.
That yields 4s to catch the timeout, emit the metric, and return a 503. (Do not
lower the in-process budget instead — 25s is already tight for the LLM call.)

### P2.4 — Next ceiling risk, for awareness not action

`POST /users/me/cv` runs `parse_cv` synchronously on `cv-parser-lambda`:
**p99 17,397ms, max 17,876ms — 11.1s of margin.** Second-closest to the ceiling
after gap. Deleting the S3 worker (P1.1) does not change this, because the worker
never contributed. If CV parse latency grows, this is the next endpoint to make
async — and *that* is the deliberate version of the feature P1.1 deletes.

### P2.5 — N15: exercise the failure handlers before trusting session 1

Session 1 makes failures legible in *code*. Nothing in the plan establishes that the
failure handlers **run** — `artifact-failure-handler`, `cr-failure-handler`,
`vpr-dlq-handler`, `error-report` have **zero invocations**, and two of them were
never checked for N1's bug shape (non-HTTP trigger + API-only handler), which is
invisible precisely because they never run.

**Change.** For each: (a) read the handler for a `Records`/`eventSource` branch —
a pure code read, no access needed, catches an N1 clone immediately; (b) add a unit
test that feeds it its **real** trigger event shape (SQS record / DLQ record). Note
the repo currently has **zero** S3-event fixtures and this class of bug is exactly
what that gap hides.

---

## P3 — Ownership and delete policy (2 days) — gates P4

### P3.1 — S3: require `user_id` on the cover-letter read (**must precede P4**)

```python
# dynamo_dal_handler.py:595-599
def read_cover_letter_by_artifact_id(self, application_id: str, artifact_id: str)
```

No `user_id`. Safe today only because `application_id` *is* the user's sub for cover
letters. P4 removes that.

**Change.** Add a required `user_id` parameter; after fetching, assert ownership via
the same tolerant accessor `core_repository` uses —
`str(item.get('user_id') or item.get('userId') or '').strip()`
([`core_repository.py:316-317`](../../src/backend/careervp/dal/core_repository.py#L316-L317)) —
and return not-found (**not** forbidden) on mismatch, so the API does not confirm
existence of another tenant's row. Update all callers.

**Verify.** A unit test that writes an artifact owned by user A and reads it as user
B, asserting not-found. This test is the thing that makes P4 safe; write it first
and watch it fail.

**Risk.** Low mechanically, high value. Do the same sweep for the other five
artifact types — the audit only traced cover letter in depth, and
`get_interview_prep_by_artifact_id` (`core_repository.py:262`) should be checked for
the same shape.

### P3.2 — N5: make the reaper work, and give it a DynamoDB path

Two separate defects:
1. **Config:** `careervp-artifact-cleanup-lambda-devx` has no `DYNAMODB_TABLE_NAME`,
   so it logs `No jobs table configured — reaper skipping` and returns
   `{'status':'ok','cleaned':0}` — 57 times. Set the var in infra (it should be the
   **jobs** table; see the P4.3 warning about this var's overloaded meaning), and
   apply P0.2 so this can never silently recur.
2. **Scope:** even configured, `cleanup_cancelled_artifact` only calls
   `s3.delete_object`. It never deletes a DynamoDB artifact row. If artifact rows
   should be reaped, that code does not exist yet.

**Verify.** After the env fix, a run logs a real `cleaned` count; add a metric so
`cleaned == 0` for N consecutive runs is visible rather than reassuring.

### P3.3 — N4: decide Delete; it is a scope decision, not a bug

Delete is **absent for 5 of 6 artifact types** — one DELETE route in a 49-route API,
no DynamoDB reaper, and no frontend DELETE call anywhere. The plan's 40% "full CRUD"
implies bugs to fix; there is no implementation to fix.

**Change: make an explicit, recorded decision** before session 6, one of:
- **(a) Defer to V2.** Legitimate — `CLAUDE.md` already defers Job Tracking and
  others. Cheapest, and honest. Cancel-plus-TTL becomes the stated lifecycle.
- **(b) Implement uniformly.** Six DELETE routes + ownership checks (P3.1 is the
  prerequisite) + frontend affordances + a real DynamoDB reaper (P3.2.2). This is
  its own session, and the plan does not have one for it.

Do not leave it implicit. An unstated Delete policy is what produced the 40%.

---

## P4 — The repartition: split the plan's session 2 into three

The premise ("legacy data is disposable, so no migration/backfill/dual-read") **is
sound and survives the evidence**. What does not survive is the assumption that
disposability also covers *code that cannot address the new grammar*. It does not:
the P4.1 sites break on **newly written** rows.

### P4.1 — Session 2a: repartition `cover_letter` + `interview_prep`

Move the partition key from `user_id` → `applicationId`.

**Must fix in the same change** (each will otherwise 404 on every request):

| site | current | fix |
|---|---|---|
| `cover_letter_handler.py:1441` | `Key={'applicationId': user_id, …}` | resolve the real applicationId; build via `table_registry.canonical_item_key()` |
| `cover_letter_handler.py:1453` | `KeyConditionExpression='applicationId = :uid'`, `':uid': user_id` | same |
| `interview_prep_handler.py:406` | `'Key': {'applicationId': user_id, …}` | same |

Where the applicationId comes from: it is available at write time —
`request_data.application_id` is already persisted (`cover_letter_submit_handler.py:161`
writes a `job_id` attribute holding it). For the **cancel/status** paths the caller
supplies only an opaque artifact id, so those need either a GSI on `artifactId` or a
resolution through the applications table. **Decide this before starting** — it is
the one genuinely open design question in session 2.

**Beware the naming lie (N19):** `table_registry.cover_letter_artifact_id(job_id)`
is passed a *cover-letter id*, not a job id (`cover_letter_submit_handler.py:145`
does `job_id = str(uuid.uuid4())`). Rename the parameter as part of this change or
it will mislead the next reader too.

**Also normalise N11** while in this file: the two interview_prep writers use
different id semantics (`prep_id` vs request id) and different status casing
(`'completed'` vs `'COMPLETED'`). Pick one casing, normalise on read.

**Verify.** The P3.1 cross-tenant test must still pass. Create → read → cancel →
PATCH each of the two types against moto.

### P4.2 — Session 2b: re-home `cv_tailored` + `gap_questions` off the users table

**Add to the plan's scope — two omissions:**

1. **The 9 `ARTIFACT#VPR#v1` rows also live in users-table**, keyed by
   `applicationId`, while a 10th VPR copy now lives in artifacts-table under a bare
   UUID `artifactId` (created by this branch's `f5a869e`). VPR is dual-homed under
   two grammars (N12). Session 2's stated scope names only `cv_tailored` and
   `gap_questions`. Either re-home VPR here or state explicitly that session 6
   deletes the users-table copies.
2. **TTL (N7).** The destination artifacts table has **TTL ENABLED on
   `expiration`**. Three attribute names are in use across the estate
   (`expiration`, `ttl`, `expiresAt`). Before moving anything in:
   - strip or deliberately set `expiration` on every moved item — an item that
     arrives carrying an `expiration` is silently deleted by DynamoDB with **no
     application log line**;
   - note that gap rows currently carry `ttl`, which is dead in users-table
     (TTL disabled) and still dead in artifacts-table (wrong attribute name);
   - pick one attribute name estate-wide.

**Good news:** the gap sort key is `ARTIFACT#GAP_ANALYSIS#<id>#<applicationId>` —
the applicationId is **already in the key**, so gap re-homing needs no lookup.

**S1/S4 fall out of this step.** `_load_tailored_cv`
([`ai_assist_handler.py:447-453`](../../src/backend/careervp/handlers/ai_assist_handler.py#L447-L453))
reads `pk=user_id, sk=ARTIFACT#CV_TAILORED#…` and filters on the `job_id`
*attribute*; it must be rewritten to the canonical read. And S4's 28-of-31 CV
duplication is a **deliberate dual-write** (`cv_upload_handler.py:196-207`) that
exists to compensate for the dead worker and the ai-assist env inversion — once
P4.3 lands, that dual-write can be dropped, which resolves S4 rather than merely
documenting it.

### P4.3 — Session 2c: collapse the env chain — **do this last, and treat it as the riskiest step**

This is the single highest-blast-radius edit in the plan attached to the
least-observable Lambda in the account.

**What you are walking into.** `ai-assist` has the two vars **swapped** relative to
all 30 other Lambdas:

```
careervp-ai-assist-lambda-devx:
  ARTIFACTS_TABLE_NAME        = careervp-users-table-devx      <-- users
  COMPANY_RESEARCH_TABLE_NAME = careervp-artifacts-table-devx   <-- artifacts
```

and the repo already documents why collapsing is unsafe
([`table_registry.py:12-15`](../../src/backend/careervp/dal/table_registry.py#L12-L15)).
`DYNAMODB_TABLE_NAME` means **users-table** on company-research/gap-api/vpr workers
and **artifacts-table** on cover-letter/interview-prep — one name, two physical
tables. `TABLE_NAME` means users-table on five Lambdas and cvs-table on two.

**Steps, in order.**
1. Land P4.1 + P4.2 so the data ai-assist reads actually lives in the artifacts
   table.
2. Re-point ai-assist's two vars to their honest values, in the same commit as the
   code change that stops relying on the inversion.
3. Then collapse `_ARTIFACTS_ENV_CHAIN` — and only then, because the fallback tail
   (`DYNAMODB_TABLE_NAME`, `TABLE_NAME`) is what makes the inversion survivable.
4. Update the `table_registry.py:12-15` docstring; it becomes false at that point.
   Leaving a stale warning is its own hazard.

**The verification problem, stated plainly.** ai-assist has **zero invocations**, no
test that would catch a mis-set env var, and (until P2.3) an error path that cannot
run. There is no signal here. Before touching it, add an integration test that
exercises `POST /ai/assist` end-to-end — the frontend already calls it
([`methods.ts:333`](../../src/frontend/api/methods.ts#L333)) and the route is
deployed, so this is a live, reachable, never-exercised path. **The prior session was
"wrong twice in ways it only discovered by deploying." This is the most likely place
for a third.**

---

## P5 — N13: re-scope the identity surrogate (plan sessions 4-5)

**It is not unstarted, and it is not done.**

Already built: `identity_map_repository.py`, `identity_resolver.py`
(`get_user_id(sub)`, `link()`, `_user_id_factory()`), `api_gateway_authorizer.py`,
plus infra plumbing (`constants.IDENTITY_MAP_TABLE_NAME_ENV`,
`api_construct.py:2473`) and a **deployed** `careervp-identity-map-table-devx`
(`KeySchema: [{sub, HASH}]`).

Not live: the table has **0 items**; the API's only authorizer is
**`COGNITO_USER_POOLS`**; the custom authorizer Lambda is **not deployed at all**;
**no** Lambda has `IDENTITY_MAP_TABLE_NAME` set.

**Re-scope from "build" to "deploy and cut over", and add the step the plan omits:**
swapping a **49-route** API from `COGNITO_USER_POOLS` to a custom Lambda authorizer.
That changes the claims shape every handler's `_extract_authenticated_user_id` reads,
and it touches frontend token handling (`middleware.ts`, auth contexts). Steps:

1. Deploy the authorizer Lambda; set `IDENTITY_MAP_TABLE_NAME` on it.
2. Backfill the identity map for the 17 existing `PROFILE` users (a mutating write —
   needs explicit approval and a reviewed script).
3. Cut routes over **incrementally**, not all 49 at once — start with `/health` and
   one read-only route.
4. Only then change `user_id` semantics in the DAL. Note `_owner_id` already
   tolerates both `user_id`/`userId` spellings, which helps here.

Sessions 4-5 as scoped are optimistic; this is closer to three.

---

## P6 — Session 6: E2E and legacy cleanup

**Blocked until P1.1 lands** — a real-CV E2E begins with a CV upload whose async
worker is 0-for-66. (After P1.1 it is unblocked, because the sync path was always
the working one.)

**Add to scope:**
- **Hebrew (N16).** Declared V1 scope in `CLAUDE.md`, code support exists
  (`cv_parser.detect_language() -> Literal['en','he']`, RTL prompt instructions), and
  **zero `'he'` values exist in live data** — 52 language values, all `'en'`. Either
  add a Hebrew CV to the E2E or explicitly move Hebrew to V2. Do not let it pass
  silently as "V1 complete".
- **"Delete legacy rows" has no tooling.** There is no DynamoDB reaper (N4/N5), so
  this is a manual, mutating, cross-table deletion. It needs a reviewed script with
  a dry-run mode, and it should run **after** the E2E proves the new paths, not
  before.
- **Do not assert on 2xx alone.** N1 is the proof: the API returned 2xx while the
  worker behind it failed 100% of the time. Assert on the artifact row and on worker
  success metrics, not the response code.

---

## Two things I would fix that are not on the plan at all

### N9 — the legacy cover-letter fallback is broken, not merely slow

```python
# dynamo_dal_handler.py:796
response = table.scan(FilterExpression=Attr('pk').eq(pk) & Attr('sk').eq(sk), Limit=1)
```

`Limit` bounds items **evaluated**; `FilterExpression` applies *after*. This
evaluates **one arbitrary item** and tests whether it happens to be the wanted one —
~1/25 today, worse as the table grows. So it almost always returns `None`.

**Fix.** Given disposability, the honest fix is to **delete this fallback** along
with `COVER_LETTER_LEGACY_READ_ENABLED` (which defaults to `'true'`). A broken
fallback is worse than none: it converts a loud `ValidationException` into a quiet
not-found. If it must stay, use a `query` on the legacy key, never a filtered scan
with `Limit`.

### N10 — `ScanIndexForward=False` on a HASH-only index does nothing

```
jobs-table GSI user_id-index KeySchema: [{ user_id, HASH }]   <-- no RANGE key
```
```python
# jobs_repository.py:157-160
'ScanIndexForward': False,  # newest first     <-- false claim
```

There is no sort order to reverse. So the ≤100-row window that
`core_repository._resolve_vpr_job_id` filters in Python is **100 arbitrary jobs**,
not the 100 newest, and the later `sort(key=updated_at)` only orders within that
arbitrary window. This is S5's real severity.

**Fix — pick one:**
- **(a)** Add a range key (`created_at`) to `user_id-index` so ordering exists and
  `Limit` means "newest N". Requires a GSI change (backfills automatically).
- **(b)** Query by `application_id` directly instead of scanning a user's jobs and
  filtering — this is the better fix, since `_resolve_vpr_job_id` already knows the
  `application_id` it wants. It removes the 100-row ceiling entirely rather than
  raising it.

Prefer (b). Also delete the false comment either way.

---

## Verification gates

Run before each phase merges. From `CLAUDE.md`:

```bash
# backend
cd src/backend && uv run ruff format . && uv run ruff check --fix . \
  && uv run mypy careervp --strict && uv run pytest tests/unit/ -v --tb=short
# baseline to hold: 1419 passed, 15 skipped, 4 xfailed

# frontend (required for P2.1)
cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration

# infra (required for P1, P4.3, P5)
cd infra && uv sync && cdk synth
python src/backend/scripts/validate_naming.py --path infra --strict
```

**A green unit suite is currently not evidence of liveness.** All 1419 tests pass
today while the CV-upload worker is 0-for-66, the reaper is a 57-times no-op, and
the stream consumer no-ops on every write. Each phase needs a **live devx check**,
not just green tests:

| phase | live check |
|---|---|
| P1.1 | `cv-upload-worker` no longer exists; Errors metric stops accruing |
| P1.2 | `list-event-source-mappings` is empty or filtered |
| P2.1 | `gap-api` p99 < 3,000ms |
| P2.2 | all four `Timeout` values ≤ 29 |
| P3.1 | cross-tenant read test fails before the fix, passes after |
| P4.1 | cancel + PATCH return 2xx for both types post-repartition |
| P4.3 | `POST /ai/assist` returns 2xx — **its first successful invocation ever** |
| P5 | identity-map `ItemCount > 0` |

---

## Still unresolved (from the audit's §5)

Two of the seven open items are now answered by this pass:

- **"Does the sync path substitute for the dead S3 worker?" — YES.**
  `cv_upload_handler.py:196-207` persists to `CVS_TABLE_NAME` explicitly to avoid
  depending on the worker. This is what makes P1.1 (delete) the right fix and
  raises audit confidence #6.
- **"Why does the D-H2 guardrail not catch N8?"** — the detector covers `pk`/`sk`
  and `USER#` only; the canonical key names are unguarded (P0.1).

Still open, unchanged:
- The 4xx security/contract split — needs access logging with `$context.status` on
  the devx stage. This remains the main caveat on the "25% → 20%" verdict.
- Whether `cover-letter-status` / `interview-prep-status` contain more N8-shaped
  sites — a pure code read; **P0.1's regex will answer it automatically.**
- Whether the hub projection resolves post-repartition — trace
  `application_repository.py:324-387` (`artifact_statuses.#at_id`).
- Whether `artifact-failure-handler` / `cr-failure-handler` share N1's bug shape —
  P2.5 step (a).
