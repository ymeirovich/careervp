# Wave-3 — Type-O closure batch, Stage 1 closeout item 4a, Stage 2

- **Date:** 2026-08-08
- **Branch:** `db-redesign`
- **Environment:** AWS 788159322332 / us-east-1 / **devx** only. `dev` and `staging` untouched.
- **Companion to:** [`CLAIMS-LEDGER.md`](../db-redesign/code/code-analysis/project/CLAIMS-LEDGER.md),
  [`wave3-preplan-audit-20260804.md`](./wave3-preplan-audit-20260804.md),
  [`wave3-preplan-remediation-20260804.md`](./wave3-preplan-remediation-20260804.md)

Every claim below carries its type, its prediction *written before the command ran*,
and the observation. Where they differ, the difference is stated flatly.

---

## 0. Things that contradicted the prompt

Recorded first, because three of them changed how the work had to be done.

| # | the prompt said | what is actually true |
|---|---|---|
| 1 | "Stage 0 enabled access logging, so C-03 is now answerable" | The access log Stage 0 created holds **33 records, all from 2026-08-05**, and **zero** on `/interview-prep/generate` or `/cover-letter/generate`. It cannot answer C-03. The question was answered instead by the **pre-existing API Gateway execution log** (`API-Gateway-Execution-Logs_ymzhvcxod0/prod`, retention **never expires**, 21,914 records, 1,310 correlated requests back to 2026-07-20), which was already installed and already held the answer. |
| 2 | "windowed **after** 2026-08-03" | After 2026-08-03 there are **2** requests total across the two decision-relevant endpoints. The instructed window is empty. The answer below comes from the full execution-log window and says so. |
| 3 | "each of the 22 [DLQ] messages names its own user" | There are **23** messages naming **5** distinct users, not 22 naming 22. One user accounts for 13 of them. |
| 4 | "it is why 31/28 drift already exists" | Measured drift is **30** rows in `cvs-table` vs **33** `CV#` rows in `users-table`. |
| 5 | C-05's prime suspect is `POST /jobs/{id}/gap-responses` | It is *a* suspect but not the largest. `POST /ai/assist` and `PATCH /cv-tailoring/{id}` are worse, because both echo back a whole artifact and measured artifacts reach 18–19.7 KB. |

---

## 1. C-03 — What fraction of 4xx is security vs contract?

**Type O · Status OBSERVED · prediction REFUTED**

> **Prediction (written first):** both `/interview-prep/generate` and
> `/cover-letter/generate` are **auth-dominated** — I expected **>60 %** of their
> non-2xx to be 401/403.

**Observed:** security 4xx is **10 of 199** (5 %). Contract 4xx is **189 of 199** (95 %).
The two target endpoints have **zero** 401 and **zero** 403.

Instrument: `API-Gateway-Execution-Logs_ymzhvcxod0/prod`, 1,310 requests joined
request-id → (method, resource path) → status. Window **2026-07-20 20:31:03Z →
2026-08-05 20:48:42Z**.

| endpoint | n | 2xx | 2xx % | 400 | 404 | 409 | 401 | 403 | 5xx |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| POST `/interview-prep/generate` | 26 | 2 | **7.7 %** | **19** | 0 | 4 | **0** | **0** | 1 |
| POST `/cover-letter/generate` | 21 | 3 | **14.3 %** | 6 | 0 | **12** | **0** | **0** | 0 |
| POST `/vpr/generate` | 29 | 11 | 37.9 % | 13 | 0 | 5 | 0 | 0 | 0 |
| POST `/gap-analysis/questions` | 26 | 8 | 30.8 % | 9 | 4 | 0 | 0 | 0 | 5 |
| POST `/jobs` | 43 | 25 | 58.1 % | 13 | 0 | 0 | 0 | 5 | 0 |
| POST `/users/me/cv` | 48 | 33 | 68.8 % | 7 | 0 | 0 | 0 | 0 | 8 |
| **overall** | **1310** | **1081** | **82.5 %** | 118 | 47 | 24 | **5** | **5** | 30 |

**Verdict on the audit's caveat.** N14 stated the low 2xx rates "cannot be explained
by auth alone". That is now measured, not suspected: they are **not explained by auth
at all**. The same query also refutes N14's other guess — that the `/users/me*` GET
rows are "very likely dominated by 401s". In this window `GET /users/me` is 93/93,
`/users/me/subscription` 51/51 and `/users/me/usage` 51/51, i.e. **100 % 2xx, zero 401s**.

**The load-bearing caveat, which cuts the other way.** Every 400 and all but one 409
on the two endpoints lands on a **single day, 2026-08-01** — the live-harness session
(`7db5005`), and *before* the three F-DEVX-1 fixes of 2026-08-03 (`f5a869e`,
`91b8917`, `f3df729`). Windowed strictly as instructed (after 2026-08-03) the counts
are: `/cover-letter/generate` 1×409, `/interview-prep/generate` **0 requests**.

So C-03's headline question is settled — the 4xx is contract, not security — but
"is there a *live, post-fix* contract defect on those two endpoints" is **not**
settled, because no one has called them since the fix. Stage 3+ produces that traffic
and the instrument is now in place to read it.

---

## 2. C-04 — Is the cover-letter read cross-tenant exploitable today?

**Type O · Status OBSERVED · prediction CONFIRMED · NO ESCALATION**

> **Prediction (from the ledger, written first):** 404/403 today; 200 only *after*
> the Stage 7 repartition if ownership does not land first.

**Observed: 404. Nobody can read anyone else's cover letter today.**

The devx test account's own Cognito `sub` **is** `848834a8-…`, the owner of all four
devx cover letters, so it could only read its own — which proves nothing. One
throwaway account was registered at explicit human approval (the no-register rule
waived for exactly one account) to get a second identity:

- user A = `848834a8-4061-703d-419c-0294d4e88d66` (owner)
- user B = `14683418-30a1-7018-9421-49a6fe0a7f78` (probe)

| request | user B | user A (control) |
|---|---|---|
| `GET /cover-letter/51fabb2a-…/status` | **404** `COVER_LETTER_NOT_FOUND` | **200** `status: completed` |
| `GET /cover-letter/99d9767a-…/status` | **404** | **200** |
| `GET /cover-letter/fb097238-…/status` | **404** | **200** |
| `GET /cover-letters` | 200, **0 items** | 200, **4 items** |

**The control is the point.** A 404 on its own is worthless evidence — it could mean
the route always 404s. It does not: the owner gets 200 on the same three ids in the
same minute. The isolation is real today.

`GET /cover-letter/{id}` *without* `/status` returns 403 `DEFAULT_4XX` for **both**
users, i.e. it is not a real route. It is excluded from the finding rather than
counted as a second "denial".

**The latent risk is unchanged and is now evidenced rather than asserted.** All four
cover letters are partitioned under **one** `applicationId`, and that value *is* the
owner's Cognito sub:

```
applicationId=848834a8-4061-703d-419c-0294d4e88d66  ARTIFACT#COVER_LETTER#51fabb2a-5829-427b-9a60-cd1f05cfa413
applicationId=848834a8-4061-703d-419c-0294d4e88d66  ARTIFACT#COVER_LETTER#99d9767a-336a-4667-9731-539bee3c9c82
applicationId=848834a8-4061-703d-419c-0294d4e88d66  ARTIFACT#COVER_LETTER#ef2ddfcc-0c13-434b-b68f-20271cd55205
applicationId=848834a8-4061-703d-419c-0294d4e88d66  ARTIFACT#COVER_LETTER#fb097238-09c4-4abd-a3ec-be9afb177056
```

`read_cover_letter_by_artifact_id` still takes **no `user_id`**. It is safe only
because the partition key it *does* use happens to be the tenant key. Stage 7
replaces that value with a real application id and the accident stops protecting
anything. **Ownership must land before the repartition** — which is exactly the
P3→P4 ordering constraint, now backed by a measurement instead of an argument.

---

## 3. C-05 — Does the 8 KB WAF body limit block anything else?

**Type O · Status OBSERVED · prediction SPLIT — confirmed on the log half, refuted on the ranking**

> **Prediction (written first):** WAF logs show **zero** `SizeRestrictions_BODY` on
> any non-CV path, but the computed max for `POST /jobs/{id}/gap-responses` exceeds
> 8 KB — a latent, not yet realised, second victim.

### Log half — CONFIRMED

`aws-waf-logs-careervp-core-waf-devx`, full 14-day retention, 1,011 records:

| action | method | uri | n |
|---|---|---|--:|
| BLOCK | POST | `/prod/users/me/cv` | 5 |
| ALLOW (rule COUNTed) | POST | `/prod/users/me/cv` | 1 |

**Zero** `SizeRestrictions_BODY` events on any other path. The single ALLOW is the
2026-08-05 20:47:54 upload that finally succeeded, and it confirms the Stage-1
override is live rather than merely synthesised:

```json
{"ruleGroupId":"AWS#AWSManagedRulesCommonRuleSet",
 "nonTerminatingMatchingRules":[{"ruleId":"SizeRestrictions_BODY",
                                 "action":"COUNT","overriddenAction":"BLOCK"}]}
```

### Computed half — the ranking was wrong

`api_models.py` declares **13 request models and zero `max_length` constraints**.
Nothing in the API contract bounds any request body below the WAF limit. Measured
artifact sizes from live devx data (the ceiling a client would echo back):

| artifact | measured max |
|---|--:|
| VPR | **19,704 B** |
| INTERVIEW_PREP | **17,537 B** |
| GAP_ANALYSIS (`questions`) | **11,239 B** |
| COMPANY_RESEARCH | 6,211 B |
| CV_TAILORED (`cv_sections`) | 2,451 B |
| COVER_LETTER | 2,469 B |

Ranked realistic max body per write endpoint (22 write routes enumerated live):

| endpoint | bound by | realistic max | > 8 KB? |
|---|---|--:|---|
| `POST /users/me/cv` | base64 of the file | 53,602 B observed | **yes** (known, overridden for devx) |
| `POST /ai/assist` | `current_text`, **unbounded** | ~19 KB if the client sends the current VPR | **yes** |
| `PATCH /cv-tailoring/{id}` | `cv_sections`, **raw `json.loads`, no model at all** | grows with real CVs | **likely** |
| `POST /jobs/{id}/gap-responses` | 10 × unbounded `response` | ~8–12 KB | **marginal** |
| `POST /jobs` | `description`, unbounded (internal model allows **50,000**) | SysAid posting = 3,026 B | no, but unbounded |
| everything else | small scalars | < 2 KB | no |

Two notes worth carrying:

- `cv_tailoring_models.py:35` declares `job_description: str = Field(..., max_length=50_000)`.
  The internal contract permits a body six times the WAF limit. That is a
  contradiction in the system's own spec, not just a gap.
- `PATCH /cv-tailoring/{id}` parses its body with a bare `json.loads` and no Pydantic
  model at all (`cv_tailoring_handler.py:942-953`), so it has no validation of any kind.

**Prediction outcome:** the log half is confirmed exactly. The prime-suspect ranking
is refuted — `gap-responses` is fourth, not first.

---

## 4. C-06 — Do the two failure handlers share N1's shape?

**Type O · Status OBSERVED · prediction CONFIRMED**

> **Prediction (written first):** both are purpose-written for a direct Step Functions
> payload and do **not** parse an API-Gateway event, so they do **not** share N1's shape.

Both handlers read a plain dict and never touch `httpMethod`, `body`, `Records` or
`eventSource`:

- `cr_failure_handler.py:35-39` — `event.get('user_id')`, `event.get('job_id')`
- `artifact_failure_handler.py:33-40` — `event['artifact_type']` + `event['context']`

The falsifier as written ("both branch on `Records`/`eventSource`") is not the right
test for these two, because their trigger is Step Functions, which does not send
`Records`. The test that matters is whether the chain's payload matches what the
handler parses. It does, exactly:

| state | payload sent (`artifact_chain_construct.py`) | handler reads |
|---|---|---|
| `HandleCRFailure` | `TaskInput.from_json_path_at("$")` — raw execution input | `user_id` / `job_id` ✓ |
| `HandleVPRFailure` / `HandleCVFailure` / `HandleCoverLetterFailure` / `HandleInterviewPrepFailure` / `HandleFinalArtifactsFailure` | `{"artifact_type": …, "context": object_at("$")}` | `artifact_type` + `context.user_id/job_id` ✓ |

All six use `payload_response_only=True`, and each `add_catch` writes its error to a
`result_path` **beside** `$` rather than replacing it, so `user_id`/`job_id` survive
into the failure branch. **No N1-shaped bug. C-06 closes clean.**

*Flagged, not fixed:* `HandleFinalArtifactsFailure` passes
`artifact_type="final_artifacts"`, and `update_artifact_status` accepts any string,
so it will write an `artifact_statuses.final_artifacts` key that no artifact type
corresponds to. Cosmetic today; it is a map key, not a validated enum.

---

## 5. C-02 — Does the sync parse path fully replace the deleted S3 worker?

**Type E · Status OBSERVED · prediction CONFIRMED (with two corrections)**

> **Prediction (written first):** all 22 DLQ users have CVs; zero bypass producers.

Read non-destructively (`--visibility-timeout 0`, 23/23 unique messages recovered,
nothing deleted, nothing consumed).

**Correction 1:** there are **23** messages naming **5** distinct users, not 22
naming 22.

**Falsifier 1 — "a DLQ message whose user has no CV row": NOT met.**

| user | DLQ msgs | cvs-table rows | users-table `CV#` |
|---|--:|--:|--:|
| 8428d4e8-d071-7088-a9c3-9e630806436b | 13 | 12 | 12 |
| f44804d8-1001-7091-5064-5ac05ae152b8 | 6 | 6 | 6 |
| 848834a8-4061-703d-419c-0294d4e88d66 | 2 | 2 | 2 |
| a4f8b498-10b1-700d-cbff-db24f144031b | 1 | 1 | 1 |
| 8418e4a8-40e1-700a-dce7-a9bf71c2c7d6 | 1 | 2 | 2 |

Correlating at object granularity via the `source_file_key` attribute (the direct S3
link): **22 of 23** DLQ objects have a CV row. The one that does not is:

```
8428d4e8-…/cdc0b0b2-4e55-46ce-b1a6-0cf6d4f91c5f.txt   113 bytes   2026-08-01T15:28:20.998Z
```

Before escalating I checked what the API told the client. The execution log:

```
(09d05318-4f4b-48df-a6e1-46874ee742f3) HTTP Method: POST, Resource Path: /users/me/cv   15:28:16.485
(09d05318-4f4b-48df-a6e1-46874ee742f3) Method completed with status: 500                15:28:25.292
```

**The request returned HTTP 500.** The absence of a CV row is the honest outcome of a
failed request, not silent loss — and the deleted worker would not have rescued it,
since that worker has failed on 100 % of its lifetime invocations. The object content
is a valid (if minimal) CV, so this was not a malformed-input rejection.

**Falsifier 2 — "a CV-bucket producer that bypasses `cv_upload_handler`": zero.**
Only two Lambdas receive `CV_BUCKET_NAME` (`api_construct.py:1334`, `:1879`) and both
run the *same* handler, `careervp.handlers.cv_upload_handler.lambda_handler` — which
independently re-confirms S-10. The worker holds `cv_bucket.grant_read` only
(`api_construct.py:1905`), so it **cannot** write. The single writer is
`cv_upload_handler.py:132`.

**Verdict: worker redundancy holds on real traffic.** C-02's prediction is confirmed
at the granularity its own falsifier defines. This is the first *independent
instrument* to confirm it, which is what the ledger asked for — the prior agreement
between two agents was correlated evidence and did not count.

**Correction 2 — a new defect, flagged not fixed.** Reconciling the bucket against
`cvs-table` found **2 orphaned S3 objects** (an object with no CV row anywhere):

```
113 B   2026-08-01T15:28:21Z  8428d4e8-…/cdc0b0b2-….txt   (the 500 above)
197 B   2026-07-20T20:31:14Z  e4b8b4c8-…/5bb32850-….txt   (predates DLQ retention)
```

Zero dangling rows in the other direction. `cv_upload_handler` writes to S3 *before*
DynamoDB (`:132` then `:188`), so any failure after the PUT orphans the object, and
per N5 the S3 reaper is a no-op. Low severity in devx; it is a real leak in prod.

---

## 6. Stage 1 closeout — item 4a only

`cv_upload_handler.py` previously logged a warning on a failed `cvs-table` write and
returned **201**. Since the Stage-1 repoint every CV reader resolves from
`CVS_TABLE_NAME`, so that combination produces a CV that exists to nobody. The write
is now fatal.

**GATE 4a — PASS.** And the gate is demonstrably real, not vacuous. Against the
*pre-change* handler the new test fails, showing the exact defect:

```
WARNING  cv_upload_handler.py:212 Failed to save CV to cvs_table (non-fatal)
INFO     cv_upload_handler.py:219 CV upload completed successfully
FAILED tests/unit/test_cv_upload_handler.py::…::test_cvs_table_write_failure_is_fatal_not_a_201
```

Against the changed handler it returns **500** and passes.

**Blast radius, stated plainly.** `tests/conftest.py:75` sets `CVS_TABLE_NAME` for the
whole session, so making the write fatal means every test that expects a 201 must
actually provide a reachable cvs-table. Five existing tests were creating only
`test-users-table` and started failing — correctly. They now create both, which is
what production looks like. That is a real consequence of the change, not test
cosmetics.

### Live verification after deploy

```
POST /users/me/cv   (text CV, 578 B)
<<<HTTP 201 in 10.533692s>>>   cv_id 138a9f19-0740-4c4b-9f33-38409e00404a  status parsed
```

Both writes landed — the fatal path does **not** fire spuriously:

| table | before | after |
|---|--:|--:|
| `careervp-cvs-table-devx` | 30 | **31** |
| `careervp-users-table-devx` `CV#` rows | 33 | **34** |

**What was NOT done live, and why.** I did not force a *live* cvs-table failure.
API Gateway invokes the published CodeDeploy alias, not `$LATEST`, so editing
`CVS_TABLE_NAME` with `update-function-configuration` would not reach the live
function; forcing it would require revoking the role's `dynamodb:PutItem` on
cvs-table. That is more invasive than this gate warrants. The forced-failure half is
therefore proven at unit level **with its falsifier demonstrated** (the test fails
against the old handler and passes against the new one), and the happy path is
proven live. Stated plainly rather than reported as a full live gate.

Steps **4b, 5 and 6 were not started**, as instructed: the users-table write still
runs, the `CV#` rows are untouched, and the worker still exists. Drift is unchanged
at 3 rows.

**Backend gates:**

```
ruff format  : 419 files left unchanged
ruff check   : All checks passed!
mypy --strict: Success: no issues found in 137 source files
pytest       : 1427 passed, 15 skipped, 4 xfailed      (baseline 1419 — risen, not fallen)
```

**A process correction on my own work.** Mid-run the suite showed 45 failures and I
first attributed them to pre-existing uncommitted changes. That was wrong. They were
caused by my own edit — I had added `CVS_TABLE_NAME` to this file's fixture teardown,
which popped a variable `tests/conftest.py` owns session-wide and starved every later
module. Isolating it (deselect my tests → still 45; revert the handler → still 45;
minimal two-file repro → `RuntimeError: CVS_TABLE_NAME is not configured`) found it.
Fixed by scoping with `monkeypatch.setenv` instead. Recorded because the ledger's
calibration section exists for exactly this.

---

## 7. Stage 2 — job + application creation

Deployed first: `ENVIRONMENT=devx make deploy-devx` → `UPDATE_COMPLETE`, 872.81 s,
exit 0. Then `POST /users/me/trial/reset` → 200 `{"status": "reset"}`.

**Summary: (a) PASS · (b) FAIL · (c) PASS · (d) PASS but vacuous · (e) N/A.**

### (a) `POST /jobs` → 201 — **PASS**

Body 3,189 bytes (SysAid posting, 3,026 B). `url: https://www.sysaid.com/` per the
instruction; the deep job URL had been rejected as unreachable in a prior run.

```
<<<HTTP 201 in 8.218261s>>>
{"id": "518c11b9-303e-41d1-bfd7-468707541bd1",
 "job_id": "518c11b9-303e-41d1-bfd7-468707541bd1",
 "user_id": "848834a8-4061-703d-419c-0294d4e88d66",
 "title": "Learning Experience Specialist", "company_name": "SysAid", …}
```

### (b) hub row in `careervp-applications-table-devx` — **FAIL**

```
$ aws dynamodb get-item --table-name careervp-applications-table-devx \
    --key '{"userId":{"S":"848834a8-…"},"applicationId":{"S":"518c11b9-…"}}'
(no output — no such item)
```

The job was written to **`careervp-jobs-table-devx`** instead, whose key schema is
`job_id` (HASH) **only** — no user partition. `careervp-applications-table-devx` is
correctly keyed `userId` (HASH) / `applicationId` (RANGE) and still holds 12 rows,
2 of them for this user, none of them this job.

**This is not a regression — it is the design, and the gate's premise was wrong.**
`create_job` (`job_handler.py:240-281`) calls only
`_get_jobs_repository().create_job(...)` and never touches `ApplicationRepository`.
More pointedly:

> **`ApplicationRepository.create()` has zero callers anywhere in the codebase.**
> The canonical hub-row constructor — the one that writes the full
> `userId`/`applicationId` item with `state='created'` and `entity_type='APPLICATION'`
> — is dead code.

The hub row is actually born **lazily and much later**, as a side effect of
`update_gap_responses` (`application_repository.py:114-151`), a deliberately
unconditioned `update_item` upsert that runs at `POST /jobs/{id}/gap-responses` —
Stage 3-4. Its `job_id = if_not_exists(job_id, :app_id)` hard-codes
**`job_id == application_id`**, which is why `GET /applications/{job_id}` resolves at
all.

### (c) access log shows the 201 with a real `status` — **PASS**

The first decision-relevant data the Stage-0 access log has ever produced:

```
2026-08-08 08:34:54.995  POST  /jobs                          201  7785ms  int=201
2026-08-08 08:36:05.856  GET   /jobs/{jobId}                  200   750ms  int=200
2026-08-08 08:36:06.803  GET   /applications/{application_id} 200  4893ms  int=200
```

### (d) `GET` the application → hub projection returns it — **PASS at the HTTP level, but the gate is vacuous**

```
<<<HTTP 200>>>
{"application": {"application_id": "518c11b9-…", "state": "created",
                 "created_at": "2026-08-08T08:35:02.662086+00:00",
                 "trial_credit_consumed": false, "company_research_error": false},
 "job": {"job_id": "518c11b9-…", "company_name": "SysAid", …}}
```

It returns `state: "created"` **for a row that does not exist**. The projection is
synthesised in memory by `_build_application_from_job`
(`application_handler.py:132-143`) from the jobs-table record whenever no hub row is
found. So gate (d) returns 200 whether or not gate (b) holds — **it cannot corroborate
(b), and a green (d) must never be read as evidence the hub row exists.** That is
worth carrying: the same synthesis is what would make a missing hub row invisible to
any later stage that checks via the API instead of the table.

### (e) no new N8-shaped write — **NOT APPLICABLE, and clean on the parts that do apply**

There is no hub write to judge, because no hub write happens. On what does exist:

- `create_job` writes through the repository, **not** an inline dict. No N8 shape.
- `ApplicationRepository`'s grammar is correct where it is used —
  `Key={'userId': user_id, 'applicationId': application_id}` in `create`, `get`,
  `update_state`, `update_cv`, `update_gap_responses`, `update_artifact_status`.
  Partition = USER, sort = APPLICATION, as required.
- `jobs-table` is partitioned by `job_id` alone, so the key is *not* a tenant
  boundary — but `get_job` compensates with an explicit application-layer ownership
  check (`job_handler.py:317-320`, `_ownership_denied_response`). Not a finding.

---

## 8. New defects — flagged, not fixed

| id | severity | what | where |
|---|---|---|---|
| **N22** | low (devx) / real (prod) | 2 orphaned CV objects in S3 with no `cvs-table` row. S3 PUT precedes the DynamoDB write, and per N5 the reaper is a no-op. | `cv_upload_handler.py:132` vs `:188` |
| **N23** | medium | `ApplicationRepository.create()` has **zero callers**. The hub row is conjured by an upsert side effect at gap-responses, so an application exists in a partial, later, implicitly-created form — and `GET /applications/{id}` hides this by synthesising one. | `application_repository.py:53`, `application_handler.py:132` |
| **N24** | medium | **No API request model declares `max_length`** (13 models, 0 constraints). `PATCH /cv-tailoring/{id}` has no model at all — bare `json.loads`. Meanwhile `cv_tailoring_models.py:35` permits 50,000 chars, six times the WAF limit. | `api_models.py`, `cv_tailoring_handler.py:942` |
| **N25** | cosmetic | `HandleFinalArtifactsFailure` writes `artifact_statuses.final_artifacts`, an artifact type that does not exist. `update_artifact_status` accepts any string. | `artifact_chain_construct.py:129`, `application_repository.py:180` |

---

## 9. Not done, deliberately

- **Stage 1 steps 4b / 5 / 6** — the users-table write still runs, the `CV#` rows are
  untouched, the worker still exists. Per instruction: 5 of 6 CV readers sit behind
  upstream artifact gates, so verifying them means running the whole journey.
- **Stage 3+ / any generator** — no VPR, gap, cover letter or interview prep was run.
  No LLM spend, no trial credits consumed beyond the reset.
- **The 23 DLQ messages** — read with `--visibility-timeout 0`, nothing deleted or
  consumed. They stay queued until uploads are proven working.
- `dev` and `staging` untouched. No repartition, no table alias, no env-chain change,
  no edit to `ai-assist`'s `ARTIFACTS_TABLE_NAME`, no scope-lock twin touched.

